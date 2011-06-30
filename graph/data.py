'''
    Queries the database, and returns data for rendering to websites.

    Usage:
    User requests a URL. URL is parsed by urls.py into arguments for views.py.
    Views then forwards these arguments to these functions to get the data.
'''
from functools import wraps

from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django import forms
from django.db.models import Avg, Max, Min, Count

from energyweb.graph.models import SensorGroup, SensorReading, Sensor, \
                                   PowerAverage, SRProfile
import calendar, datetime, simplejson, time

from constants import *

##############################
# URL generating helper functions
##############################

def _gen_now():
    ''' Returns now as a time that urls play nicely with '''
    return str(calendar.timegm(datetime.datetime.now().timetuple()))

def _generate_start_data(startOffset):
    '''
    Returns a formated date for use as HTML.
    This allows for passing of start dates to data gathering functions.
    '''
    junk=_gen_now()
    start_dt = datetime.datetime.now() - startOffset
    data = str(int(calendar.timegm(start_dt.timetuple()) * 1000))
    return (data,junk)

##############################
# User Specified Data's Form Verification
##############################

def _graph_max_points(start, end, res):
    '''
    Return the maximum number of points a graph for this date range
    (starting at datetime start and ending at datetime end), and
    using resolution res, might have.  (The graph may have fewer
    points if there are missing sensor readings in the date range.)
    '''
    delta = end - start
    per_incr = RESOLUTION_DELTAS[res]
    return ((delta.days * 3600 * 24 + delta.seconds) 
            / float(per_incr.days * 3600 * 24 + per_incr.seconds))

class CustomGraphForm(forms.Form):
    ''' Used to validate forms for custom graphs '''
    DATE_INPUT_FORMATS = (
        '%Y-%m-%d',              # '2006-10-25'
        '%m/%d/%Y',              # '10/25/2006'
        '%m/%d/%y',              # '10/25/06'
    )
    TIME_INPUT_FORMATS = (
        '%H:%M',        # '14:30'
        '%I:%M %p',     # '2:30 PM'
        '%I%p',         # '2PM'
    )
    DATE_FORMAT = '%Y-%m-%d'
    TIME_FORMAT = '%l:%M %p'
    DT_INPUT_SIZE = '10'
    # TODO: last I checked, the entry for month in AVERAGE_TYPES was
    # None... handle this less hackishly
    RES_LIST = [res for res in PowerAverage.AVERAGE_TYPES if res != 'month']
    RES_CHOICES = (
        [('auto', 'auto')]
        + [(res_choice, PowerAverage.AVERAGE_TYPE_DESCRIPTIONS[res_choice])
           for res_choice in RES_LIST]
    )
    
    start = forms.SplitDateTimeField(
        input_date_formats=DATE_INPUT_FORMATS,
        input_time_formats=TIME_INPUT_FORMATS,
        widget=forms.SplitDateTimeWidget(attrs={'size': DT_INPUT_SIZE},
                                         date_format=DATE_FORMAT,
                                         time_format=TIME_FORMAT))
    end = forms.SplitDateTimeField(
        input_date_formats=DATE_INPUT_FORMATS,
        input_time_formats=TIME_INPUT_FORMATS,
        widget=forms.SplitDateTimeWidget(attrs={'size': DT_INPUT_SIZE},
                                         date_format=DATE_FORMAT,
                                         time_format=TIME_FORMAT))

    res = forms.ChoiceField(label='Resolution', choices=RES_CHOICES)

    def clean(self):
        '''
        Ensure that:
        * Start and end times constitute a valid range.
        * The number of data points requested is reasonable.
        Also set computed_res (a key in the cleaned data dictionary)
        to the specified resolution, or if the specified resolution was
        auto, set it to the actual resolution to be used.
        '''
        cleaned_data = self.cleaned_data

        if not cleaned_data['start'] < cleaned_data['end']:
            raise forms.ValidationError('Start and end times do not '
                                        'constitute a valid range.')

        delta = cleaned_data['end'] - cleaned_data['start']

        # Check that the defined resolution isn't going to be too fine
        # and cause too many data points
        if cleaned_data['res'] in self.RES_LIST:
            per_incr = PowerAverage.AVERAGE_TYPE_TIMEDELTAS[
                cleaned_data['res']]
            max_points = ((delta.days * 3600 * 24 + delta.seconds) 
                / float(per_incr.days * 3600 * 24 + per_incr.seconds))

            cleaned_data['computed_res'] = cleaned_data['res']
            
        # Typically called if auto is used
        else:
            if delta.days > 7*52*3: # 3 years
                cleaned_data['computed_res'] = 'week'
            elif delta.days > 7*8: # 8 weeks
                cleaned_data['computed_res'] = 'day'
            elif delta.days > 6: # 1-7 weeks
                cleaned_data['computed_res'] = 'hour'
            elif delta.days > 0: # 1-7 days
                cleaned_data['computed_res'] = 'minute*10'
            elif delta.seconds > 3600*3: # 3 hours
                cleaned_data['computed_res'] = 'minute'
            else:
                cleaned_data['computed_res'] = 'second*10'
                
        return cleaned_data

class StaticGraphForm(CustomGraphForm):
    '''
    Used to limit data queries for the Public Custom Graph.
    '''
    GRAPH_MAX_POINTS = 2000

    def clean(self):
        '''
        Ensure the data is sane.
        This version also checks that ordinary users are not asking
        for too much data, because it might kill the server.
        Really only an issue for users who specified resolutions.
        '''
        cleaned_data = CustomGraphForm.clean(self)

        if _graph_max_points(cleaned_data['start'], 
                             cleaned_data['end'], 
                             cleaned_data['computed_res']) \
                             > self.GRAPH_MAX_POINTS:
            raise forms.ValidationError('Too many points in graph '
                                        '(resolution too fine).')
        return cleaned_data                

##############################
# Utility
##############################

# TODO: this could probably be done in a more portable way.
def _get_sensor_groups():
    '''
    Return a list with three elements,
    representing the sensors and sensor groups.
    The zeroth element is a list containing:
      -The sensor group id (building id)
      -The sensor group name (building name)
      -The sensor group color (building color for graphing)
      - A list containing [sensor id, sensor name] for all sensors associated
        with the sensor group
    The first element is a list of individual sensor ids.
    The second element is a dictionary with:
      -keys: sensor group ids (building ids)
      -values: all sensors belonging to that building
    '''
    # get the sensors from the database
    # They must be ordered so that we can put them into groups.
    sensors = Sensor.objects.select_related().order_by('sensor_group__pk')

    sensor_groups = []
    sensor_ids = []
    sensor_ids_by_group = {}
    sg_id = None # Keep track of last seen id for grouping purposes

    for sensor in sensors:
        # Mark all seen sensors
        sensor_ids.append(sensor.pk)
        # We've had this group before, so add it to the list
        if sg_id == sensor.sensor_group.pk:
            sensor_groups[-1][3].append([sensor.pk, sensor.name])
            sensor_ids_by_group[sg_id].append(sensor.pk)
        # Start a new sensor group
        else:
            sg_id = sensor.sensor_group.pk
            sensor_groups.append([
                         sg_id,
                         sensor.sensor_group.name,
                         sensor.sensor_group.color, 
                         [
                             [sensor.pk, sensor.name]
                         ]
                     ])
            sensor_ids_by_group[sg_id] = [sensor.pk]
            
    return (sensor_groups, sensor_ids, sensor_ids_by_group)

##############################
# Average Collecting
##############################

def _query_averages(res,start_offset = 0):
    """
    Gets the averages for a string res (needs to be a resolution type)
    Returns them for all Sensors, in a dictionary with sensor ID as keys.
    Start_offset is to be used for cycle_view. This should be the key of 
    the list to use.
    """
    all_averages = dict([[sid,0] for sid in SENSOR_IDS])

    trunc_reading_time = None
        
    for average in PowerAverage.objects.filter(average_type=res
                    ).order_by('-trunc_reading_time')[len(SENSOR_IDS)*(
        CYCLE_START_DIFFS[res][start_offset]):len(SENSOR_IDS)*(
        CYCLE_START_DIFFS[res][start_offset]+1)]:

        if trunc_reading_time is None:
            trunc_reading_time = average.trunc_reading_time
        if average.trunc_reading_time == trunc_reading_time:
            # Note that we limited the query by the number of sensors in
            # the database.  However, there may not be an average for
            # every sensor for this time period.  If this is the case,
            # some of the results will be for an earlier time period and
            # have an earlier trunc_reading_time .
            all_averages[average.sensor_id] \
                = average.watts / 1000.0
    return all_averages

def _get_averages():
    '''
    Obtains minute, week, and month averages over those
    last cycles for certain sensors.
    sensor_ids must be a list of sensors.
    '''
    res_choices = ['minute','week','month']
    all_averages = dict([[res,{}] for res in res_choices])

    for average_type in res_choices:
        all_averages[average_type] = \
                _query_averages(average_type,0)

    return all_averages

def _get_detail_averages(res):
    '''
    Gets the averages for detail graphs.
    Gets it both for cycle and diagnostic modes.
    '''
    all_averages = dict([[sid,{}] for sid in SENSOR_IDS])
    # Use start_offsets to mark each cycle
    for start_offset in range(len(CYCLE_START_DIFFS[res])):
        results = _query_averages(res,start_offset)
        for sid,value in results.iteritems():
            all_averages[sid][start_offset] = value

    return all_averages

###############
# Integrate
###############

def _integrate(start_dt,end_dt,res,splitSensors=True):
    '''
    Reports the integrated power usage from start to stop.
    Returns in watt*hr
    Uses data points of res resolution for the integration.
    '''
    corrections = {
        'minute*10':1/6.0,#6 of these per hour
        'hour':1,
        'day':24,}
    
    if splitSensors:
        watt_totals = dict([ [sid,0] for sid in SENSOR_IDS])
        def _acc_call(sg,x,y,rtn_obj):
            pass
        def _snr_call(sid,x,y,rtn_obj):
            try:
                rtn_obj[sid] += y
            except:
                rtn_obj[sid] += 0

    else:
        watt_totals = dict([ [sg[0], 0] for sg in SENSOR_GROUPS])
        def _acc_call(sg,x,y,rtn_obj):
            try:
                rtn_obj[sg] += y
            except:
                pass
        def _snr_call(sid,x,y,rtn_obj):
            pass

    _build_db_results(res,start_dt,end_dt,
                      watt_totals,
                      lambda a,b : None, # Does nothing on x_call
                      _acc_call,
                      _snr_call)
    if not watt_totals:
        return None
         
    for reading in watt_totals.keys():
        watt_totals[reading] = watt_totals[reading]*corrections[res]

    return watt_totals
    
##############################
# Converting data to a serializable form
##############################

def _make_data_dump(start, end=None, res='second*10'):
    '''
    Creates a dictionary of data.
    Dictionary always includes
       sg_xy_pairs:
           Graph points in [x,y] for each building
       sensor_groups:
           List of the sensor groups as given by _get_sensor_groups
       (The next two are only used by dynamic graphs)
       desired_first_record:
           Tells what data point should be used to refresh the graph
       last_record:
           Tells where the graph stops
    If failed to make the data dictionary, will simply return None.   
    '''
    start_dt = datetime.datetime.utcfromtimestamp(int(start))
    if end:
        end_dt = datetime.datetime.utcfromtimestamp(int(end))
    else:
        end_dt = None

    sg_xy_pairs = dict([[sg[0], []] for sg in SENSOR_GROUPS])
        
    _build_db_results(res,start_dt,end_dt,
                      sg_xy_pairs,
                      lambda x,rtn_obj : int(calendar.timegm(x))*1000,
                      lambda id,x,y,rtn_obj : rtn_obj[id].append((x,y))
                      )

    if not sg_xy_pairs:
        d = {
            'no_results': True,
            'sensor_groups': SENSOR_GROUPS,
            }
    else:
        last_record = sg_xy_pairs[1][-1][0] # get last x value
        # Says where the graph should start at
        desired_first_record = start*1000
    
        d = {'no_results': False,
             'sg_xy_pairs': sg_xy_pairs,
             'desired_first_record':
             desired_first_record,
             'sensor_groups': SENSOR_GROUPS,
             'last_record':last_record}
    return d

def download_csv(request, start, end, res):
    '''
    A view returning the CSV data points of the static graph.
    Called when someone hits the button on the static graph page.
    Used for users to download data.
    This does not utilize _make_data_dump because the csv files
    use a significantly different structuring than the list of points.
    Thus while the algorithm is effectively the same,
    how it stores data differs.
    '''
    # Start writing the csv output
    data = ''
    
    start_dt = datetime.datetime.utcfromtimestamp(int(start))
    end_dt = datetime.datetime.utcfromtimestamp(int(end))


    # Write down the column headings
    data += ',Time,'
    for building in SENSOR_GROUPS:
        data += building[1] + ','

    data_pnts = []

    def _x_handler(x,rtn_obj):
        ''' Start a new line, then return x back as readable time'''
        rtn_obj.append('\n')
        rtn_obj.append(time.strftime("%a %d %b %Y %H:%M:%S",x))
        return x
        
    _build_db_results(res,start_dt,end_dt,
                      data_pnts,
                      _x_handler,
                      lambda id,x,y,rtn_obj : rtn_obj.append(str(y))
                      )

    template = ","
    data += template.join(data_pnts)

    # Send the csv to be posted
    return HttpResponse(data,
                        mimetype='application/csv')

def _get_detail_data(building, resolution, start_time):
    '''
    Creates the dictionary for detail view
    '''
    # Because transferring non-strings over gets annoying,
    # this is how we'll get buildings
    cur_building = None
    for sg in SENSOR_GROUPS:
        if sg[1].lower() == str(building): # check if identical names
            cur_building = sg

    returnDictionary = {'graph_data':[],
                        'building': building.capitalize(),
                        'building_color': cur_building[2],
                        'res': resolution,
                        }

    for start_time_delta in range(len(CYCLE_START_DELTAS[resolution])):

        start_dt = datetime.datetime.utcfromtimestamp(
            int(start_time) / 1000 - 
            CYCLE_START_DELTAS[resolution][start_time_delta].seconds - 
            CYCLE_START_DELTAS[resolution][start_time_delta].days*3600*24 )
        
        # dictionary has keys of total and then the sensor ids
        xy_pairs = {'total':[]}
        for sensor_id in SENSOR_IDS_BY_GROUP[cur_building[0]]:
            xy_pairs[sensor_id] = []

        def _x_call(x,rtn_obj):
            value = int(calendar.timegm(x))*1000
            if not start_time_delta == 0:
                old_cycle = CYCLE_START_DELTAS[resolution][start_time_delta]
                value += old_cycle.seconds*1000 +\
                    old_cycle.days*3600*24*1000 -\
                    CYCLE_START_DELTAS[resolution][0].seconds*1000 -\
                    CYCLE_START_DELTAS[resolution][0].days*3600*24*1000   
            rtn_obj['total'].append([value,0])
            return value

        def _snr_call(sid,x,y,rtn_obj):
            if sid in rtn_obj.keys():
                index = len(rtn_obj[sid])
                for snr in rtn_obj.keys():
                    try:
                        y = y - rtn_obj[snr][index][-1]
                    except:
                        pass
                rtn_obj[sid].append([x,y])

        def _acc_call(sg_id,x,y,rtn_obj):
            if sg_id == cur_building[0]:
                try:
                    rtn_obj['total'][-1][1] += y
                except:
                    rtn_obj['total'][-1][1] += 0

        _build_db_results(AUTO_RES_CONVERT[resolution],
                          start_dt, start_dt+RESOLUTION_DELTAS[resolution],
                          xy_pairs,
                          _x_call,_acc_call,_snr_call)

        if len(xy_pairs['total']) > 0:
            returnDictionary['graph_data'].append(xy_pairs)
        
    # desired_first_record is our start_time in seconds
    desired_first_record = int(start_time)/1000
    # last x result
    last_record = returnDictionary['graph_data'][0]['total'][-1][0] 

    junk = _gen_now()
    data_url = reverse('energyweb.graph.views.detail_graph_data',
                       kwargs={ 'building': building, \
                                    'resolution':resolution, \
                                    'start_time':str(last_record)
                                }) + '?junk=' + junk

    returnDictionary['data_url'] = data_url
    returnDictionary['sensors'] = xy_pairs.keys()
    returnDictionary['no_results'] = False
    returnDictionary['desired_first_record'] = desired_first_record

    return returnDictionary

def _get_detail_table(building, resolution, start_time):
    '''
    Returns two data tables.
    Cycle Table:
        Cycle Name | Avg This Cycle | Integrated Value
    Diagnostic Table:
        Sensor ID | Avg. This Minute | Avg. This Interval | Integrated Value
    '''
    # Because transferring non-strings over gets annoying,
    # this is how we'll get buildings
    cur_building = None
    for sg in SENSOR_GROUPS:
        if sg[1].lower() == str(building): # check if identical names
            cur_building = sg
            
    dataDictionary = {'graph_data':[],
                      'building': building.capitalize(),
                      'res': resolution,
                      }
    
    dataDictionary['cycleTable'] = {}
    dataDictionary['diagnosticTable'] = {}

    for sid in SENSOR_IDS_BY_GROUP[cur_building[0]]:
        dataDictionary['diagnosticTable'][str(sid)] = {
            'now': 0,
            'interval':0,
            'integrated':0,
            }
    # Python doesn't shuffle order of lists...
    dataDictionary['diagnosticRow'] = ['now','interval','integrated']

    for cycle_id in range(len(CYCLE_START_DELTAS[resolution])):
        dataDictionary['cycleTable'][str(cycle_id)] = \
            dict([['avg',0],['integrated',0]])

    # Input all of the "Now" averages for Diagnostic
    cur_cycles = _get_detail_averages('minute')
    for sid in SENSOR_IDS_BY_GROUP[cur_building[0]]:
        dataDictionary['diagnosticTable'][str(sid)]['now'] = \
            cur_cycles[sid][0]

    dataDictionary['debug'] = {}
    # Input all of the "This Interval" for diagostic table.
    average_cycles = _get_detail_averages(resolution)
    for sid in SENSOR_IDS_BY_GROUP[cur_building[0]]:
        dataDictionary['diagnosticTable'][str(sid)]['interval'] = \
            average_cycles[sid][0]
        dataDictionary['debug'][sid] = average_cycles[sid]



    # Input Cycle Table's Values
    for cycle_id in dataDictionary['cycleTable'].keys():
        cid = int(cycle_id)

        start_dt = datetime.datetime.utcfromtimestamp(
            int(start_time) / 1000 - 
            CYCLE_START_DELTAS[resolution][cid].seconds - 
            CYCLE_START_DELTAS[resolution][cid].days*3600*24 )

        # Integrate gives information back by building.
        integValues = _integrate(start_dt,
                                 start_dt+RESOLUTION_DELTAS[resolution],
                                 AUTO_RES_CONVERT[resolution],
                                 False)
        try:
            dataDictionary['cycleTable'][cycle_id]['integrated'] = \
                integValues[cur_building[0]]
        except:
            dataDictionary['cycleTable'][cycle_id]['integrated'] = 0
        # The Average getter gets by sensor group. Thus need to sum.
        for sid in SENSOR_IDS_BY_GROUP[cur_building[0]]:
            dataDictionary['cycleTable'][cycle_id]['avg'] += \
                average_cycles[sid][int(cycle_id)]
        
    # Python doesn't shuffle order of lists...
    dataDictionary['cycleRow'] = ['avg',
                                  'integrated']

    CONVERT = {'minute': 'now', resolution:'interval'}

    ####
    # get averages for the diagnostic table
    all_averages = {}
    for average_type in ('minute',resolution):

        results = _query_averages(average_type,0)

        for sid,value in results.iteritems():
            if sid in dataDictionary['diagnosticTable'].keys():
                dataDictionary['diagnosticTable']\
                                [sid][CONVERT[average_type]] \
                                = value

    start_dt = datetime.datetime.utcfromtimestamp(
        int(start_time) / 1000 - 
        CYCLE_START_DELTAS[resolution][0].seconds - 
        CYCLE_START_DELTAS[resolution][0].days*3600*24 )
    
    # GET INTEGRATED VALUES
    all_watthr_data = _integrate(start_dt,
                                 start_dt + \
                                     RESOLUTION_DELTAS[resolution],
                                 AUTO_RES_CONVERT[resolution],
                                 True)
    for ID in dataDictionary['diagnosticTable'].keys():
        dataDictionary['diagnosticTable'][ID]['integrated'] = \
            all_watthr_data[int(ID)]
    
    return dataDictionary

def _build_db_results(res,start_dt,end_dt,
                      rtn_obj, x_call, acc_call,snr_call=None):
    '''
    Loops through the database from UTC datetime object start_dt to end_dt
    Uses a string of res to determine point resolution.
    rtn_obj must be a mutable type, like dictionary or list.
    x_call will get current timetuple and the return object
    acc_call puts things into the rtn_obj by building
    snr_call will place things into the rtn_obj by sensor
    '''
    from django.db import connection, transaction

    cur = connection.cursor()
    PowerAverage.graph_data_execute(cur, res, start_dt, end_dt)

    r = cur.fetchone()

    if r is None:
        return None
    else:
        per = r[2]
        per_incr = RESOLUTION_DELTAS[res]
    
        # At the end of each outer loop, we increment the
        # current period by a resolution step.
        while r is not None:
            # Call the given function.
            # Pass the return object in case they want to do something odd
            x = x_call(per.timetuple(), rtn_obj)

            for sg in SENSOR_GROUPS:
                y = 0 # Always starts at 0
                for sid in SENSOR_IDS_BY_GROUP[sg[0]]:
                    # If this sensor has a reading for the current per,
                    # update y.  There are three ways the sensor might
                    # not have such a reading:
                    # 1. r is None, i.e. there are no more readings at
                    #    all
                    # 2. r is not None and r[2] > per, i.e. there are 
                    #    more readings but not for this per
                    # 3. r is not None and r[2] <= per and r[1] != s[0],
                    #    i.e. there are more readings for this per,
                    #    but none for this sensor
                    if r is not None and r[2] <= per and r[1] == sid:
                        # Increase y if its there.
                        # Then get the next data point
                        if y is not None:
                            y += float(r[0])
                        r = cur.fetchone()
                    else:
                        y = None
                    if snr_call:
                        snr_call(sid,x,y,rtn_obj)
                # Add to object as described
                acc_call(sg[0],x,y,rtn_obj)
                
            per += per_incr

    return rtn_obj


(SENSOR_GROUPS, SENSOR_IDS, SENSOR_IDS_BY_GROUP) = _get_sensor_groups()
RESIDENTIAL_SENSORGROUPS = SENSOR_GROUPS[:8]
ACADEMIC_SENSORGROUPS = SENSOR_GROUPS[8:]
