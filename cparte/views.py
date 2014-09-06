from multiprocessing import Process
from django.http import HttpResponse
from django.shortcuts import render

from cparte.models import Campaign, MetaChannel, Channel

import logging


logger = logging.getLogger(__name__)


meta_channel = MetaChannel(initiative="California Report Card")


def count_and_print():
    a = 0
    while a <= 1000000:
        a += 1
        logger.info(a)


def index(request):
    p = Process(target=count_and_print)
    p.start()
    return HttpResponse("Welcome to the CParte application!")


def posts(request):
    latest_campaigns = Campaign.objects.all()[:5]
    context = {'latest_campaigns': latest_campaigns}
    return render(request, 'cparte/posts.html', context)


def listen(request, channel):
    app_account_id = Channel.objects.get(name=channel).app_account_id
    if channel == "all":
        msg = "Start listening all channels..."
        meta_channel.authenticate()
        meta_channel.listen(followings=app_account_id)
    else:
        msg = "Start listening %s channel..." % channel
        meta_channel.authenticate(channel)
        meta_channel.listen(channel=channel, followings=[app_account_id])
    #request.session['meta_channel'] = serializers.serialize("json", meta_ch, ignorenonexistent=True)
    logger.info(msg)
    return HttpResponse(msg)


def hangup(request, channel):
    #meta_ch = serializers.deserialize("json", request.session['meta_channel'])
    if meta_channel is not None:
        if channel == "all":
            meta_channel.disconnect()
            msg = "All channels disconnected..."
        else:
            meta_channel.disconnect(channel)
            msg = "Channel %s has been disconnected..." % channel
    else:
        msg = "No channels listening..."
    logger.info(msg)
    return HttpResponse(msg)