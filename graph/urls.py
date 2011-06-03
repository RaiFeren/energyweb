"""
Contains regexs for the URLS.
Used so the graphs can parse URL into input for the graphing functions
"""

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('energyweb.graph.views',
    (r'^$', 'dynamic_graph'), # home page -- Dynamic graph
    (r'^(?P<data>\d+)/data.json$', 'dynamic_graph_data'), # data dump for it
    (r'^(?P<data>\d+)/averages_data.json$', 'statistics_table_data'),
    (r'^detail/(?P<building>\d+)/$','detail_graphs'), # details page -- for building views
    (r'^detail/(?P<building>\d+)/(?P<mode>[a-z]+)/(?P<resolution>[a-z]+)/(?P<start_time>\d+)/data.json$','detail_graphs_data'),
    (r'^interface/$', 'data_interface'), # Energy Statistics Table
    (r'^interface/(?P<data>\d+)/data.json$', 'statistics_table_data'),
    (r'^static/$', 'static_graph'), # Custom Graph -- For user defined time ranges
    (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.json$', 'static_graph_data'),
    (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.csv$', 'download_csv'),
    (r'^status/$', 'mon_status'), # Status Page, for telling if the sensors work
    (r'^status/data.json$', 'mon_status_data'),
)

if settings.DEBUG:
    # Add views for HTML-wrappings of the JSON data views.
    urlpatterns += patterns('energyweb.graph.views',
        (r'^(?P<data>\d+)/data.json.html$', 'dynamic_graph_data_html'),
        (r'^static/(?P<start>\d+)/to/(?P<end>\d+)/(?P<res>[a-z]+(\*10)?)/data.json.html$', 'static_graph_data_html'),
    )
