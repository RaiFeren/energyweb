"""
Contains regexs for the URLS.
Used so the graphs can parse URL into input for the graphing functions
"""

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('energyweb.graph.views',
    (r'^$', 'dynamic_graph'), # home page -- Dynamic graph
    (r'^(?P<input_data>\d+)/data.json$', 'dynamic_graph_data'), # data dump for it
    (r'^detail/(?P<building>[a-z]+)/(?P<res>[a-z]+)/$','detail_graphs'), # details page -- for building views
    (r'^detail/(?P<building>[a-z]+)/(?P<mode>[a-z]+)/(?P<resolution>[a-z]+)/(?P<start_time>\d+)/data.json$','detail_graphs_data'),
    (r'^energytable/$', 'energy_table'), # Energy Statistics Table
    (r'^energytable/data.json$', 'statistics_table_data'),
    (r'^static/$', 'static_graph'), # Custom Graph -- For user defined time ranges
    (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.json$', 'static_graph_data'),
    (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.csv$', 'download_csv'),
    (r'^status/$', 'mon_status'), # Status Page, for telling if the sensors work
    (r'^status/data.json$', 'mon_status_data'),
    (r'^logs/$', 'logs'),
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
