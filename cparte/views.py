#from multiprocessing import Process
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from cparte.models import MetaChannel, Channel, ContributionPost

import logging


logger = logging.getLogger(__name__)


def index(request):
    #p = Process(target=count_and_print)
    #p.start()
    return HttpResponse("Welcome to the CParte application!")


def posts(request):
    contribution_posts = ContributionPost.objects.all()
    context = {'posts': contribution_posts}
    return render(request, 'cparte/posts.html', context)


def listen(request, channel_name):
    initiatives = [1,2]   # Add here the ids of the initiatives
    accounts = [1]  # Add here the ids of the accounts
    MetaChannel.authenticate(channel_name=channel_name)
    MetaChannel.listen(channel_name=channel_name, followings=accounts, initiatives=initiatives)
    return HttpResponseRedirect("/admin/cparte/channel/")


def hangup(request, channel_name):
    MetaChannel.disconnect(channel_name)
    return HttpResponseRedirect("/admin/cparte/channel/")