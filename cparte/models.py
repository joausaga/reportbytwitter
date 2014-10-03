from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db import connection
from apiclient.discovery import build
import multiprocessing
import tweepy
import abc
import re
import time
import logging
import json
import ast
import os
import signal
import traceback

logger = logging.getLogger(__name__)
#logger = multiprocessing.get_logger()


""" Data Models
"""

LANGUAGES = (
    ('en', 'English'),
    ('es', 'Spanish'),
    ('it', 'Italian')
)


class Channel(models.Model):
    name = models.CharField(max_length=50)
    enabled = models.BooleanField(default=False)
    status = models.BooleanField(default=False, blank=True, editable=False)
    url = models.URLField(null=True)
    max_length_msgs = models.IntegerField(null=True, blank=True, help_text="Maximum length of messages to send through"
                                                                           "this channel from the application. Leave it"
                                                                           " blank for unlimited lengths.")

    def __unicode__(self):
        return self.name

    def on(self):
        self.status = True
        self.save()

    def off(self):
        self.status = False
        self.save()


class Account(models.Model):
    owner = models.CharField(max_length=50)
    id_in_channel = models.CharField(max_length=50)
    handler = models.CharField(max_length=50)
    url = models.URLField()
    channel = models.ForeignKey(Channel)

    def __unicode__(self):
        return self.owner


class Message(models.Model):
    name = models.CharField(max_length=50)
    body = models.TextField()
    key_terms = models.CharField(max_length=100)
    CATEGORIES = (
                    ('thanks_contribution', 'Express thanks for a contribution'),
                    ('incorrect_answer', 'Incorrect answer'),
                    ('ask_change_contribution', 'Ask whether participant wants to change a previous contribution'),
                    ('thanks_change', 'Express thanks for changing a contribution'),
                    ('contribution_cannot_save', 'Notify that a contribution cannot be saved'),
                    ('limit_answers_reached', 'Notify that the limit of answers has been reached'),
                    ('request_author_extrainfo', 'Ask for participant extra information'),
                    ('incorrect_author_extrainfo', 'Incorrect participant extra information'),
                    ('author_banned', 'Notify the author that he/she was banned'),
                    ('not_understandable_change_contribution_reply', 'Not understandable reply to the request about'
                                                                     'changing a previous contribution'),
    )
    category = models.CharField(max_length=100, choices=CATEGORIES)
    answer_terms = models.CharField(max_length=10, null=True, blank=True, help_text="Max length 10 characters")
    language = models.CharField(max_length=3, choices=LANGUAGES)
    channel = models.ForeignKey(Channel)

    def __unicode__(self):
        return self.name


class Setting(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    value = models.TextField()
    TYPES = (
        ('INT', 'Integer'),
        ('STR', 'String')
    )
    type = models.CharField(max_length=3, choices=TYPES)

    def __unicode__(self):
        return "Name: %s - Value: %s" % (self.name, self.value)

    def get_casted_value(self):
        if self.type == "INT":
            return int(self.value)
        else:
            return self.value


class ExtraInfo(models.Model):
    name = models.CharField(max_length=15, help_text="Max length 15 characters")
    description = models.TextField(null=True)
    STYLE_ANSWER = (
        ('FR', 'Free'),
        ('ST', 'Structured')
    )
    style_answer = models.CharField(max_length=20, choices=STYLE_ANSWER)
    format_answer = models.CharField(max_length=50, null=True, blank=True, help_text="A regular expression or blank in "
                                                                                     "case of freestyle answers")
    messages = models.ManyToManyField(Message)

    def __unicode__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True)
    screen_name = models.CharField(max_length=100)
    id_in_channel = models.CharField(max_length=50)
    channel = models.ForeignKey(Channel)
    language = models.CharField(max_length=10, null=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    zipcode = models.CharField(max_length=10, null=True, blank=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    banned = models.BooleanField(editable=False, default=False)
    input_mistakes = models.IntegerField(editable=False, default=0)
    request_mistakes = models.IntegerField(editable=False, default=0)
    friends = models.IntegerField(editable=False, default=0)
    followers = models.IntegerField(editable=False, default=0)
    groups = models.IntegerField(editable=False, default=0)
    posts_count = models.IntegerField(editable=False, default=0)
    url = models.URLField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    def reset_mistake_flags(self):
        self.input_mistakes = 0
        self.request_mistakes = 0
        self.save()

    def is_banned(self):
        return self.banned

    def ban(self):
        self.banned = True
        self.save()

    def add_input_mistake(self):
        self.input_mistakes += 1
        self.save()

    def add_request_mistake(self):
        self.request_mistakes += 1
        self.save()

    def get_input_mistakes(self):
        return self.input_mistakes

    def get_request_mistakes(self):
        return self.request_mistakes

    def get_extra_info(self):
        return self.zipcode

    def set_extra_info(self, extra_info):
        self.zipcode = extra_info  # For CRC extra_info equals zipcode
        self.save()


class Initiative(models.Model):
    name = models.CharField(max_length=100)
    organizer = models.CharField(max_length=50)
    account = models.ForeignKey(Account)
    hashtag = models.CharField(unique=True, max_length=14, help_text="Max length 14 characters (do not include '#')")
    url = models.URLField(null=True, blank=True)
    language = models.CharField(max_length=3, choices=LANGUAGES)

    def __unicode__(self):
        return self.name


class Campaign(models.Model):
    name = models.CharField(max_length=100)
    initiative = models.ForeignKey(Initiative)
    hashtag = models.CharField(max_length=14, null=True, blank=True,
                               help_text="Max length 14 characters (do not include '#')")
    url = models.URLField(null=True, blank=True)
    extrainfo = models.ForeignKey(ExtraInfo, blank=True, null=True)
    messages = models.ManyToManyField(Message)

    def __unicode__(self):
        return self.name


class Challenge(models.Model):
    name = models.CharField(max_length=100)
    campaign = models.ForeignKey(Campaign)
    hashtag = models.CharField(max_length=14, help_text="Max length 14 characters (do not include '#')")
    STYLE_ANSWER = (
        ('FR', 'Free'),
        ('ST', 'Structured')
    )
    style_answer = models.CharField(max_length=20, choices=STYLE_ANSWER)
    format_answer = models.CharField(max_length=50, null=True, blank=True,
                                     help_text="A regular expression or blank in case of freestyle answers")
    max_length_answer = models.IntegerField(null=True, blank=True)
    answers_from_same_author = models.IntegerField(default=1, help_text="Number of answers allowed from the same "
                                                                        "author. Use -1 for not limit")
    url = models.URLField(null=True, blank=True)

    def __unicode__(self):
        return self.name


class ContributionPost(models.Model):
    id_in_channel = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    contribution = models.TextField()
    full_text = models.TextField()
    url = models.URLField()
    author = models.ForeignKey(Author)
    in_reply_to = models.CharField(max_length=50, null=True)
    initiative = models.ForeignKey(Initiative)
    campaign = models.ForeignKey(Campaign)
    challenge = models.ForeignKey(Challenge)
    channel = models.ForeignKey(Channel)
    votes = models.IntegerField(default=0)      # e.g. +1 in Google+, like in Facebook
    re_posts = models.IntegerField(default=0)   # e.g. Share in Facebook, RT in Twitter
    bookmarks = models.IntegerField(default=0)  # e.g. Favourite in Twitter
    STATUS = (('TE', 'Temporal'), ('PE', 'Permanent'), ('DI', 'Discarded'))
    status = models.CharField(max_length=3, choices=STATUS)

    def __unicode__(self):
        return self.url

    def preserve(self):
        self.status = "PE"
        self.save()

    def discard(self):
        self.status = "DI"
        self.save()

    def temporal(self):
        if self.status == "TE":
            return True
        else:
            return False


class AppPost(models.Model):
    id_in_channel = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    text = models.TextField()
    url = models.URLField(null=True)
    app_parent_post = models.ForeignKey('self', null=True)
    contribution_parent_post = models.ForeignKey(ContributionPost, null=True)
    initiative = models.ForeignKey(Initiative)
    campaign = models.ForeignKey(Campaign)
    challenge = models.ForeignKey(Challenge)
    channel = models.ForeignKey(Channel)
    votes = models.IntegerField(default=0)          # e.g. +1 in Google+, like in Facebook
    re_posts = models.IntegerField(default=0)       # e.g. Share in Facebook, RT in Twitter
    bookmarks = models.IntegerField(default=0)      # e.g. Favourite in Twitter
    delivered = models.BooleanField(default=True)
    CATEGORIES = (('EN', 'Engagement'), ('PR', 'Promotion'))
    category = models.CharField(max_length=3, choices=CATEGORIES)
    payload = models.TextField(null=True, editable=False)
    answered = models.BooleanField(default=False)
    recipient_id = models.CharField(max_length=50, null=True, editable=False)

    def __unicode__(self):
        if self.url:
            return self.url
        else:
            return self.text

    def do_answer(self):
        self.answered = True
        self.save()


class MsgQueue(models.Model):
    timestamp = models.DateTimeField(auto_now=True)
    message_text = models.TextField()
    recipient_id = models.CharField(max_length=100, null=True)
    TYPES = (('PU', 'Public'), ('RE', 'Reply'), ('DM', 'Direct Message'))
    type = models.CharField(max_length=3, choices=TYPES)
    channel = models.ForeignKey(Channel)
    payload = models.TextField(null=True)

    def __unicode__(self):
        return self.message_text


""" Domain Models
"""


class MetaChannel():

    channels = None

    def __init__(self, channel_names):
        self.channels = {}
        for channel_name in channel_names:
            self.channels[channel_name] = None

    def authenticate(self, channel_name):
        channel_name = channel_name.lower()
        if channel_name == "twitter":
            self.channels[channel_name] = Twitter()
        else:
            logger.error("Unknown channel: %s" % channel_name)
            return
        self.channels[channel_name].authenticate()

    def channel_enabled(self, channel_name):
        channel_name = channel_name.lower()
        return channel_name in self.channels

    def broadcast(self, message):
        for name in self.channels.iterkeys():
            if self.channels[name]:
                self.channels[name].queue_message(message=message, type_msg="PU")

    def post_public(self, channels, message):
        for channel in channels:
            channel = channel.lower()
            if self.channels[channel]:
                self.channels[channel].queue_message(message=message, type_msg="PU")
            else:
                logger.error("%s channel is unavailable, it cannot post into it" % channel)

    def send_direct_message(self, channel_name, recipient, message):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].queue_message(message=message, type_msg="DM", payload={'author': recipient})
        else:
            logger.error("%s channel is unavailable, it cannot send direct message through it" % channel_name)

    def reply_to(self, channel_name, id_message, message):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].queue_message(message=message, type_msg="RE", recipient_id=id_message)
        else:
            logger.error("%s channel is unavailable, it cannot post to a user through it" % channel_name)

    def get_post(self, channel_name, id_post):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].get_post(id_post)
        else:
            logger.error("%s channel is unavailable, it cannot get a post" % channel_name)

    def get_info_user(self, channel_name, id_user):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].get_info_user(id_user)
        else:
            logger.error("%s channel is unavailable, it cannot get info about a user" % channel_name)

    def listen(self, channel_name):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].listen()
        else:
            logger.error("%s channel is unavailable, it cannot be listened" % channel_name)

    def disconnect(self, channel_name):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].disconnect()
        else:
            logger.error("The object %s channel does not exist. A low-level disconnection was performed" % channel_name)
            Channel.objects.get(name=channel_name).off()

    def set_initiatives(self, channel_name, initiative_ids):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].set_initiatives(initiative_ids)
        else:
            logger.error("%s channel is unavailable, initiatives cannot be set" % channel_name)

    def set_accounts(self, channel_name, account_ids):
        channel_name = channel_name.lower()
        if self.channels[channel_name]:
            self.channels[channel_name].set_accounts(account_ids)
        else:
            logger.error("%s channel is unavailable, accounts cannot be set" % channel_name)


class PostManager():
    channel = None
    settings = {}
    url_shortener = None
    NO_LIMIT_ANSWERS = -1
    NOTIFICATION_MESSAGE = "NT"
    ENGAGE_MESSAGE = "EN"
    STRUCTURED_ANSWER = "ST"
    FREE_ANSWER = "FR"

    def __init__(self, channel):
        self.channel = channel
        self._set_settings()
        if settings.SHORT_URL:
            self.url_shortener = build(serviceName=self.settings['urlshortener_api_name'],
                                       version=self.settings['urlshortener_api_version'],
                                       developerKey=settings.URL_SHORTENER_API_KEY)
        else:
            self.url_shortener = None

    def _set_settings(self):
        try:
            self.settings['limit_wrong_inputs'] = Setting.objects.get(name="limit_wrong_inputs").get_casted_value()
            self.settings['limit_wrong_requests'] = Setting.objects.get(name="limit_wrong_requests").get_casted_value()
            self.settings['datetime_format'] = Setting.objects.get(name="datetime_format").value
            self.settings['urlshortener_api_name'] = Setting.objects.get(name="gurlshortener_api_name").value
            self.settings['urlshortener_api_version'] = Setting.objects.get(name="gurlshortener_api_version").value
        except Setting.DoesNotExist as e:
            e_msg = "Unknown setting %s, the post manager cannot be started" % e
            logger.critical(e_msg)
            raise Exception(e_msg)

    def manage_post(self, post):
        try:
            author_obj = self.channel.get_author_obj(post["author"])
            if author_obj is None or not author_obj.is_banned():
                return self._do_manage(post, author_obj)
            else:
                logger.info("The post was ignore, its author, called %s, is in the black list" % author_obj.screen_name)
                return None
        except Exception as e:
            logger.critical("Error when managing the post: %s. Internal message: %s" % (post["text"], e))
            logger.critical(traceback.format_exc())

    def _do_manage(self, post, author_obj):
        parent_post_id = post["parent_id"]
        app_parent_post = None
        author_id = post["author"]["id"]
        if parent_post_id is None:
            if author_id in self.channel.get_account_ids():
                return None  # So far, I'm not interested in processing posts authored by the accounts bound to the app
            else:
                initiative = self.channel.has_initiative_hashtags(post)
                within_initiative = True if initiative else False
                challenge = self.channel.get_challenge_info(post, initiative) if within_initiative else None
        else:
            try:
                # Searching for the post in the app db
                app_parent_post = AppPost.objects.get(id_in_channel=parent_post_id)
                # Check whether the category of the root post is engagement (EN).
                # Posts in this category are intended to engage the public into the initiative challenges
                within_initiative = app_parent_post.category == self.ENGAGE_MESSAGE and \
                                    app_parent_post.app_parent_post is None
                challenge = app_parent_post.challenge if within_initiative else None
            except AppPost.DoesNotExist:
                return None  # I'm not interested in processing replies that were not posted to the app posts

        if within_initiative and challenge:
            if author_obj is None:
                author_obj = self.channel.register_new_author(post["author"])
            logger.info("Post from %s within the initiative: %s, campaign: %s, challenge: %s. Text: %s" %
                        (author_obj.screen_name, challenge.campaign.initiative.name, challenge.campaign.name,
                         challenge.name, post["text"]))
            return self._process_input(post, author_obj, challenge)
        elif parent_post_id is not None:  # It is a reply but not to a challenge post
            if app_parent_post and app_parent_post.category == self.NOTIFICATION_MESSAGE:
                # Only process replies that were made to app posts categorized as notification (NT)
                if not app_parent_post.answered and app_parent_post.recipient_id == author_id:
                    message = self._get_parent_post_message(app_parent_post.text, app_parent_post.campaign)
                    if message:
                        if message.category == "request_author_extrainfo":
                            # It is a reply to an extra info request
                            ret = self._process_extra_info(post, author_obj, app_parent_post)
                            app_parent_post.do_answer()
                            return ret
                        elif message.category == "incorrect_answer":
                            # It is a reply to a wrong input notification
                            app_parent_post.do_answer()
                            if not author_obj.is_banned():
                                ret = self._process_input(post, author_obj, app_parent_post.challenge)
                                return ret
                            else:
                                return None
                        elif message.category == "ask_change_contribution":
                            app_parent_post.do_answer()
                            temp_contribution = self._get_contribution_post(app_parent_post)
                            # It is a reply to a question about changing previous input
                            answer_terms = message.answer_terms.split()
                            found_term = False
                            for answer_term in answer_terms:
                                if self._to_unicode(answer_term).lower() in self._to_unicode(post["text"]).lower():
                                    found_term = True
                            if found_term:
                                ret = self._update_contribution(post, author_obj, app_parent_post)
                                return ret
                            else:
                                new_message = app_parent_post.campaign.messages.get(category="not_understandable_change_contribution_reply")
                                self._send_reply(post, app_parent_post.initiative, app_parent_post.challenge, new_message)
                                # If we cannot understand the answer we reply saying that and discard the temporal post
                                temp_contribution.discard()
                                return new_message
                        elif message.category == "incorrect_author_extrainfo":
                            # It is a reply to a wrong extra info notification
                            ret = self._process_extra_info(post, author_obj, app_parent_post)
                            app_parent_post.do_answer()
                            return ret
                        else:
                            logger.info("Unknown message category. Text: %s" % app_parent_post.text)
                            app_parent_post.do_answer()
                            return None
                    else:
                        logger.info("Cannot determine to which app message this post '%s' belongs to" %
                                    app_parent_post.text)
                        app_parent_post.do_answer()
                        return None
                else:
                    logger.info("The post received is a reply to an already answered request post or it was sent by an "
                                "user who is not the original recipient of the request post")
                    return None
            else:
                logger.error("App parent post does not exist or the category of the app parent post is not "
                             "'notification'. The post: '%s' will be ignored" % post["text"])
                return None

    def _get_parent_post_message(self, text_post, campaign):
        messages = list(campaign.messages.all())
        # Add campaign's extrainfo messages
        for msg_extrainfo in campaign.extrainfo.messages.all():
            messages.append(msg_extrainfo)
        for message in messages:
            found_all_terms = True
            terms = message.key_terms.split()
            for term in terms:
                if self._to_unicode(term).lower() not in self._to_unicode(text_post).lower():
                    found_all_terms = False
            if found_all_terms:
                return message
        return None

    def _process_extra_info(self, post, author_obj, app_parent_post):
        text_post = post["text"].lower()
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        author = post["author"]
        extra_info = self._get_extra_info(text_post, campaign)
        if extra_info is not None:
            logger.info("%s's extra information was processed correctly. His/her contribution was permanently saved." %
                        author["name"])
            ret = self._preserve_temporal_post(post, author_obj, extra_info, app_parent_post)
            self._preserve_author_temporal_posts(author)
            return ret
        else:
            author_obj.add_request_mistake()
            author_wrong_request_counter = author_obj.get_request_mistakes()
            if author_wrong_request_counter > self.settings['limit_wrong_requests']:
                if author_wrong_request_counter - self.settings['limit_wrong_requests'] == 1:
                    logger.info("The participant %s has exceed the limit of wrong requests, his/her last contribution "
                                "will be discarded" % author["name"])
                    # A notification message will be sent only after the first time the limit was exceed
                    message = campaign.messages.get(category="contribution_cannot_save")
                    self._send_reply(post, campaign.initiative, challenge, message)
                    # Discard the "incomplete" contribution
                    contribution_post = self._get_contribution_post(app_parent_post)
                    contribution_post.discard()
                    return message
                else:
                    logger.info("The participant %s has exceed the limit of %s wrong requests, the message will be "
                                "ignored" % (author["name"], self.settings['limit_wrong_requests']))
                    return None
            else:
                logger.info("%s's reply is in an incorrect format" % author["name"])
                message = campaign.extrainfo.messages.get(category="incorrect_author_extrainfo")
                self._send_reply(post, campaign.initiative, challenge, message)
                return message

    def _preserve_temporal_post(self, post, author_obj, extra_info, app_parent_post):
        author_obj.set_extra_info(extra_info)
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        post_db = self._get_contribution_post(app_parent_post)
        post_db.preserve()
        message = campaign.messages.get(category="thanks_contribution")
        self._send_reply(post, campaign.initiative, challenge, message)
        author_obj.reset_mistake_flags()
        return message

    def _update_contribution(self, post, author_obj, app_parent_post):
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        try:
            # Permanent Post
            old_post = ContributionPost.objects.get(challenge=challenge, author=author_obj.id, status="PE")
            # Temporal Post
            new_post = ContributionPost.objects.filter(challenge=challenge, author=author_obj.id, status="TE").\
                       order_by('-datetime').first()
            new_post.preserve()  # Preserve the newest (temporal)
            old_post.discard()  # Discard the oldest (permanent)
            self._discard_temporal_post(author_obj, challenge)  # Discard the remaining temporal posts related to 'challenge'
            message = campaign.messages.get(category="thanks_change")
            self._send_reply(post, campaign.initiative, challenge, message, new_post)
            author_obj.reset_mistake_flags()
            return message
        except (ContributionPost.DoesNotExist, ContributionPost.MultipleObjectsReturned) as e:
            logger.critical("Error when trying to update a previous contribution. %s" % str(e))
            return None

    def _get_extra_info(self, text, campaign):
        reg_expr = re.compile(self._to_unicode(campaign.extrainfo.format_answer))
        for term in text.split():
            if reg_expr.match(self._to_unicode(term)):
                return term
        return None

    def _get_contribution_post(self, post):
        db_post = post
        while not db_post.contribution_parent_post:
            db_post = db_post.app_parent_post
        return db_post.contribution_parent_post

    def _process_input(self, post, author_obj, challenge):
        author = post["author"]
        curated_input = self._validate_input(post, challenge)
        campaign = challenge.campaign
        if curated_input is not None:
            # It is a valid input
            if challenge.answers_from_same_author != self.NO_LIMIT_ANSWERS:
                existing_posts = list(self._has_already_posted(author_obj, challenge))
                if len(existing_posts) > 0:
                    if challenge.answers_from_same_author == 1:
                        # Allow changes only if the number of allowed answers is 1
                        if len(existing_posts) > 1:
                            # It should exist only one contribution, but if not and as way of auto-recovering from an
                            # inconsistent state the newest ones will be discarded, leaving only the oldest one in
                            # the database
                            logger.critical("The challenge %s allows only one contribution per participant but the author "
                                            "%s has more than one contribution saved in the db. The newest ones will be "
                                            "discarded" % (challenge.name, author["name"]))
                            for e_post in existing_posts[:]:
                                e_post.discard()
                                existing_posts.remove(e_post)
                                if len(existing_posts) == 1:
                                    break
                        existing_post = existing_posts[0]
                        if self._to_unicode(curated_input) != self._to_unicode(existing_post.contribution):
                            # Only if the new contribution is different from the previous we will process it
                            # otherwise it will be ignored
                            self._save_post(post, author_obj, curated_input, challenge, temporal=True)
                            logger.info("A new contribution to the challenge %s was posted by the participant %s. "
                                        "It was saved temporarily" % (challenge.name, author["name"]))
                            message = campaign.messages.get(category="ask_change_contribution")
                            self._send_reply(post, campaign.initiative, challenge, message, (curated_input, existing_post))
                            return message
                        else:
                            logger.info("The new contribution: %s is equal as the already existing" % curated_input)
                            return None
                    else:
                        if len(existing_posts) <= challenge.answers_from_same_author:
                            # Save participant's answer if the participant is still under the limit of allowed answers
                            return self._do_process_input(post, author_obj, campaign, challenge, curated_input)
                        else:
                            # Send a message saying that he/she has reached the limit of allowed answers
                            message = campaign.messages.get(category="limit_answers_reached")
                            self._send_reply(post, campaign.initiative, challenge, message)
                            author_obj.reset_mistake_flags()
                            logger.info("The participant %s has reached the limit of %s contributions allowed in the "
                                        "challenge %s" % (author["name"], challenge.answers_from_same_author, challenge.name))
                            return message
                else:
                    return self._do_process_input(post, author_obj, campaign, challenge, curated_input)
            else:
                return self._do_process_input(post, author_obj, campaign, challenge, curated_input)
        else:
            # The input is not valid
            author_obj.add_input_mistake()
            if author_obj.get_input_mistakes() > self.settings['limit_wrong_inputs']:
                logger.info("The participant %s has been banned because he/she has exceed the limit of %s wrong "
                            "contributions" % (author["name"], self.settings['limit_wrong_inputs']))
                # Ban author and notify him that he/she has been banned
                author_obj.ban()
                new_message = campaign.messages.get(category="author_banned")
                self._send_reply(post, campaign.initiative, challenge, new_message)
                return new_message
            else:
                logger.info("The contribution %s of the participant %s does not satisfy the required format of the "
                            "challenge %s" % (post["text"], author["name"], challenge.name))
                # Reply saying that his/her input was wrong
                message = campaign.messages.get(category="incorrect_answer")
                self._send_reply(post, campaign.initiative, challenge, message)
                return message

    def _do_process_input(self, post, author_obj, campaign, challenge, curated_input):
        author = post["author"]
        if campaign.extrainfo is None or author_obj.get_extra_info() is not None:
            post_saved = self._save_post(post, author_obj, curated_input, challenge, temporal=False)
            message = campaign.messages.get(category="thanks_contribution")
            self._send_reply(post, campaign.initiative, challenge, message, post_saved)
            author_obj.reset_mistake_flags()
            logger.info("The contribution '%s' of the participant %s to the challenge %s has been saved" %
                        (curated_input, author["name"], challenge.name))
        else:
            post_saved = self._save_post(post, author_obj, curated_input, challenge, temporal=True)
            message = campaign.extrainfo.messages.get(category="request_author_extrainfo")
            self._send_reply(post, campaign.initiative, challenge, message, post_saved)
            logger.info("The contribution '%s' of the participant %s to the challenge %s has been saved temporarily "
                        "until getting the required additional information of the contributor" %
                        (curated_input, author["name"], challenge.name))
        return message

    def _validate_input(self, post, challenge):
        curated_text = self._to_unicode(post["text"])
        if challenge.style_answer == self.STRUCTURED_ANSWER:
            result = re.search(self._to_unicode(challenge.format_answer), curated_text)
            if result is not None:
                start = result.start()
                end = result.end()
                curated_text = curated_text[start:end].strip()  # Slicing and trimming the text of the tweet
                return curated_text
            else:
                return None
        elif challenge.style_answer == self.FREE_ANSWER and challenge.max_length_answer is not None:
            if len(curated_text) > challenge.max_length_answer:
                return None
            else:
                return curated_text
        else:
            return curated_text

    # Check if the participant has already posted an answer to the challenge
    def _has_already_posted(self, author_obj, challenge):
        try:
            return ContributionPost.objects.filter(challenge=challenge, author=author_obj.id, status='PE').order_by('-datetime')
        except ContributionPost.DoesNotExist:
            return None

    def _save_post(self, post, author_obj, curated_input, challenge, temporal):
        channel_obj = self.channel.get_channel_obj()
        campaign = challenge.campaign
        initiative = campaign.initiative
        if temporal:
            status = 'TE'
        else:
            status = 'PE'
        post_to_save = ContributionPost(id_in_channel=post["id"],
                                        datetime=timezone.make_aware(post["datetime"], timezone.get_default_timezone()),
                                        contribution=curated_input, full_text=post["text"], url=post["url"],
                                        author=author_obj, in_reply_to=post["parent_id"], initiative=initiative,
                                        campaign=campaign, challenge=challenge, channel=channel_obj, votes=post["votes"],
                                        re_posts=post["re_posts"], bookmarks=post["bookmarks"], status=status)
        post_to_save.save(force_insert=True)
        if not temporal:
            self._discard_temporal_post(author_obj, challenge)
        return post_to_save

    # Discard any temporal post existing within 'challenge' and posted by 'author'
    def _discard_temporal_post(self, author_obj, challenge):
        try:
            temp_posts = ContributionPost.objects.filter(challenge=challenge, author=author_obj.id, status='TE')
            for post in temp_posts:
                post.discard()
            return True
        except ContributionPost.DoesNotExist:
            return False

    # Preserve author's posts that were saved as temporal because of the lack of his/her extra info
    def _preserve_author_temporal_posts(self, author):
        author_obj = self.channel.get_author_obj(author)
        try:
            temp_posts = ContributionPost.objects.filter(author=author_obj.id, status='TE')
            for post in temp_posts:
                try:
                    app_post = AppPost.objects.get(contribution_parent_post=post.id, answered=False)
                    message_sent = self._get_parent_post_message(app_post.text, app_post.campaign)
                    if message_sent.category == "request_author_extrainfo":
                        campaign = app_post.campaign
                        challenge = app_post.challenge
                        post.preserve()
                        app_post.do_answer()
                        message = campaign.messages.get(category="thanks_contribution")
                        post_dict = {"id": post.id_in_channel, "parent_id": post.in_reply_to, "author": author}
                        self._send_reply(post_dict, campaign.initiative, challenge, message)
                except AppPost.DoesNotExist, AppPost.MultipleObjectsReturned:
                    pass
            return True
        except ContributionPost.DoesNotExist:
            return False

    def _send_reply(self, post, initiative, challenge, message, extra=None):
        msg = None
        author_username = post["author"]["print_name"]
        author_id = post["author"]["id"]
        current_datetime = time.strftime(self.settings['datetime_format'])
        type_msg = ""
        short_url = None

        if message.category == "thanks_contribution":
            short_url = self._do_short_initiative_url(initiative.url) if self.url_shortener else initiative.url
            msg = message.body % (author_username, challenge.hashtag, short_url)
            type_msg = "TH"
        elif message.category == "incorrect_answer":
            msg = message.body % (author_username, current_datetime)
            type_msg = "NT"
        elif message.category == "ask_change_contribution":
            old_contribution = extra[1].contribution
            new_contribution = extra[0]
            msg = message.body % (author_username, old_contribution, challenge.hashtag, message.answer_terms,
                                  new_contribution)
            type_msg = "NT"
        elif message.category == "thanks_change":
            short_url = self._do_short_initiative_url(initiative.url) if self.url_shortener else initiative.url
            msg = message.body % (author_username, challenge.hashtag, extra.contribution, short_url)
            type_msg = "TH"
        elif message.category == "contribution_cannot_save":
            msg = message.body % (author_username, current_datetime)
            type_msg = "NT"
        elif message.category == "limit_answers_reached":
            msg = message.body % (author_username, current_datetime, challenge.hashtag)
            type_msg = "NT"
        elif message.category == "request_author_extrainfo":
            msg = message.body % (author_username, extra.contribution, challenge.hashtag)
            type_msg = "NT"
        elif message.category == "incorrect_author_extrainfo":
            msg = message.body % (author_username, current_datetime)
            type_msg = "NT"
        elif message.category == "author_banned":
            msg = message.body % author_username
            type_msg = "NT"
        elif message.category == "not_understandable_change_contribution_reply":
            msg = message.body % (author_username, current_datetime)
            type_msg = "NT"
        if msg is not None:
            payload = {'parent_post_id': post["parent_id"], 'type_msg': type_msg,
                       'post_id': post["id"], 'initiative_id': initiative.id, 'author_username': author_username,
                       'author_id': author_id, 'campaign_id': challenge.campaign.id, 'challenge_id': challenge.id,
                       'initiative_short_url': short_url}
            payload_json = json.dumps(payload)
            self.channel.queue_message(message=msg, type_msg="RE", recipient_id=post["id"], payload=payload_json)

    def _do_short_initiative_url(self, long_url):
        try:
            url = self.url_shortener.url()
            body = {'longUrl': long_url}
            resp = url.insert(body=body).execute()
            if 'error' not in resp:
                short_url = resp['id']
            else:
                short_url = long_url
                logger.error("Error %s when trying to short the initiative URL. Reason: %s" % (resp['error']['code'],
                                                                                               resp['error']['message']))
        except Exception, e:
            short_url = long_url
            logger.error("Error when trying to short the initiative URL. Message: %s" % e)
        return short_url

    def _to_unicode(self, obj, encoding="utf-8"):
        if isinstance(obj, basestring):
            if not isinstance(obj, unicode):
                obj = unicode(obj, encoding)
        return obj


class SocialNetwork():
    __metaclass__ = abc.ABCMeta
    initiatives = None
    accounts = None
    hashtags = None
    MSG_DUPLICATE_CODE = 187
    channel = None
    pid_messenger = None
    pid_listener = None

    @abc.abstractmethod
    def authenticate(self):
        """Authenticate into the channel"""
        raise NotImplementedError

    @abc.abstractmethod
    def listen(self):
        """Listen the channel"""
        raise NotImplementedError

    @abc.abstractmethod
    def _post_public(self, message, payload):
        """Post a public messages into the channel"""
        raise NotImplementedError

    @abc.abstractmethod
    def _send_direct_message(self, message, author_id, payload):
        """Send a private message to a particular user"""
        raise NotImplementedError

    @abc.abstractmethod
    def _reply_to(self, message, id_post, payload):
        """Reply to an existing post"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_post(self, id_post):
        """Get a post previously published in the channel and identified by id_post"""
        raise NotImplementedError

    @abc.abstractmethod
    def delete_post(self, id_post):
        """Delete the post identified by id_post"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_info_user(self, id_user):
        """Get information about a particular user"""
        raise NotImplementedError

    @abc.abstractmethod
    def to_dict(self, post):
        """Transform post object into a dictionary"""
        raise NotImplementedError

    # Return the object of the post author
    def get_author_obj(self, author):
        try:
            return Author.objects.get(id_in_channel=author["id"], channel=self.channel.id)
        except Author.DoesNotExist:
            return None

    # Register in the database a new author
    def register_new_author(self, author):
        new_author = Author(name=author["name"], screen_name=author["screen_name"], id_in_channel=author["id"],
                            channel=self.channel, friends=author["friends_count"], followers=author["followers_count"],
                            url=author["url"], description=author["description"], language=author["lang"],
                            posts_count=author["statuses_count"])
        new_author.save(force_insert=True)
        return new_author

    # Check whether the text of the post has the hashtags the identifies the initiative
    def has_initiative_hashtags(self, post):
        for initiative in self.initiatives:
            initiative_hashtag = initiative.hashtag
            for post_hashtag in post['hashtags']:
                if post_hashtag == initiative_hashtag.lower().strip():
                    return initiative
        return None

    # Return information about the challenge
    def get_challenge_info(self, post, initiative):
        campaigns = initiative.campaign_set.all()
        for campaign in campaigns:
            challenges = campaign.challenge_set.all()
            for challenge in challenges:
                challenge_hashtag = challenge.hashtag
                for post_hashtag in post['hashtags']:
                    if post_hashtag == challenge_hashtag.lower().strip():
                        return challenge
        return None

    def disconnect(self):
        # Kill process that manages the message queue
        try:
            os.kill(self.pid_messenger, signal.SIGKILL)
            logger.info("Messenger has been stopped")
        except Exception as e:
            logger.error("An error occurs trying to kill the process that runs the messenger. Internal message: %s" % e)
        # Kill the process that listens Twitter's stream
        try:
            os.kill(self.pid_listener, signal.SIGKILL)
            logger.info("Listener has been stopped")
        except Exception as e:
            logger.error("An error occurs trying to kill the process that runs the listener. Internal message: %s" % e)
        # Flag that the channel is off-line
        self.channel.off()
        self.pid_messenger = None
        self.pid_listener = None

    def set_initiatives(self, initiative_ids):
        for id_initiative in initiative_ids:
            try:
                initiative = Initiative.objects.get(pk=id_initiative)
            except Initiative.DoesNotExist:
                e_msg = "Does not exist an initiative identified with the id %s" % id_initiative
                logger.critical(e_msg)
                raise Exception(e_msg)

            if self.initiatives:
                self.initiatives.append(initiative)
                self.hashtags.append(initiative.hashtag)
            else:
                self.initiatives = [initiative]
                self.hashtags = [initiative.hashtag]
            # Add to the array of hashtags the hashtags of the initiative's campaigns
            for campaign in initiative.campaign_set.all():
                if campaign.hashtag is not None:
                    self.hashtags.append(campaign.hashtag)
                # Add to the array of hashtags the hashtags of the campaign's challenges
                for challenge in campaign.challenge_set.all():
                    self.hashtags.append(challenge.hashtag)

    def set_accounts(self, account_ids):
        self.accounts = []
        for id_account in account_ids:
            try:
                self.accounts.append(Account.objects.get(pk=id_account).id_in_channel)
            except Account.DoesNotExist:
                e_msg = "Does not exist an account identified with the id %s" % id_account
                logger.critical(e_msg)
                raise Exception(e_msg)

    def get_account_ids(self):
        return self.accounts

    def get_channel_obj(self):
        return self.channel

    def get_name(self):
        return self.channel.name

    def run_msg_dispatcher(self):
        while True:
            if MsgQueue.objects.exists():
                msg_to_dispatch = MsgQueue.objects.earliest('timestamp')
                payload_hash = json.loads(msg_to_dispatch.payload)
                if msg_to_dispatch.type == "PU":  # Public Posts
                    res = self._post_public(msg_to_dispatch.message_text, payload_hash)
                elif msg_to_dispatch.type == "RE":  # Reply
                    res = self._reply_to(msg_to_dispatch.message_text, msg_to_dispatch.recipient_id, payload_hash)
                else:  # Direct message
                    res = self._send_direct_message(msg_to_dispatch.message_text, payload_hash['author_id'], payload_hash)
                if res['delivered']:
                    msg_to_dispatch.delete()
                else:
                    if res['response'][0]['code'] == self.MSG_DUPLICATE_CODE:
                        msg_to_dispatch.delete()
                    # Need to add actions for other errors, so far only duplicate messages are considered
            else:
                time.sleep(10)  # Wait some time

    def queue_message(self, message, type_msg, recipient_id=None, payload=None):
        msg_queue = MsgQueue(message_text=message, recipient_id=recipient_id, type=type_msg, channel=self.channel,
                             payload=payload)
        msg_queue.save(force_insert=True)

    def save_post_db(self, payload, response, channel):
        parent_post_id = payload['parent_post_id']
        post_id = payload['post_id']
        type_msg = payload['type_msg']
        initiative_short_url = payload['initiative_short_url']
        initiative = Initiative.objects.get(pk=payload['initiative_id'])
        campaign = Campaign.objects.get(pk=payload['campaign_id'])
        challenge = Challenge.objects.get(pk=payload['challenge_id'])
        recipient_id = payload['author_id']
        if parent_post_id is not None:
            app_parent_post = AppPost.objects.get(id_in_channel=parent_post_id)
        else:
            app_parent_post = None
        try:
            contribution_parent_post = ContributionPost.objects.get(id_in_channel=post_id)
        except ContributionPost.DoesNotExist:
            contribution_parent_post = None
        app_post = AppPost(id_in_channel=response["id"], datetime=timezone.now(), text=response["text"],
                           url=response["url"], app_parent_post=app_parent_post, initiative=initiative, campaign=campaign,
                           contribution_parent_post=contribution_parent_post, challenge=challenge,
                           channel=channel.get_channel_obj(), votes=0, re_posts=0, bookmarks=0, delivered=True,
                           category=type_msg, payload=initiative_short_url, recipient_id=recipient_id, answered=False)
        app_post.save(force_insert=True)
        if app_post.id is None:
            if channel.delete_post(response) is not None:
                logger.error("The app post couldn't be saved into the db, so its corresponding post was deleted from "
                             "%s" % channel.get_name())
            else:
                logger.critical("The app post couldn't be saved into the db, but its corresponding post couldn't be "
                                "delete from %s. The app may be in an inconsistent state" % channel.get_name())
        else:
            logger.info("The app post with the id: %s was created" % app_post.id)


class Twitter(SocialNetwork):
    auth_handler = None

    def __init__(self):
        self.channel = Channel.objects.get(name="twitter")

    def authenticate(self):
        self.auth_handler = tweepy.OAuthHandler(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)
        self.auth_handler.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)

    def listen(self):
        manager = PostManager(self)
        listener = TwitterListener(manager)
        stream = tweepy.Stream(self.auth_handler, listener)
        # Spawn off a process that listens Twitter's firehose
        proc_listener = multiprocessing.Process(target=stream.filter, args=[self.accounts, self.hashtags])
        connection.close()  # Close the connection to DB to avoid the child process uses it, which crashes MySQL engine
        proc_listener.start()
        self.pid_listener = proc_listener.pid
        logger.info("Starting to listen Twitter Stream")
        # Spawn off a process that manages the queue of messages to send
        proc_messenger = multiprocessing.Process(target=self.run_msg_dispatcher)
        connection.close()  # Close the connection to DB to avoid the child process uses it, which crashes MySQL engine
        proc_messenger.start()
        self.pid_messenger = proc_messenger.pid
        logger.info("Message Dispatcher on")
        self.channel.on()

    def _post_public(self, message, payload):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        try:
            response = api.update_status(status=message)
            logger.info("The post '%s' has been published through Twitter" % message)
            response_dict = self.to_dict(response)
            self.save_post_db(payload, response_dict, self)
            return {'delivered': True, 'response': response}
        except tweepy.TweepError as e:
            reason = ast.literal_eval(e.reason)
            logger.error("The post couldn't be delivered. Reason: %s" % reason[0]['message'])
            return {'delivered': False, 'response': reason}

    def _send_direct_message(self, message, author_id, payload):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        try:
            response = api.send_direct_message(user_id=author_id, text=message)
            logger.info("The message '%s' has been sent directly to %s through Twitter" % (message, author_id))
            response_dict = self.to_dict(response)
            self.save_post_db(payload, response_dict, self)
            return {'delivered': True, 'response': response}
        except tweepy.TweepError as e:
            reason = ast.literal_eval(e.reason)
            logger.error("The post couldn't be delivered. Reason: %s" % reason[0]['message'])
            return {'delivered': False, 'response': reason}

    def _reply_to(self, message, id_post, payload):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        try:
            response = api.update_status(status=message, in_reply_to_status_id=id_post)
            logger.info("The post '%s' has been sent to %s through Twitter" % (message, payload['author_username']))
            response_dict = self.to_dict(response)
            self.save_post_db(payload, response_dict, self)
            return {'delivered': True, 'response': response}
        except tweepy.TweepError as e:
            reason = ast.literal_eval(e.reason)
            logger.error("The post couldn't be delivered. Reason: %s" % reason[0]['message'])
            return {'delivered': False, 'response': reason}

    def get_post(self, id_post):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        return api.get_status(id_post)

    def delete_post(self, post):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        try:
            return api.destroy_status(post["id"])
        except tweepy.TweepError, e:
            logger.error("The post %s couldn't be destroyed. %s" % (post["id"], e.reason))

    def get_info_user(self, id_user):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        return api.get_user(id_user)

    def to_dict(self, post):
        return {"id": post.id_str, "text": post.text,
                "url": self.channel.url + post.author.screen_name + "/status/" + post.id_str}


class TwitterListener(tweepy.StreamListener):
    manager = None
    url = "https://twitter.com/"

    def __init__(self, manager):
        super(TwitterListener, self).__init__()
        self.manager = manager

    def on_status(self, status):
        author = status.author
        status_dict = {"id": status.id_str, "text": status.text, "parent_id": status.in_reply_to_status_id_str,
                       "datetime": status.created_at, "url": self.build_url_post(status), "votes": 0,
                       "re_posts": status.retweet_count, "bookmarks": status.favorite_count,
                       "hashtags": self.build_hashtags_array(status),
                       "author": {"id": author.id_str, "name": author.name, "screen_name": author.screen_name,
                                  "print_name": "@" + author.screen_name, "url": self.url + author.screen_name,
                                  "description": author.description, "language": author.lang,
                                  "posts_count": author.statuses_count, "friends": author.friends_count,
                                  "followers": author.followers_count, "groups": author.listed_count}
                       }
        self.manager.manage_post(status_dict)
        return True

    def on_error(self, status_code):
        logger.error("Error in the firehose, status code: %s" % str(status_code))
        return True  # To continue listening

    def on_timeout(self):
        logger.warning("Got timeout from the firehose")
        return True  # To continue listening

    def build_url_post(self, status):
        return self.url + status.author.screen_name + "/status/" + status.id_str

    def build_hashtags_array(self, status):
        hashtags = []
        for hashtag in status.entities['hashtags']:
            hashtags.append(hashtag['text'].lower().strip())
        return hashtags
