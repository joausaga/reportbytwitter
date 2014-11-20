from celery.result import AsyncResult
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.conf import settings

import channel_middleware
import ConfigParser
import logging
import models
import os


logger = logging.getLogger(__name__)


def index(request):
    return HttpResponse("Welcome to Participa!")


def posts(request):
    contribution_posts = models.ContributionPost.objects.all()
    context = {'posts': contribution_posts}
    return render(request, 'cparte/posts.html', context)


def listen(request, channel_name):
    initiatives = [1, 2]   # Add here the ids of the initiatives

    channel_middleware.connect(initiatives, channel_name)
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(settings.BASE_DIR, "cparte/config"))
    subdomain = config.get("app","subdomain")
    if subdomain:
        redirect_url = "%s/admin/cparte/channel/" % subdomain
    else:
        redirect_url = "/admin/cparte/channel/"
    return HttpResponseRedirect(redirect_url)


def hangup(request, channel_name):
    task_id = channel_middleware.disconnect(channel_name)
    task = AsyncResult(task_id)
    if not task.ready():
        # Force to hangup if the channel wasn't disconnected already
        task.revoke(terminate=True, signal='SIGTERM')
        logger.info("Channel %s was forced to disconnect" % channel_name)
    else:
        logger.info("Channel %s was already disconnected" % channel_name)
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(settings.BASE_DIR, "cparte/config"))
    subdomain = config.get("app","subdomain")
    if subdomain:
        redirect_url = "%s/admin/cparte/channel/" % subdomain
    else:
        redirect_url = "/admin/cparte/channel/"
    return HttpResponseRedirect(redirect_url)