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
            'mon_status_url': reverse('energyweb.graph.views.mon_status'),
            'data_interface_url': reverse('energyweb.graph.views.data_interface'),
            'detail_url': reverse('energyweb.graph.views.detail_graphs' ,
                                  kwargs={'building':'atwood','res':'day'}),
            }

def detail_views_urls(request):
    '''
    Return URLs used in generating detail views page
    '''
    from django.core.urlresolvers import reverse
    return {
        'atwood_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'atwood','res':'day'}),
        'case_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'case','res':'day'}),
        'sontag_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'sontag','res':'day'}),
        'linde_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'linde','res':'day'}),
        'east_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'east','res':'day'}),
        'north_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'north','res':'day'}),
        'west_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'west','res':'day'}),
        'south_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'south','res':'day'}),
        }
