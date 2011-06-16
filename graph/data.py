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
    # TODO (last I checked, the entry for month in AVERAGE_TYPES was
    # None... handle this less hackishly)
    RES_LIST = [res for res in PowerAverage.AVERAGE_TYPES if res != 'month']
    RES_CHOICES = (
        [('auto', 'auto')]
        + [(res_choice, PowerAverage.AVERAGE_TYPE_DESCRIPTIONS[res_choice])
           for res_choice in RES_LIST]
    )
    
    start = forms.SplitDateTimeField(input_date_formats=DATE_INPUT_FORMATS,
                input_time_formats=TIME_INPUT_FORMATS,
                widget=forms.SplitDateTimeWidget(attrs={'size': DT_INPUT_SIZE},
                                                 date_format=DATE_FORMAT,
                                                 time_format=TIME_FORMAT))

    end = forms.SplitDateTimeField(input_date_formats=DATE_INPUT_FORMATS,
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
    # TODO: GRAPH_MAX_POINTS is used to determine when to refuse data
    # because the resolution is too fine (it would be too hard on the
    # database).  
    GRAPH_MAX_POINTS = 2000

    def clean(self):
        '''
        Ensure the data is sane.
        This version also checks that ordinary users aren't asking
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

# TODO: this could probably be done in a more portable way.
def _get_sensor_groups():
    '''
    Return a list with three elements, representing the sensors and sensor groups.
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

def _get_averages(sensor_ids):
    '''
    Obtains minute, week, and month averages over those
    last cycles for certain sensors.
    sensor_ids must be a list of sensors.
    '''

    all_averages = {
        'minute':{},
        'week':{},
        'month':{}
        }

    for average_type in ('minute','week', 'month'):

        trunc_reading_time = None

        for average in PowerAverage.objects.filter(average_type=average_type
            ).order_by('-trunc_reading_time')[:len(SENSOR_IDS)]:

            if trunc_reading_time is None:
                trunc_reading_time = average.trunc_reading_time
            if average.trunc_reading_time == trunc_reading_time:
                # Note that we limited the query by the number of sensors in
                # the database.  However, there may not be an average for
                # every sensor for this time period.  If this is the case,
                # some of the results will be for an earlier time period and
                # have an earlier trunc_reading_time .
                all_averages[average_type][average.sensor_id] \
                    = average.watts / 1000.0
        for sensor_id in SENSOR_IDS:
            if not all_averages[average_type].has_key(sensor_id):
                # We didn't find an average for this sensor; set the entry
                # to None.
                all_averages[average_type][sensor_id] = None        

    return all_averages

def _integrate(start_dt,end_dt,res,splitSensors=True):
    '''
    Reports the integrated power usage from start to stop.
    Returns in watt*hr
    Uses data points of res resolution for the integration.
    '''
    from django.db import connection, transaction
    cur = connection.cursor()

    per_incr = PowerAverage.AVERAGE_TYPE_TIMEDELTAS[res]

    corrections = {
        'minute*10':1/6.0,#6 of these per hour
        'hour':1,
        'day':24,}
    
    PowerAverage.graph_data_execute(cur, res, start_dt, end_dt)

    if not splitSensors:
        watt_totals = dict([ [sg[0], 0] for sg in SENSOR_GROUPS])
    else:
        watt_totals = dict([ [sid,0] for sid in SENSOR_IDS])

    r = cur.fetchone()
    if r is None:
        return None
    else:
        per = r[2]
    
        while r is not None:

            for sg in SENSOR_GROUPS:
                y = 0
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
                        if y is not None:
                            if splitSensors:
                                watt_totals[sid] += float(r[0])
                            else:
                                y += float(r[0])
                        r = cur.fetchone()
                    else:
                        y = None
                if not splitSensors and y:
                    watt_totals[sg[0]] += y
            per += per_incr
        
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
    from django.db import connection, transaction
    cur = connection.cursor()

    (sensor_groups, sensor_ids, sensor_ids_by_group) = _get_sensor_groups()

    start_dt = datetime.datetime.utcfromtimestamp(int(start))
    if end:
        end_dt = datetime.datetime.utcfromtimestamp(int(end))
    else:
        end_dt = None
    per_incr = PowerAverage.AVERAGE_TYPE_TIMEDELTAS[res]
    
    PowerAverage.graph_data_execute(cur, res, start_dt, end_dt)

    # Also note, above, that if data was supplied then we selected
    # everything since the provided timestamp's truncated date,
    # including that date.  We will always provide the client with
    # a new copy of the latest record he received last time, since
    # that last record may have changed (more sensors may have
    # submitted measurements and added to it).  The second to
    # latest and older records, however, will never change.

    # Now organize the query in a format amenable to the 
    # (javascript) client.  (The grapher wants (x, y) pairs.)

    sg_xy_pairs = dict([[sg[0], []] for sg in sensor_groups])
    r = cur.fetchone()
    if r is None:
        d = {'no_results':True,
             'sensor_groups':sensor_groups}
        return d
    else:
        per = r[2]
    
        # At the end of each outer loop, we increment per (the current
        # ten-second period of time we're considering) by ten seconds.
        while r is not None:
            # Remember that the JavaScript client takes (and
            # gives) UTC timestamps in ms
            x = int(calendar.timegm(per.timetuple()) * 1000)
            for sg in sensor_groups:
                y = 0
                for sid in sensor_ids_by_group[sg[0]]:
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
                        # If y is None, leave it as such.   Else, add
                        # this sensor reading to y.  Afterwards, in
                        # either case, fetch a new row.
                        if y is not None:
                            y += float(r[0])
                        r = cur.fetchone()
                    else:
                        y = None
                sg_xy_pairs[sg[0]].append((x, y))
            per += per_incr
    
        last_record = x
        # desired_first_record lags by (3:00:00 - 0:00:10) = 2:59:50
        desired_first_record = x - 1000*3600*3 + 1000*10
    
        d = {'no_results': False,
             'sg_xy_pairs': sg_xy_pairs,
             'desired_first_record':
                 desired_first_record,
             'sensor_groups': sensor_groups,
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
    from django.db import connection, transaction
    cur = connection.cursor() # Allows for SQL queries

    # Start writing the csv output
    data = ''
    
    start_dt = datetime.datetime.utcfromtimestamp(int(start))
    end_dt = datetime.datetime.utcfromtimestamp(int(end))
    per_incr = PowerAverage.AVERAGE_TYPE_TIMEDELTAS[res]

    (sensor_groups, sensor_ids, sensor_ids_by_group) = _get_sensor_groups()

    # Write down the column headings
    data += 'Time,'
    for building in sensor_groups:
        data += building[1] + ','
    data = data[:-1] + '\n' #slice off last comma because it will be extraneous.

    # Run Search to get data
    PowerAverage.graph_data_execute(cur, res, start_dt, end_dt)

    # Crazy loop to put things in table format.

    r = cur.fetchone() # Retrieves results as r
    
    if r: # Don't let this happen if r is none 'cause will segfault
        per = r[2]

        # At the end of each outer loop, we increment per (the current
        # ten-second period of time we're considering) by ten seconds.
        while r is not None:
            x = per.timetuple()
            # Formats time like 'Mon 30 May 2011 22:17:00'
            data += time.strftime("%a %d %b %Y %H:%M:%S",x) + ','
            for sg in sensor_groups:
                y = 0
                for sid in sensor_ids_by_group[sg[0]]:
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
                        # None implies signal was lost and should be preserved
                        if y is not None:
                            y += float(r[0])
                        r = cur.fetchone() # Go to the next data point
                    else:
                        y = None

                data += str(y) + ','
            per += per_incr
            data = data[:-1] + '\n' # Slice off the last comma, again

    # Send the csv to be posted
    return HttpResponse(data,
                        mimetype='application/csv')

(SENSOR_GROUPS, SENSOR_IDS, SENSOR_IDS_BY_GROUP) = _get_sensor_groups()
