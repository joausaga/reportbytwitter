from django.conf.urls import patterns, url
from cparte import views

urlpatterns = patterns('',
    # ex: /cparte/
    url(r'^$', views.index, name='index'),
    # ex: /cparte/posts/
    url(r'^posts/$', views.posts, name='posts'),
    # ex: /cparte/listen/twitter or /cparte/listen/all
    url(r'^listen/(?P<channel>[a-z]+)$', views.listen, name='listen'),
    # ex: /cparte/hangup/twitter or /cparte/hangup/all
    url(r'^hangup/(?P<channel>[a-z]+)$', views.hangup, name='hangup'),
)