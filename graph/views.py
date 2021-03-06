'''
    Used to select a template and generate contexts to fill it.

    Contexts generated by this file will override any generated by
    context_processors.py. Use this for page specific contexts.

    Several of these contexts will be generated by looking stuff
    up in the database. Use data.py for any lookup functions.

    Notes:
        Might be inconsistent across files with datetime.datetime.now()
        or datetime.datetime.utcnow()
'''

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

DYNAMIC_START_TIME = datetime.timedelta(0,3600*2,0)

def energy_table(request):
    '''
    A view returning the HTML for the dynamic table.
    This table holds curr. use (minute avg) and avg of past week/month.
    '''
    data.increase_count(DYNAMIC_TABLE)

    # Get data from three hours ago until now.
    (startTime, junk) = \
                data._generate_start_data( DYNAMIC_START_TIME )

    return render_to_response('graph/energy_table.html', 
        {'sensor_groups': data.SENSOR_GROUPS,
         'data_url': reverse('energyweb.graph.views.statistics_table_data'
                             ) + '?junk=' + junk,
         'scope': 'residential'},
        context_instance=RequestContext(request))

def energy_table_mode(request,scope):
    '''
    Generates a data table with the ability to set 'scope'
    Scope refers either to Academic Buildings, Residential Buildings, or All
    Table reports averages over last minute, week, month.
    '''
    data.increase_count(DYNAMIC_TABLE)

    (startTime, junk) = \
        data._generate_start_data( DYNAMIC_START_TIME )

    if SHOW_ACADEMIC:
        snrgrp = data.SENSOR_GROUPS
        if str(scope) == 'academic':
            snrgrp = data.ACADEMIC_SENSORGROUPS
        elif str(scope) == 'residential':
            snrgrp = data.RESIDENTIAL_SENSORGROUPS
        return render_to_response('graph/table_all.html',
                        {'sensor_groups': snrgrp,
                         'data_url': reverse(
                             'energyweb.graph.views.statistics_table_data'
                             ) + '?junk=' + junk,
                         'scope': scope,
                         'dynamic_graph_url': reverse(
                             'energyweb.graph.views.dynamic_graph_mode',
                             kwargs={'scope':scope}),
                         'energy_table_url':reverse(
                             'energyweb.graph.views.energy_table_mode',
                             kwargs={'scope':scope})
                         },
                    context_instance=RequestContext(request))
    else:
        return energy_table(request)    

def statistics_table_data(request):
    '''
    A view returning the JSON data used to populate the averages table.
    '''
    all_averages = data._get_averages()

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
    (This graph represents the last two hours and updates
    automatically.)
    '''
    data.increase_count(DYNAMIC_GRAPH)

    # Get all data from last two hours until now
    (start_date, junk) = \
        data._generate_start_data( DYNAMIC_START_TIME )

    return render_to_response('graph/dynamic_graph.html', 
        {'sensor_groups': data.SENSOR_GROUPS,
         'data_url': reverse('energyweb.graph.views.dynamic_graph_data', 
                             kwargs={'input_data': start_date}) +\
             '?junk=' + junk,
         'scope':'residential'},
        context_instance=RequestContext(request))

def dynamic_graph_mode(request,scope):
    '''
    Generates a dynamic graph with the ability to set 'scope'
    Scope refers either to Academic Buildings, Residential Buildings, or All
    '''
    data.increase_count(DYNAMIC_GRAPH)

    # Get all data from last two hours until now
    (start_date, junk) = \
        data._generate_start_data( DYNAMIC_START_TIME )

    if SHOW_ACADEMIC:        
        return render_to_response('graph/dynamic_all.html',
                {'sensor_groups': data.ACADEMIC_SENSORGROUPS,
                 'data_url': reverse('energyweb.graph.views.dynamic_graph_data',
                                     kwargs={'input_data': start_date}
                                     ) + '?junk=' + junk,
                 'scope':scope,
                 'dynamic_graph_url': reverse(
                    'energyweb.graph.views.dynamic_graph_mode', 
                    kwargs={'scope':scope}),
                 'energy_table_url':reverse(
                    'energyweb.graph.views.energy_table_mode',
                    kwargs={'scope':scope})
                 },
                                  context_instance=RequestContext(request))
    else:
        return dynamic_graph(request)

def dynamic_graph_data(request, input_data):
    '''
    A view returning the JSON data used to populate the dynamic graph.
    '''
    # Set the maximum possible start time to two hours ago
    # to prevent excessive drawing of data
    max_time = datetime.datetime.now() -DYNAMIC_START_TIME
    start = max( datetime.datetime.utcfromtimestamp(int(int(input_data)/1000)) ,
                 max_time )
    
    # Grab the xy pairs
    data_dump = data._make_data_dump( calendar.timegm(start.timetuple()) ,
                        None,
                        'second*10')

    if not data_dump['no_results']:
        # Create the URL to refresh for more data
        junk = data._gen_now()
        data_url = reverse('energyweb.graph.views.dynamic_graph_data', \
                           kwargs={'input_data': \
                                   str(data_dump['last_record'])}) + \
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
    # Increase the viewCount for today
    data.increase_count(CUSTOM)

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
    
    # int_* is in seconds. REMEMBER highcharts needs milliseconds!
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
                  'res': RESOLUTION_DELTAS[res].seconds,
                  'timedelta_ms': (int_end-int_start)*1000}
    
    return render_to_response('graph/static_graph.html', 
                              final_args,
                              context_instance=RequestContext(request))

def static_graph_data(request, start, end, res):
    '''
    A view returning the JSON data used to populate the static graph.
    '''
    # Increase the viewCount for today
    data.increase_count(CUSTOM_GRAPH)

    data_dump = data._make_data_dump(start, end, res)
    
    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(data_dump),
                        mimetype='application/json')

def download_csv(request, start, end, res):
    # Increase the viewCount for today
    data.increase_count(DATA_DOWNLOAD)
    return data.download_csv(request, start, end, res)

def detail_graph(request, building, mode, res):
    '''
    A view returning the HTML for the Detailed Building graph.
    (This graph represents the last three hours and updates
    automatically.)
    '''
    # Increase the viewCount for today
    data.increase_count(DETAILED_VIEW)

    # Get the current date.
    (start_data, junk) = data._generate_start_data( datetime.timedelta(0,0,0) )

    d = {'data_url': reverse('energyweb.graph.views.detail_graph_data', 
                             kwargs={'building': building,
                                     'resolution':res,
                                     'start_time':start_data}) +\
         '?junk=' + junk,
         'table_url': reverse('energyweb.graph.views.detail_table_data', 
                             kwargs={'building': building,
                                     'resolution':res,
                                     'start_time':start_data}) +\
         '?junk=' + junk,
         'building': building.capitalize(),
         'mode': mode,
         'res': res,
         'timedelta_ms': data._dt_to_sec(RESOLUTION_DELTAS[res])*1000,
        }

    # Set the URLs for changing time periods.
    for time_period in ['day','week','month','year']:
        d[time_period+'_url'] = reverse('energyweb.graph.views.detail_graph',
                                        kwargs={'building':building,
                                                'mode':mode,
                                                'res':time_period})
    # Set the URLs for changing modes
    for mode_setting in ['cycle','diagnostic']:
        d[mode_setting+'_url'] = reverse('energyweb.graph.views.detail_graph',
                                        kwargs={'building':building,
                                                'mode':mode_setting,
                                                'res':res})
    # Change Building URLs
    for building in ['south','north','west','east',\
                         'sontag','atwood','case','linde']:
        d[building+'_url'] = reverse('energyweb.graph.views.detail_graph' ,
                                     kwargs={'building':building,
                                             'mode':mode,'res':res})

    return render_to_response('graph/detail_graphs.html',d,
        context_instance=RequestContext(request))


def detail_graph_data(request, building, resolution, start_time):
    '''
    A view returning the JSON data used to populate the Detailed graph.
    '''
    returnDictionary = data._get_detail_data(building,
                                             resolution,
                                             start_time)

    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(returnDictionary),
                        mimetype='application/json')

def detail_table_data(request, building, resolution, start_time):
    '''
    A view returning the JSON data used to populate the Detailed Table.
    '''
    returnDictionary = data._get_detail_table(building,
                                             resolution,
                                             start_time)

    json_serializer = serializers.get_serializer("json")()
    return HttpResponse(simplejson.dumps(returnDictionary),
                        mimetype='application/json')

def signal_processing_data(request):
    """
    Generates data for the monitor status page
    """
    junk = data._gen_now()

    sreadings = dict()
    for s_id in data.SENSOR_IDS:
        sreadings[s_id] = [None, None, None, None]
        try:
            sr = SensorReading.objects.filter(sensor__id=s_id).latest('reading_time')
            sreadings[s_id][0] = int(
                calendar.timegm(sr.reading_time.timetuple()) * 1000)
        except SensorReading.DoesNotExist:
            pass
        # TODO: magic number
        d = SRProfile.objects.filter(
            sensor_reading__sensor__id=s_id,
            sensor_reading__reading_time__gte=(
                datetime.datetime.now() - datetime.timedelta(1))
            ).aggregate(
            Avg('transaction_time'), 
            Min('transaction_time'),
            Max('transaction_time')) 
        sreadings[s_id][1] = int(d['transaction_time__avg'])
        sreadings[s_id][2] = d['transaction_time__min']
        sreadings[s_id][3] = d['transaction_time__max']
    return HttpResponse(simplejson.dumps({'sensor_readings': sreadings,
                                          'sensor_groups': data.SENSOR_GROUPS,
                                          'data_url': reverse(
                                              'energyweb.graph.views.signal_processing_data')
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
def signal_processing(request):
    ''' Requires login, shows the status table for sensors. '''
    # Increase the viewCount for today
    data.increase_count(SIGNAL_PROCESSING)

    junk = str(calendar.timegm(datetime.datetime.now().timetuple()))
    return render_to_response('graph/maintenance/processing.html',
                        {'sensor_groups': data._get_sensor_groups()[0],
                         'data_url': reverse(
                             'energyweb.graph.views.signal_processing_data')
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
    # Increase the viewCount for today
    data.increase_count(DATA_ACCESS)

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

import os
@login_required
def system_status(request):
    # Increase the viewCount for today
    data.increase_count(SYSTEM_STATUS)

    status_list = data.getLastStatus()
    load = os.getloadavg()
    status_data = {
        'data': status_list,
        'load': [load[0], load[1], load[2]],}
    return render_to_response('graph/maintenance/status.html',
                              status_data,
                              context_instance=RequestContext(request))

@login_required
def detaillog(request, id_num, lvl, sens_type):
    # Increase the viewCount for today
    data.increase_count(MON_STATUS)

    log_list = data.grabLogs(sens_type, lvl, id_num)
    loc = Sensor.objects.filter(pk=id_num)[0].sensor_group.name
    dict_to_render = {
        'log_data': log_list,
        'id_num': id_num,
        'lvl': lvl,
        'sens_type': sens_type,
        'location': loc,}
    return render_to_response('graph/maintenance/generic_log.html',
                              dict_to_render,
                              context_instance=RequestContext(request))
    
@login_required
def server_stats(request):
    # Increase the viewCount for today
    data.increase_count(SERVER_STATS)

    dict_to_render = data.system_statistics()
    dict_to_render["numstatlist"] = range(1, len(dict_to_render["mem"]))
    dict_to_render["viewCounts"] = data.viewCountStats()
    return render_to_response('graph/maintenance/server.html',
                              dict_to_render,
                              context_instance=RequestContext(request))

def logout(request):
    ''' Log a user out then redirect to main page of energyweb site'''
    from django.contrib.auth import logout
    
    logout(request)
    return HttpResponseRedirect('/graph/')

@login_required
def change_password(request,
                    template_name='registration/password_change_form.html'):
    ''' Let a user change their password by entering their old password'''
    from django.contrib.auth.forms import PasswordChangeForm
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/graph/status/')
    else:
        form = PasswordChangeForm(request.user)
    return render_to_response(
        'registration/password_change_form.html',
        {'form': form,},
        context_instance=RequestContext(request))


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
