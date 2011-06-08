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
                                  kwargs={'building':'atwood'}),
            }

def detail_views_urls(request):
    '''
    Return URLs used in generating detail views page
    '''
    from django.core.urlresolvers import reverse
    return {
        'atwood_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'atwood'}),
        'case_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'case'}),
        'sontag_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'sontag'}),
        'linde_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'linde'}),
        'east_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'east'}),
        'north_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'north'}),
        'west_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'west'}),
        'south_url': reverse('energyweb.graph.views.detail_graphs' ,
                              kwargs={'building':'south'}),
        }
