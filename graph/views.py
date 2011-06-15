from functools import wraps

from django.shortcuts import render_to_response
from django.core import serializers
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.conf import settings
from django import forms
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login
from django.db.models import Avg, Max, Min, Count

from energyweb.graph.models import SensorGroup, SensorReading, Sensor, \
                                   PowerAverage, SRProfile
import calendar, datetime, simplejson, time

from constants import *

# If a full graph has this many points or fewer, show the individual
# points.  (Otherwise only draw the lines.)
GRAPH_SHOW_POINTS_THRESHOLD = 40


def _graph_max_points(start, end, res):
    '''
    Return the maximum number of points a graph for this date range
    (starting at datetime start and ending at datetime end), and
    using resolution res, might have.  (The graph may have fewer
    points if there are missing sensor readings in the date range.)
    '''
    delta = end - start
    per_incr = RESOLUTION_DELTAS[res] #PowerAverage.AVERAGE_TYPE_TIMEDELTAS[res]
    return ((delta.days * 3600 * 24 + delta.seconds) 
            / float(per_incr.days * 3600 * 24 + per_incr.seconds))


class StaticGraphForm(forms.Form):
    # TODO: GRAPH_MAX_POINTS is used to determine when to refuse data
    # because the resolution is too fine (it would be too hard on the
    # database).  This functionality could be more robust.
    GRAPH_MAX_POINTS = 2000
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

            if _graph_max_points(cleaned_data['start'], 
                                 cleaned_data['end'], 
                                 cleaned_data['res']) > self.GRAPH_MAX_POINTS:
                raise forms.ValidationError('Too many points in graph '
                                            '(resolution too fine).')
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

def _generate_start_data(startOffset):
    '''
    Returns a formated date for use as HTML.
    This allows for passing of start dates to data gathering functions.
    '''
    junk=str(calendar.timegm(datetime.datetime.now().timetuple()))
    start_dt = datetime.datetime.now() - startOffset
    data = str(int(calendar.timegm(start_dt.timetuple()) * 1000))
    return (data,junk)

def data_interface(request):
    '''
    A view returning the HTML for the dynamic table.
    This table holds curr. use and avg of past week/month.
    '''
    # Get data from three hours ago until now.
    (data, junk) = _generate_start_data( datetime.timedelta(0,3600*3,0) )

    return render_to_response('graph/data_interface.html', 
        {'sensor_groups': _get_sensor_groups()[0],
         'data_url': reverse('energyweb.graph.views.statistics_table_data', 
                             kwargs={'data': data}) + '?junk=' + junk},
        context_instance=RequestContext(request))

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
            ).order_by('-trunc_reading_time')[:len(sensor_ids)]:

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
        for sensor_id in sensor_ids:
            if not all_averages[average_type].has_key(sensor_id):
                # We didn't find an average for this sensor; set the entry
                # to None.
                all_averages[average_type][sensor_id] = None        

    return all_averages

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

def statistics_table_data(request, data):
    '''
    A view returning the JSON data used to populate the averages table.
    '''
    from django.db import connection, transaction
    cur = connection.cursor()

    (sensor_groups, sensor_ids, sensor_ids_by_group) = _get_sensor_groups()

    all_averages = _get_averages(sensor_ids)

    # Create the final return dictionary with initial values
    d = {
        'no_results': True,
        'min_averages': all_averages['minute'],
        'week_averages': all_averages['week'],
        'month_averages': all_averages['month'],
        'sensor_groups': sensor_groups,
        }

    # Get current data. Loop through data to make sure we have something
    now = datetime.datetime.now() - datetime.timedelta(0,40,0)
    PowerAverage.graph_data_execute(cur, 'second*10', now)

    current_values = {}
    r = cur.fetchone()
    if r:
        per = r[2]
        per_incr = datetime.timedelta(0, 10, 0)
        # Increment the time period for 10 second intervals each loop
        while r is not None:
            x = int(calendar.timegm(per.timetuple())*1000)
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
                current_values[sg[0]] = y
            per += per_incr
        last_record = x
        junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
        data_url = reverse('energyweb.graph.views.statistics_table_data', 
                           kwargs={'data': str(last_record)}) + '?junk=' + junk
        # update with our results
        d['no_results'] = False
        d['cur_values'] = current_values
        d['data_url'] = data_url
             
    # Use json to transfer the data from Python to Javascript
    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(d),
                        mimetype='application/json')


def dynamic_graph(request):
    '''
    A view returning the HTML for the dynamic (home-page) graph.
    (This graph represents the last three hours and updates
    automatically.)
    '''
    # Get all data from last three hours until now
    (data, junk) = _generate_start_data( datetime.timedelta(0,3600*3,0) )

    return render_to_response('graph/dynamic_graph.html', 
        {'sensor_groups': _get_sensor_groups()[0],
         'data_url': reverse('energyweb.graph.views.dynamic_graph_data', 
                             kwargs={'data': data}) + '?junk=' + junk},
        context_instance=RequestContext(request))


def dynamic_graph_data(request, data):
    '''
    A view returning the JSON data used to populate the dynamic graph.
    '''
    # Set the maximum possible start time to three hours ago
    # to prevent excessive drawing of data
    max_time = datetime.datetime.now() - datetime.timedelta(0,3600*3,0)
    start = max( datetime.datetime.utcfromtimestamp(int(int(data)/1000)) ,
                 max_time )
    # Grab the dump of xy pairs
    data_dump = _make_data_dump( calendar.timegm(start.timetuple()) ,
                                None,
                                'second*10')

    if not data_dump['no_results']:
        # Create the URL to get more data
        junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
        data_url = reverse('energyweb.graph.views.dynamic_graph_data', \
                               kwargs={'data': \
                                           str(data_dump['last_record'])}) +\
                                           '?junk=' + junk
        data_dump['data_url'] = data_url
    
    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(data_dump),
                        mimetype='application/json')

def static_graph(request):
    '''
    A view returning the HTML for the static (custom-time-period) graph.
    Several return possibilities:
       1) Did not input data yet
       2) Input invalid data
       3) Input valid data
    They only get a graph back if they have input valid data!
    '''

    def _request_valid(request):
        return request.method == 'GET' \
               and 'start_0' in request.GET \
               and 'end_0' in request.GET \
               and 'res' in request.GET
    
    def _clean_input(get):
        # *_0 gives date, *_1 gives time in 12 hr w/ AM or PM
        for field in ('start_0', 'start_1', 'end_0', 'end_1'):
            if field in ('start_1', 'end_1'):
                # Allow e.g. pm or p.m. instead of PM
                get[field] = get[field].upper().replace('.', '')
                # Allow surrounding whitespace
            get[field] = get[field].strip()
        return get
    
    def _show_only_form():
        '''
        Refuse to show them a graph until they give you good parameters
        '''
        now = datetime.datetime.now()
        one_day_ago = now - datetime.timedelta(1)
        form = StaticGraphForm(initial={
            'start': one_day_ago,
            'end': now
        })
        return render_to_response('graph/static_graph_form.html',
            {'form_action': reverse('energyweb.graph.views.static_graph'),
             'form': form},
            context_instance=RequestContext(request))
    # BEGIN Case 1

    if not _request_valid(request):
        return _show_only_form()
    # BEGIN Case 2
    
    _get = _clean_input(request.GET.copy())
    form = StaticGraphForm(_get)

    if not form.is_valid():
        return _show_only_form()
    # We've passed the checks, now can display the graph!

    # The following functions are for setting the various arguments
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']
    res = form.cleaned_data['computed_res']
    
    # js_* is in the format for the Flot plotting package.
    int_start = int(calendar.timegm(start.timetuple()))
    int_end = int(calendar.timegm(end.timetuple()))
    js_start = int_start * 1000
    js_end = int_end * 1000
    junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
    keyword_args = {'start': str(int_start), 
                    'end': str(int_end), 
                    'res': res}
    
    # generate the URLs for data dumps
    data_url = reverse('energyweb.graph.views.static_graph_data',
                       kwargs=keyword_args) + '?junk=' + junk
    
    download_url = reverse('energyweb.graph.views.download_csv',
                           kwargs=keyword_args) + '?junk=' + junk

    final_args = {'start': js_start,
                  'end': js_end,
                  'data_url': data_url,
                  'download_url': download_url,
                  'form': form,
                  'form_action': reverse('energyweb.graph.views.static_graph'),
                  'res': res}
    
    return render_to_response('graph/static_graph.html', 
                              final_args,
                              context_instance=RequestContext(request))


def static_graph_data(request, start, end, res):
    '''
    A view returning the JSON data used to populate the static graph.
    '''
    
    data_dump = _make_data_dump(start, end, res)
    
    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(data_dump),
                        mimetype='application/json')

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
            data = data[:-1] + '\n'

    # Send the csv to be posted
    return HttpResponse(data,
                        mimetype='application/csv')

def detail_graphs(request, building, res):
    '''
    A view returning the HTML for the Detailed Building graph.
    (This graph represents the last three hours and updates
    automatically.)
    '''
    # Get the current date.
    (data, junk) = _generate_start_data( datetime.timedelta(0,0,0) )

    d = {
        'data_url': reverse('energyweb.graph.views.detail_graphs_data', 
                            kwargs={'building': building,
                                    'mode':'cycle',
                                    'resolution':res,
                                    'start_time':data}) + '?junk=' + junk,
        'graph_title': building.capitalize() + ' viewed over a ' + res, 
        }

    # Set the URLs for changing time periods.
    for time_period in ['day','week','month','year']:
        d[time_period+'_url'] = reverse('energyweb.graph.views.detail_graphs',
                                        kwargs={'building':building,
                                                'res':time_period})

    for building in ['south','north','west','east',\
                         'sontag','atwood','case','linde']:
        d[building+'_url'] = reverse('energyweb.graph.views.detail_graphs' ,
                                     kwargs={'building':building,'res':res})

    return render_to_response('graph/detail_graphs.html',d,
        context_instance=RequestContext(request))


def detail_graphs_data(request, building, mode, resolution, start_time):
    '''
    A view returning the JSON data used to populate the Detailed graph.
    '''
    from django.db import connection, transaction
    cur = connection.cursor()

    (sensor_groups, sensor_ids, sensor_ids_by_group) = _get_sensor_groups()

    # Because transferring non-strings over gets annoying,
    # this is how we'll get buildings
    cur_building = None
    for sg in sensor_groups:
        if sg[1].lower() == str(building): # check if identical names
            cur_building = sg

    average_data = {}
    all_averages = _get_averages(sensor_ids)
    for sid in sensor_ids_by_group[cur_building[0]]:
        average_data[sid] = {}
        for average_type in all_averages.keys():
            average_data[sid][average_type] = \
                all_averages[average_type][sid]

    returnDictionary = {'graph_data':[]}

    for start_time_delta in range(len(CYCLE_START_DELTAS[resolution])):
        # If the client has supplied data (a string of digits in the
        # URL---representing UTC seconds since the epoch), then we only
        # consider data since (and including) that timestamp.
        
        # NOTE: Removed the max... Might be a bad idea. We'll see.
        start_dt = datetime.datetime.utcfromtimestamp(
            int(start_time) / 1000 - 
            CYCLE_START_DELTAS[resolution][start_time_delta].seconds - 
            CYCLE_START_DELTAS[resolution][start_time_delta].days*3600*24 )
                   
        PowerAverage.graph_data_execute(cur,
                                        AUTO_RES_CONVERT[resolution],
                                        start_dt,
                                        start_dt + RESOLUTION_DELTAS[resolution]);

        # Also note, above, that if data was supplied then we selected
        # everything since the provided timestamp's truncated date,
        # including that date.  We will always provide the client with
        # a new copy of the latest record he received last time, since
        # that last record may have changed (more sensors may have
        # submitted measurements and added to it).  The second to
        # latest and older records, however, will never change.
        
        # Now organize the query in a format amenable to the 
        # (javascript) client.  (The grapher wants (x, y) pairs.)
        
        # dictionary has keys of total and then the sensor ids
        xy_pairs = {'total':[]}
        for sensor_id in sensor_ids_by_group[cur_building[0]]:
            xy_pairs[sensor_id] = []
            
        r = cur.fetchone()

        if r is None:
            d = {'no_results': True,}
        else:
            per = r[2]
            per_incr = RESOLUTION_DELTAS[AUTO_RES_CONVERT[resolution]]
            
            while r is not None:
                # Remember that the JavaScript client takes (and
                # gives) UTC timestamps in ms
                x = int(calendar.timegm(per.timetuple()) * 1000)
                # Need to adjust start time such that all X values are actually the same
                if not start_time_delta == 0:
                    x += CYCLE_START_DELTAS[resolution][start_time_delta].seconds*1000
                    x += CYCLE_START_DELTAS[resolution][start_time_delta].days*3600*24*1000 
                    x -= CYCLE_START_DELTAS[resolution][0].seconds*1000
                    x -= CYCLE_START_DELTAS[resolution][0].days*3600*24*1000
                    pass
                xy_pairs['total'].append([x,0])
                for sg in sensor_groups:
                    for sid in sensor_ids_by_group[sg[0]]:
                        y = 0
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
                            if y is not None and sid in xy_pairs.keys():
                                y += float(r[0])
                                # increment total here!
                                xy_pairs['total'][-1][1] += y
                            r = cur.fetchone()
                        else:
                            y = None

                        if start_time_delta == 0 and sid in xy_pairs.keys():
                            xy_pairs[sid].append( [x, y] )
                per += per_incr
            

            last_record = x
            # desired_first_record lags by 10 seconds from our initial time
            desired_first_record = x -  \
                int((RESOLUTION_DELTAS[resolution].seconds + \
                         RESOLUTION_DELTAS[resolution].days*3600*24) * 1000)

            # Only set the data_url for the original time loop
            if ( start_time_delta == 0):
                junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
                data_url = reverse('energyweb.graph.views.detail_graphs_data',
                                   kwargs={ 'building': building, \
                                                'mode':'cycle', \
                                                'resolution':resolution, \
                                                'start_time':str(last_record)
                                            }) + '?junk=' + junk
                returnDictionary['data_url'] = data_url
                returnDictionary['sensors'] = xy_pairs.keys()
                returnDictionary['no_results'] = False
                returnDictionary['desired_first_record'] = desired_first_record
                d = xy_pairs # Allow for split sensors
            else:
                d = xy_pairs

            # Put the graph data on the return dictionary
            returnDictionary['graph_data'].append(d)

    # Set some useful things to return
    returnDictionary['building'] = building.capitalize()
    returnDictionary['building_color'] = cur_building[2]
    returnDictionary['averages'] = average_data
    returnDictionary['res'] = resolution

    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(returnDictionary),
                        mimetype='application/json')

def mon_status_data(request):
    junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
    (sensor_groups, sensor_ids, sensor_ids_by_group) = _get_sensor_groups()
    sreadings = dict()
    for s_id in sensor_ids:
        sreadings[s_id] = [None, None, None, None]
        try:
            sr = SensorReading.objects.filter(sensor__id=s_id).latest('reading_time')
            sreadings[s_id][0] = int(calendar.timegm(sr.reading_time.timetuple()) * 1000)
        except SensorReading.DoesNotExist:
            pass
        # TODO: magic number
        d = SRProfile.objects.filter(sensor_reading__sensor__id=s_id, sensor_reading__reading_time__gte=(datetime.datetime.now() - datetime.timedelta(1))).aggregate(
            Avg('transaction_time'), 
            Min('transaction_time'),
            Max('transaction_time')) 
        sreadings[s_id][1] = int(d['transaction_time__avg'])
        sreadings[s_id][2] = d['transaction_time__min']
        sreadings[s_id][3] = d['transaction_time__max']
    return HttpResponse(simplejson.dumps({'sensor_readings': sreadings,
                                          'sensor_groups': sensor_groups,
                                          'data_url': reverse('energyweb.graph.views.mon_status_data')
                                                              + '?junk=' + junk}),
                        mimetype='application/json')

# decorator for views that require login
def login_required(view_callable):
    def check_login(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_callable(request, *args, **kwargs)

        assert hasattr(request, 'session'), "Session middleware needed."
        login_kwargs = {
            'extra_context': {
                REDIRECT_FIELD_NAME: request.get_full_path(),
                },
            }
        return login(request, **login_kwargs)
    return wraps(view_callable)(check_login)


@login_required
def mon_status(request):
    ''' Requires login, shows the status table for sensors. '''
    junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
    return render_to_response('graph/maintenance/status.html',
                              {'sensor_groups': _get_sensor_groups()[0],
                               'data_url': reverse('energyweb.graph.views.mon_status_data')
                               + '?junk=' + junk},
                              context_instance=RequestContext(request))

@login_required
def data_access(request):
    '''                                                                                   
    A view returning the HTML for the unrestricted data download page.
    Two return possibilities:
       1) Did not input data yet
       2) Input valid data
    '''

    def _request_valid(request):
        return request.method == 'GET' \
               and 'start_0' in request.GET \
               and 'end_0' in request.GET \
               and 'res' in request.GET

    def _clean_input(get):
        # *_0 gives date, *_1 gives time in 12 hr w/ AM or PM
        for field in ('start_0', 'start_1', 'end_0', 'end_1'):
            if field in ('start_1', 'end_1'):
                # Allow e.g. pm or p.m. instead of PM
                get[field] = get[field].upper().replace('.', '')
                # Allow surrounding whitespace
            get[field] = get[field].strip()
        return get

    def _show_only_form():
        '''
        Refuse to show them a graph until they give you good parameters
        '''
        now = datetime.datetime.now()
        one_day_ago = now - datetime.timedelta(1)
        form = StaticGraphForm(initial={
            'start': one_day_ago,
            'end': now
        })
        return render_to_response('graph/maintenance/data_access.html',
            {'form_action': reverse('energyweb.graph.views.data_access'),
             'form': form},
            context_instance=RequestContext(request))
    # BEGIN Case 1
    if not _request_valid(request):
        return _show_only_form()

    _get = _clean_input(request.GET.copy())
    form = StaticGraphForm(_get)

    # We've passed the checks, now can display the graph!
    # The following functions are for setting the various arguments
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']
    res = form.cleaned_data['computed_res']

    # js_* is in the format for the Flot plotting package.
    int_start = int(calendar.timegm(start.timetuple()))
    int_end = int(calendar.timegm(end.timetuple()))
    junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
    keyword_args = {'start': str(int_start),
                    'end': str(int_end),
                    'res': res}

    # generate the URLs for data dumps
    download_url = reverse('energyweb.graph.views.download_csv',
                           kwargs=keyword_args) + '?junk=' + junk

    final_args = {
                  'download_url': download_url,
                  'form': form,
                  'form_action': reverse('energyweb.graph.views.data_access'),
                  'res': res}

    return render_to_response('graph/maintenance/data_access_graph.html',
                              final_args,
                              context_instance=RequestContext(request))

@login_required
def data_access_data(request, start, end, res):
    '''
    A view returning the JSON data used to populate the static graph.
    '''

    data_dump = _make_data_dump(start, end, res)

    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(data_dump),
                        mimetype='application/json')

@login_required
def logs(request):
    return render_to_response('graph/maintenance/logs.html',
                              context_instance=RequestContext(request))

def logout(request):
    ''' Log a user out then redirect to main page of energyweb site'''
    from django.contrib.auth import logout
    
    logout(request)
    return HttpResponseRedirect('/graph/')

@login_required
def change_password(request, template_name='registration/password_change_form.html'):
    ''' Let a user change their password by entering their old password'''
    from django.contrib.auth.forms import PasswordChangeForm
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/graph/status/')
    else:
        form = PasswordChangeForm(request.user)
    return render_to_response('registration/password_change_form.html', {'form': form,}, context_instance=RequestContext(request))


if settings.DEBUG:
    def _html_wrapper(view_name):
        '''
        Wrap a view in HTML.  (Useful for using the debug toolbar with
        JSON responses.)
        '''
        view = globals()[view_name]
        def _view(*args, **kwargs):
            response = view(*args, **kwargs)
            return HttpResponse('''
                                <html>
                                    <head><title>%s HTML</title></head>
                                    <body>%s</body>
                                </html>
                                ''' % (view_name, response.content), 
                                mimetype='text/html')
        return _view

    dynamic_graph_data_html = _html_wrapper('dynamic_graph_data')
    static_graph_data_html = _html_wrapper('static_graph_data')
