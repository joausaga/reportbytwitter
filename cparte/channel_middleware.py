from celery.result import AsyncResult
from django.utils import timezone
from cparte.models import Channel, Initiative, Account, Campaign, AppPost, Challenge, ContributionPost
from social_network import Twitter, Facebook, GooglePlus

import json
import logging
import post_manager

logger = logging.getLogger(__name__)


def process_post(post, channel_name):
    channel_name = channel_name.lower()
    channel = Channel.objects.get(name=channel_name)
    ts_last_message = channel.last_message
    now = timezone.now()
    if ts_last_message is None:
        channel.update_last_message_ts(now)
    else:
        delta = now - ts_last_message
        # Update last message timestamp every 15 minutes
        if (delta.seconds/60) >= 15:
            channel.update_last_message_ts(now)
    post_manager.manage_post(post)


def connect(initiative_ids, channel_name):
    channel_name = channel_name.lower()
    channel = Channel.objects.get(name=channel_name)

    session_info = get_session_info(initiative_ids)
    if channel_name.lower() == "twitter":
        task = Twitter.listen.delay(session_info["accounts"], session_info["hashtags"])
        task_id = task.id
        logger.info("Start listening Twitter channel")
    elif channel_name.lower() == "facebook":
        Facebook.listen(session_info["accounts"], session_info["hashtags"])  # Add .delay
        task_id = None
    elif channel_name.lower() == "googleplus":
        GooglePlus.listen(session_info["accounts"], session_info["hashtags"])  # Add .delay
        task_id = None
    else:
        logger.error("Unknown channel: %s" % channel_name)
        return None
    channel.connect(task_id, json.dumps(session_info))


def get_session_info(initiative_ids):
    hashtags = None
    account_ids = []
    for id_initiative in initiative_ids:
        try:
            initiative = Initiative.objects.get(pk=id_initiative)
        except Initiative.DoesNotExist:
            e_msg = "Does not exist an initiative identified with the id %s" % id_initiative
            logger.critical(e_msg)
            raise Exception(e_msg)

        if hashtags:
            hashtags.append(initiative.hashtag)
        else:
            hashtags = [initiative.hashtag]
        account_ids.append(initiative.account.id)

        # Add to the array of hashtags the hashtags of the initiative's campaigns
        for campaign in initiative.campaign_set.all():
            if campaign.hashtag is not None:
                hashtags.append(campaign.hashtag)
            # Add to the array of hashtags the hashtags of the campaign's challenges
            for challenge in campaign.challenge_set.all():
                hashtags.append(challenge.hashtag)
    accounts = get_accounts(account_ids)
    session_info = {"initiative_ids": initiative_ids, "hashtags": hashtags, "accounts": accounts}

    return session_info


def get_accounts(account_ids):
    accounts = []
    for id_account in account_ids:
        try:
            accounts.append(Account.objects.get(pk=id_account).id_in_channel)
        except Account.DoesNotExist:
            e_msg = "The account identified with the id %s does not exist" % id_account
            logger.critical(e_msg)
            raise Exception(e_msg)
    return accounts


def send_message(channel_name, message, type_msg, payload, recipient_id=None):
    channel_obj = Channel.objects.get(name=channel_name)
    url = channel_obj.url

    if channel_name.lower() == "twitter":
        ret = Twitter.send_message(message, type_msg, payload, recipient_id, url)
        channel = Twitter
    elif channel_name.lower() == "facebook":
        ret = Facebook.send_message(message, type_msg, payload, recipient_id, url)
        channel = Facebook
    elif channel_name.lower() == "googleplus":
        ret = GooglePlus.send_message(message, type_msg, payload, recipient_id, url)
        channel = GooglePlus
    else:
        logger.error("Unknown channel: %s" % channel_name)
        return
    if ret and ret['delivered']:
        app_post = save_post_db(payload, ret['response'], channel_obj)
        if app_post.id is None:
            if channel.delete_post(ret['response']) is not None:
                logger.error("The app post couldn't be saved into the db, so its corresponding post was deleted "
                             "from %s" % channel_name)
            else:
                logger.critical("The app post couldn't be saved into the db, but its corresponding post couldn't be "
                                "delete from %s. The app may be in an inconsistent state" % channel_name)
        else:
            logger.info("The app post with the id: %s was created" % app_post.id)


def save_post_db(payload, response, channel_obj):
    parent_post_id = payload['parent_post_id']
    post_id = payload['post_id']
    type_msg = payload['type_msg']
    initiative_short_url = payload['initiative_short_url']
    initiative = Initiative.objects.get(pk=payload['initiative_id'])
    campaign = Campaign.objects.get(pk=payload['campaign_id'])
    challenge = Challenge.objects.get(pk=payload['challenge_id'])
    recipient_id = payload['author_id']
    if parent_post_id is not None:
        try:
            app_parent_post = AppPost.objects.get(id_in_channel=parent_post_id)
        except AppPost.DoesNotExist:
            app_parent_post = None
    else:
        app_parent_post = None
    try:
        contribution_parent_post = ContributionPost.objects.get(id_in_channel=post_id)
    except ContributionPost.DoesNotExist:
        contribution_parent_post = None
    app_post = AppPost(id_in_channel=response["id"], datetime=timezone.now(), text=response["text"],
                       url=response["url"], app_parent_post=app_parent_post, initiative=initiative, campaign=campaign,
                       contribution_parent_post=contribution_parent_post, challenge=challenge,
                       channel=channel_obj, votes=0, re_posts=0, bookmarks=0, delivered=True,
                       category=type_msg, payload=initiative_short_url, recipient_id=recipient_id, answered=False)
    app_post.save(force_insert=True)
    return app_post


def disconnect(channel_name):
    channel_name = channel_name.lower()
    try:
        ch = Channel.objects.get(name=channel_name)
        task_id = ch.streaming_pid
        ch.disconnect()
        task = AsyncResult(task_id)
        if not task.ready():
            # Force to hangup if the channel wasn't disconnected already
            task.revoke(terminate=True, signal='SIGTERM')
            logger.info("Channel %s was forced to disconnect" % channel_name)
        else:
            logger.info("Channel %s was already disconnected" % channel_name)
    except Channel.DoesNotExist:
        logger.error("Cannot disconnect, channel %s couldn't be found" % channel_name)


# Auto-recovery the channel when it crashes
def auto_recovery(channel_name):
    disconnect(channel_name)
    initiative_ids = [1,2]  # Need to be dynamic
    connect(initiative_ids, channel_name)