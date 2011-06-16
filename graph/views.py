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

import energyweb.graph.data as data

def data_interface(request):
    '''
    A view returning the HTML for the dynamic table.
    This table holds curr. use and avg of past week/month.
    '''
    # Get data from three hours ago until now.
    (startTime, junk) = \
                data._generate_start_data( datetime.timedelta(0,3600*3,0) )

    return render_to_response('graph/data_interface.html', 
        {'sensor_groups': data.SENSOR_GROUPS,
         'data_url': reverse('energyweb.graph.views.statistics_table_data'
                             ) + '?junk=' + junk},
        context_instance=RequestContext(request))

def statistics_table_data(request):
    '''
    A view returning the JSON data used to populate the averages table.
    '''
    all_averages = data._get_averages(data.SENSOR_IDS)

    data_url = reverse('energyweb.graph.views.statistics_table_data') \
               +'?junk=' + data._gen_now()

    # Create the final return dictionary
    d = {
        'no_results': False,
        'min_averages': all_averages['minute'],
        'week_averages': all_averages['week'],
        'month_averages': all_averages['month'],
        'sensor_groups': data.SENSOR_GROUPS,
        'data_url': data_url
        }
             
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
    (start_date, junk) = \
        data._generate_start_data( datetime.timedelta(0,3600*3,0) )

    return render_to_response('graph/dynamic_graph.html', 
        {'sensor_groups': data.SENSOR_GROUPS,
         'data_url': reverse('energyweb.graph.views.dynamic_graph_data', 
                             kwargs={'input_data': start_date}) +\
             '?junk=' + junk},
        context_instance=RequestContext(request))


def dynamic_graph_data(request, input_data):
    '''
    A view returning the JSON data used to populate the dynamic graph.
    '''
    # Set the maximum possible start time to three hours ago
    # to prevent excessive drawing of data
    max_time = datetime.datetime.now() - datetime.timedelta(0,3600*3,0)
    start = max( datetime.datetime.utcfromtimestamp(int(int(input_data)/1000)) ,
                 max_time )
    # Grab the dump of xy pairs
    data_dump = data._make_data_dump( calendar.timegm(start.timetuple()) ,
                                None,
                                'second*10')

    if not data_dump['no_results']:
        # Create the URL to get more data
        junk = data._gen_now()
        data_url = reverse('energyweb.graph.views.dynamic_graph_data', \
                               kwargs={'input_data': \
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
        form = data.StaticGraphForm(initial={
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
    form = data.StaticGraphForm(_get)

    if not form.is_valid():
        return _show_only_form()
    # We've passed the checks, now can display the graph!

    # The following functions are for setting the various arguments
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']
    res = form.cleaned_data['computed_res']
    
    # int_* is in seconds. REMEMBER flot needs milliseconds!
    int_start = int(calendar.timegm(start.timetuple()))
    int_end = int(calendar.timegm(end.timetuple()))

    junk = data._gen_now()
    keyword_args = {'start': str(int_start), 
                    'end': str(int_end), 
                    'res': res}
    
    # generate the URLs for data dumps
    data_url = reverse('energyweb.graph.views.static_graph_data',
                       kwargs=keyword_args) + '?junk=' + junk
    
    download_url = reverse('energyweb.graph.views.download_csv',
                           kwargs=keyword_args) + '?junk=' + junk

    final_args = {'start': int_start*1000,
                  'end': int_end*1000,
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
    data_dump = data._make_data_dump(start, end, res)
    
    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(data_dump),
                        mimetype='application/json')

def download_csv(request, start, end, res):
    return data.download_csv(request, start, end, res)

def detail_graphs(request, building, res):
    '''
    A view returning the HTML for the Detailed Building graph.
    (This graph represents the last three hours and updates
    automatically.)
    '''
    # Get the current date.
    (start_data, junk) = data._generate_start_data( datetime.timedelta(0,0,0) )

    d = {
        'data_url': reverse('energyweb.graph.views.detail_graphs_data', 
                            kwargs={'building': building,
                                    'mode':'cycle',
                                    'resolution':res,
                                    'start_time':start_data}) + '?junk=' + junk,
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

    # Because transferring non-strings over gets annoying,
    # this is how we'll get buildings
    cur_building = None
    for sg in data.SENSOR_GROUPS:
        if sg[1].lower() == str(building): # check if identical names
            cur_building = sg

    average_data = {}
    all_averages = data._get_averages(data.SENSOR_IDS)
    for sid in data.SENSOR_IDS_BY_GROUP[cur_building[0]]:
        average_data[sid] = {}
        for average_type in all_averages.keys():
            average_data[sid][average_type] = \
                all_averages[average_type][sid]

    returnDictionary = {'graph_data':[]}

    for start_time_delta in range(len(CYCLE_START_DELTAS[resolution])):

        start_dt = datetime.datetime.utcfromtimestamp(
            int(start_time) / 1000 - 
            CYCLE_START_DELTAS[resolution][start_time_delta].seconds - 
            CYCLE_START_DELTAS[resolution][start_time_delta].days*3600*24 )
                   
        PowerAverage.graph_data_execute(cur,
                                        AUTO_RES_CONVERT[resolution],
                                        start_dt,
                                        start_dt + \
                                        RESOLUTION_DELTAS[resolution])

        # If data was supplied then we selected everything since
        # the provided timestamp's truncated date, including that date.
        # We will always provide the client with
        # a new copy of the latest record he received last time, since
        # that last record may have changed (more sensors may have
        # submitted measurements and added to it).  The second to
        # latest and older records, however, will never change.

        
        # Now organize the query in a format amenable to the 
        # (javascript) client.  (The grapher wants (x, y) pairs.)
        
        # dictionary has keys of total and then the sensor ids
        xy_pairs = {'total':[]}
        for sensor_id in data.SENSOR_IDS_BY_GROUP[cur_building[0]]:
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
                # Need to adjust start time such that all
                # x values are actually the same.
                # So lines will show on same axis.
                if not start_time_delta == 0:
                    old_cycle = CYCLE_START_DELTAS[resolution][start_time_delta]

                    x += old_cycle.seconds*1000 +\
                         old_cycle.days*3600*24*1000 -\
                         CYCLE_START_DELTAS[resolution][0].seconds*1000 -\
                         CYCLE_START_DELTAS[resolution][0].days*3600*24*1000

                xy_pairs['total'].append([x,0])
                for sg in data.SENSOR_GROUPS:
                    for sid in data.SENSOR_IDS_BY_GROUP[sg[0]]:
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
                junk = data._gen_now()
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
    """
    Generates data for the monitor status page
    """
    junk = data._gen_now()

    sreadings = dict()
    for s_id in data.SENSOR_IDS:
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
                                          'sensor_groups': data.SENSOR_GROUPS,
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
                              {'sensor_groups': data._get_sensor_groups()[0],
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
        form = data.CustomGraphForm(initial={
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
    form = data.CustomGraphForm(_get)

    if not form.is_valid():
        return _show_only_form()

    # We've passed the checks, now can display the graph!
    # The following functions are for setting the various arguments
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']
    res = form.cleaned_data['computed_res']


    int_start = int(calendar.timegm(start.timetuple()))
    int_end = int(calendar.timegm(end.timetuple()))
    junk = data._gen_now()
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

    data_dump = data._make_data_dump(start, end, res)

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
