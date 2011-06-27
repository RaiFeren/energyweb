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
    return {'dynamic_graph_url': reverse('energyweb.graph.views.dynamic_graph'),
            'static_graph_url': reverse('energyweb.graph.views.static_graph'),
            'status_url': reverse('energyweb.graph.views.mon_status'),
            'energy_table_url': reverse('energyweb.graph.views.energy_table'),
            'detail_url': reverse('energyweb.graph.views.detail_graph' ,
                                  kwargs={'building':'east','mode':'cycle',
                                          'res':'day'}),
            'logs_url': reverse('energyweb.graph.views.logs'),
            'data_access_url': reverse('energyweb.graph.views.data_access'),
            'admin_url': '/admin/',
            'logout_url': reverse('energyweb.graph.views.logout'),
            'change_password_url': reverse('energyweb.graph.views.change_password'),
            }

