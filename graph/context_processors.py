'''
    Defines contexts shared across all templates.
    (definition- Context: Variables for the Django Templates)
    Can be overwritten by contexts generated in views.py.

    important functions:
        reverse(FUNCTION_NAME_IN_views.py, KWARGS_dictionary)
            generates the URL. reverse as in "Reverse the regular expression"
            to generate instead of matching patterns.
            See urls.py for the regexs.
'''

def media_url(request):
    '''
    Return the URL used for site media.
    '''
    from django.conf import settings
    return {'media_url': settings.MEDIA_URL}

def nav_urls(request):
    '''
    Return URLs used in generating the navigation bar.
    '''
    from django.core.urlresolvers import reverse
    return {'dynamic_graph_url': reverse('energyweb.graph.views.dynamic_graph_mode',
                                         kwargs={'scope':'residential'}),
            'static_graph_url': reverse('energyweb.graph.views.static_graph'),
            'processing_url': reverse('energyweb.graph.views.signal_processing'),
            'energy_table_url': reverse('energyweb.graph.views.energy_table_mode',
                                         kwargs={'scope':'residential'}),
            'detail_url': reverse('energyweb.graph.views.detail_graph' ,
                                  kwargs={'building':'east','mode':'cycle',
                                          'res':'day'}),
            'status_url': reverse('energyweb.graph.views.system_status'),
            'server_stat_url': reverse('energyweb.graph.views.server_stats'),
            'data_access_url': reverse('energyweb.graph.views.data_access'),
            'admin_url': '/admin/',
            'logout_url': reverse('energyweb.graph.views.logout'),
            'change_password_url': reverse('energyweb.graph.views.change_password'),
            'dynamic_ac_url': reverse('energyweb.graph.views.dynamic_graph_mode',
                                      kwargs={'scope':'academic'}),
            'dynamic_all_url': reverse('energyweb.graph.views.dynamic_graph_mode',
                                      kwargs={'scope':'all'}),
            'dynamic_res_url': reverse('energyweb.graph.views.dynamic_graph_mode',
                                      kwargs={'scope':'residential'}),
            'table_ac_url': reverse('energyweb.graph.views.energy_table_mode',
                                    kwargs={'scope':'academic'}),
            'table_all_url': reverse('energyweb.graph.views.energy_table_mode',
                                     kwargs={'scope':'all'}),
            'table_res_url': reverse('energyweb.graph.views.energy_table_mode',
                                     kwargs={'scope':'residential'}),
            }
