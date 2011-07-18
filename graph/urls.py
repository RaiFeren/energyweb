"""
    Contains regexs for the URLS.
    Used so the graphs can parse URL into input for the graphing functions.
"""

from django.conf.urls.defaults import *
from django.conf import settings
from constants import *

# $ allows for any thing to follow. Most notably junk fields to avoid cache issues
urlpatterns = patterns('energyweb.graph.views',
    (r'^$', 'dynamic_graph_mode',{'scope':'residential'}), # home page -- Dynamic graph
    (r'^dynamic_(?P<scope>[a-z]+)/$', 'dynamic_graph_mode'),
    (r'^table_(?P<scope>[a-z]+)/$', 'energy_table_mode'),
    (r'^(?P<input_data>\d+)/data.json$', 'dynamic_graph_data'), # data dump for it
    (r'^detail/(?P<building>[a-z]+)/(?P<mode>[a-z]+)/(?P<res>[a-z]+)/$','detail_graph'), # details page -- for building views
    (r'^detail/(?P<building>[a-z]+)/(?P<resolution>[a-z]+)/(?P<start_time>\d+)/graph_data.json$','detail_graph_data'),
    (r'^detail/(?P<building>[a-z]+)/(?P<resolution>[a-z]+)/(?P<start_time>\d+)/table_data.json$','detail_table_data'),
    (r'^energytable/$', 'energy_table_mode',{'scope':'residential'}), # Energy Statistics Table
    (r'^energytable/data.json$', 'statistics_table_data'),
    (r'^static/$', 'static_graph'), # Custom Graph -- For user defined time ranges
    (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.json$', 'static_graph_data'),
    (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.csv$', 'download_csv'),
    (r'^processing/$', 'signal_processing'), # Status Page, for telling if the sensors work
    (r'^processing/data.json$', 'signal_processing_data'),
    (r'^status/$', 'system_status'),
    (r'^status/server/$', 'server_stats'),
    (r'^status/(?P<id_num>\d{1,2})/(?P<sens_type>[MF])/(?P<lvl>[AESW])/$', 'detaillog'),
    (r'^dataaccess/$', 'data_access'),
    (r'^dataaccess/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.json$', 'data_access_data'),
    (r'^dataaccess/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.csv$', 'download_csv'),
    (r'^logout/$', 'logout'),
    (r'^changepass/$', 'change_password'),
)

'''
# Admin site:
urlpatters += patterns('',
    (r'^admin/', include(admin.site.urls)),
)
'''
if settings.DEBUG:
    # Add views for HTML-wrappings of the JSON data views.
    urlpatterns += patterns('energyweb.graph.views',
        (r'^(?P<data>\d+)/data.json.html$', 'dynamic_graph_data_html'),
        (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.json.html$', 'static_graph_data_html'),
    )
