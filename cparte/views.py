from celery.result import AsyncResult
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.conf import settings

import apps
import logging
import models


logger = logging.getLogger(__name__)


def index(request):
    return HttpResponse("Welcome to Participa!")


def posts(request):
    contribution_posts = models.ContributionPost.objects.all()
    context = {'posts': contribution_posts}
    return render(request, 'cparte/posts.html', context)


def listen(request, channel_name):
    initiatives = [1, 2]   # Add here the ids of the initiatives

    if apps.channel_middleware.channel_enabled(channel_name):
        apps.channel_middleware.listen(initiatives, channel_name)
    else:
        logger.error("The channel is not enabled")
    if hasattr(settings, 'URL_PREFIX') and settings.URL_PREFIX:
        redirect_url = "%s/admin/cparte/channel/" % settings.URL_PREFIX
    else:
        redirect_url = "/admin/cparte/channel/"
    return HttpResponseRedirect(redirect_url)


def hangup(request, channel_name):
    task_id = apps.channel_middleware.disconnect(channel_name)
    task = AsyncResult(task_id)
    if not task.ready():
        # Force to hangup if the channel wasn't disconnected already
        task.revoke(terminate=True)
        logger.info("Channel %s was forced to disconnect" % channel_name)
    else:
        logger.info("Channel %s was already disconnected" % channel_name)
    if hasattr(settings, 'URL_PREFIX') and settings.URL_PREFIX:
        redirect_url = "%s/admin/cparte/channel/" % settings.URL_PREFIX
    else:
        redirect_url = "/admin/cparte/channel/"
    return HttpResponseRedirect(redirect_url)