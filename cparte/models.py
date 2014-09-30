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
    STATUS = (('TE', 'Temporal'), ('PE', 'Permanent'), ('DI','Discarded'))
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
        return self.channels.has_key(channel_name)

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
            self.channels[channel_name].queue_message(message=message, type_msg="DM", payload={'author':recipient})
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
            author = self.channel.get_author(post)
            if author is None or not author.is_banned():
                type_post = self.channel.get_type_post(post)
                if type_post[0] == "reply" or type_post[0] == "status":
                    return self._do_manage(post, author, type_post[1])
                else:
                    logger.warninig("The type %s of the message is unknown. Message text: '%s'" %
                                    (type_post[0], self.channel.get_text_post(post)))
                    return None
            else:
                logger.info("The post was ignore, its author, called %s, is in the black list" % author.screen_name)
                return None
        except Exception as e:
            logger.critical("Unexpected error when managing the post: %s" % self.channel.get_text_post(post))
            logger.critical(traceback.print_exc())

    def _do_manage(self, post, author, parent_post_id=None):
        app_parent_post = None
        author_id = self.channel.get_author_id(post)
        if parent_post_id is None:
            if author_id in self.channel.get_account_ids():
                return None # So far, I'm not interested in processing posts authored by the accounts bound to the app
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
                return None # I'm not interested in processing replies that were not posted to the app posts

        if within_initiative and challenge:
            if author is None:
                author = self.channel.register_new_author(post)
            logger.info("Post from %s within the initiative: %s, campaign: %s, challenge: %s" %
                        (author.screen_name, challenge.campaign.initiative.name, challenge.campaign.name, challenge.name))
            return self._process_input(post, challenge, parent_post_id)
        elif parent_post_id is not None:  # It is a reply but not to a challenge post
            if app_parent_post and app_parent_post.category == self.NOTIFICATION_MESSAGE:
                if not app_parent_post.answered and app_parent_post.recipient_id == author_id:
                    # Only process replies that were made to app posts categorized as notification (NT)
                    message = self._get_parent_post_message(app_parent_post.text, app_parent_post.campaign)
                    if message:
                        if message.category == "request_author_extrainfo":
                            # It is a reply to an extra info request
                            ret = self._process_extra_info(post, app_parent_post)
                            app_parent_post.do_answer()
                            return ret
                        elif message.category == "incorrect_answer":
                            # It is a reply to a wrong input notification
                            author = self.channel.get_author(post)
                            if not author.is_banned():
                                ret = self._process_input(post, app_parent_post.challenge, parent_post_id)
                                app_parent_post.do_answer()
                                return ret
                            else:
                                app_parent_post.do_answer()
                                return None
                        elif message.category == "ask_change_contribution":
                            temp_contribution = self._get_contribution_post(app_parent_post)
                            # It is a reply to a question about changing previous input
                            answer_terms = message.answer_terms.split()
                            found_term = False
                            for answer_term in answer_terms:
                                if answer_term in self.channel.get_text_post(post).lower():
                                    found_term = True
                            if found_term:
                                ret = self._update_contribution(post, app_parent_post)
                                app_parent_post.do_answer()
                                return ret
                            else:
                                new_message = app_parent_post.campaign.messages.get(category="not_understandable_change_contribution_reply")
                                self._send_reply(post, initiative=app_parent_post.initiative, challenge=app_parent_post.challenge,
                                                 message=new_message)
                                # If we cannot understand the answer we reply saying that and discard the temporal post
                                temp_contribution.discard()
                                app_parent_post.do_answer()
                                return new_message
                        elif message.category == "incorrect_author_extrainfo":
                            # It is a reply to a wrong extra info notification
                            ret = self._process_extra_info(post, app_parent_post)
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
                             "'notification'. The post: '%s' will be ignored" % self.channel.get_text_post(post))
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
                if term not in text_post:
                    found_all_terms = False
            if found_all_terms:
                return message
        return None

    def _process_extra_info(self, post, app_parent_post):
        text_post = self.channel.get_text_post(post).lower()
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        extra_info = self._get_extra_info(text_post, campaign)
        if extra_info is not None:
            logger.info("%s's extra information was processed correctly. His/her contribution was permanently saved." %
                        self.channel.get_author(post).name)
            return self._preserve_temporal_post(post, extra_info, app_parent_post)
        else:
            self._increment_author_wrong_request(post)
            if self._get_author_wrong_request_counter(post) > self.settings['limit_wrong_requests']:
                if self._get_author_wrong_request_counter(post) - self.settings['limit_wrong_requests'] == 1:
                    logger.info("The participant %s has exceed the limit of wrong requests, his/her last contribution "
                                "will be discarded" % self.channel.get_author(post).name)
                    # A notification message will be sent only after the first time the limit was exceed
                    message = campaign.messages.get(category="contribution_cannot_save")
                    self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message)
                    # Discard the "incomplete" contribution
                    contribution_post = self._get_contribution_post(app_parent_post)
                    contribution_post.discard()
                    return message
                else:
                    logger.info("The participant %s has exceed the limit of %s wrong requests, the message will be "
                                "ignored" % (self.channel.get_author(post).name, self.settings['limit_wrong_requests']))
                    return None
            else:
                logger.info("%s's reply is in an incorrect format" % self.channel.get_author(post).name)
                message = campaign.extrainfo.messages.get(category="incorrect_author_extrainfo")
                self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge,message=message)
                return message

    def _preserve_temporal_post(self, post, extra_info, app_parent_post):
        author = self.channel.get_author(post)
        author.set_extra_info(extra_info)
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        post_db = self._get_contribution_post(app_parent_post)
        post_db.preserve()
        message = campaign.messages.get(category="thanks_contribution")
        self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message)
        author.reset_mistake_flags()
        return message

    def _update_contribution(self, post, app_parent_post):
        author = self.channel.get_author(post)
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        try:
            old_post = ContributionPost.objects.get(challenge=challenge, author=author.id, status="PE")  # Permanent
            new_post = ContributionPost.objects.filter(challenge=challenge, author=author.id, status="TE").\
                       order_by('-datetime').first()  # Temporal
            new_post.preserve()  # Preserve the newest (temporal)
            message = campaign.messages.get(category="thanks_change")
            self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message,
                             extra=new_post)
            old_post.discard()  # Discard the oldest (permanent)
            author.reset_mistake_flags()
            self._discard_temporal_post(author, challenge)  # Discard the remaining temporal posts related to 'challenge'
            return message
        except (ContributionPost.DoesNotExist, ContributionPost.MultipleObjectsReturned) as e:
            logger.critical("Error when trying to update a previous contribution. %s" % str(e))
            raise None

    def _get_extra_info(self, text, campaign):
        reg_expr = re.compile(campaign.extrainfo.format_answer)
        for term in text.split():
            if reg_expr.match(term):
                return term
        return None

    def _get_contribution_post(self, post):
        db_post = post
        while not db_post.contribution_parent_post:
            db_post = db_post.app_parent_post
        return db_post.contribution_parent_post

    def _process_input(self, post, challenge, parent_post_id=None):
        curated_input = self._validate_input(post, challenge)
        campaign = challenge.campaign
        if curated_input is not None:
            # It is a valid input
            if challenge.answers_from_same_author != self.NO_LIMIT_ANSWERS:
                existing_posts = list(self._has_already_posted(post, challenge))
                if len(existing_posts) > 0:
                    if challenge.answers_from_same_author == 1:
                        # Allow changes only if the number of allowed answers is 1
                        if len(existing_posts) > 1:
                            # It should exist only one contribution, but if not and as way of auto-recovering from an
                            # inconsistent state the newest ones will be discarded, leaving only the oldest one in
                            # the database
                            logger.critical("The challenge %s allows only one contribution per participant but the author "
                                            "%s has more than one contribution saved in the db. The newest ones will be "
                                            "discarded" % (challenge.name, self.channel.get_author(post).name))
                            for e_post in existing_posts[:]:
                                e_post.discard()
                                existing_posts.remove(e_post)
                                if len(existing_posts) == 1:
                                    break
                        existing_post = existing_posts[0]
                        if curated_input != existing_post.contribution:
                            # Only if the new contribution is different from the previous we will process it
                            # otherwise it will be ignored
                            self._save_post(post, curated_input, parent_post_id, challenge, temporal=True)
                            logger.info("A new contribution to the challenge %s was posted by the participant %s. "
                                        "It was saved temporarily" % (challenge.name,
                                                                      self.channel.get_author(post).name))
                            message = campaign.messages.get(category="ask_change_contribution")
                            self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge,
                                             message=message, extra=(curated_input, existing_post))
                            return message
                        else:
                            logger.info("The new contribution: %s is equal as the already existing" % curated_input)
                            return None

                    else:
                        if len(existing_posts) <= challenge.answers_from_same_author:
                            # Save participant's answer if the participant is still under the limit of allowed answers
                            return self._do_process_input(post, campaign, challenge, curated_input, parent_post_id)
                        else:
                            # Send a message saying that he/she has reached the limit of allowed answers
                            message = campaign.messages.get(category="limit_answers_reached")
                            self._send_reply(post, initiative=campaign.initiative, challenge=challenge, message=message)
                            self.channel.get_author(post).reset_mistake_flags()
                            logger.info("The participant %s has reached the limit of %s contributions allowed in the "
                                        "challenge %s" % (self.channel.get_author(post).name,
                                                          challenge.answers_from_same_author, challenge.name))
                            return message
                else:
                    return self._do_process_input(post, campaign, challenge, curated_input, parent_post_id)
            else:
                return self._do_process_input(post, campaign, challenge, curated_input, parent_post_id)
        else:
            # The input is not valid
            self._increment_author_wrong_input(post)
            if self._get_author_wrong_input_counter(post) > self.settings['limit_wrong_inputs']:
                logger.info("The participant %s has been banned because he/she has exceed the limit of %s wrong "
                            "contributions" % (self.channel.get_author(post).name, self.settings['limit_wrong_inputs']))
                # Ban author and notify him that he/she has been banned
                self._ban_author(post)
                new_message = campaign.messages.get(category="author_banned")
                self._send_reply(post, initiative=campaign.initiative, challenge=challenge, message=new_message)
                return new_message
            else:
                logger.info("The contribution '%s' of the participant %s does not satisfy the format required by the "
                            "challenge %s" % (self.channel.get_text_post(post), self.channel.get_author(post).name,
                                              challenge.name))
                # Reply saying that his/her input was wrong
                message = campaign.messages.get(category="incorrect_answer")
                self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message)
                return message

    def _do_process_input(self, post, campaign, challenge, curated_input, parent_post_id):
        if campaign.extrainfo is None or self._author_has_extrainfo(post) is not None:
            post_saved = self._save_post(post, curated_input, parent_post_id, challenge, temporal=False)
            message = campaign.messages.get(category="thanks_contribution")
            self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message,
                             extra=post_saved)
            self.channel.get_author(post).reset_mistake_flags()
            logger.info("The contribution '%s' of the participant %s to the challenge %s has been saved" %
                        (curated_input, self.channel.get_author(post).name, challenge.name))
        else:
            post_saved = self._save_post(post, curated_input, parent_post_id, challenge, temporal=True)
            message = campaign.extrainfo.messages.get(category="request_author_extrainfo")
            self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message,
                             extra=post_saved)
            logger.info("The contribution '%s' of the participant %s to the challenge %s has been saved temporarily "
                        "until getting the required additional information of the contributor" %
                        (curated_input, self.channel.get_author(post).name, challenge.name))
        return message

    def _validate_input(self, post, challenge):
        curated_text = self.channel.get_text_post(post)
        if challenge.style_answer == self.STRUCTURED_ANSWER:
            result = re.search(challenge.format_answer, curated_text)
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
    def _has_already_posted(self, post, challenge):
        author = self.channel.get_author(post)
        try:
            return ContributionPost.objects.filter(challenge=challenge, author=author.id, status='PE').order_by('-datetime')
        except ContributionPost.DoesNotExist:
            return None

    def _save_post(self, post, curated_input, parent_post_id, challenge, temporal):
        post_curated_info = self.channel.get_info_post(post)
        campaign = challenge.campaign
        initiative = campaign.initiative
        if temporal:
            status = 'TE'
        else:
            status = 'PE'
        post_to_save = ContributionPost(id_in_channel=post_curated_info['id'],
                                        datetime=timezone.make_aware(post_curated_info['datetime'],
                                                                     timezone.get_default_timezone()),
                                        contribution=curated_input, full_text=post_curated_info['text'],
                                        url=post_curated_info['url'], author=post_curated_info['author'],
                                        in_reply_to=parent_post_id, initiative=initiative,
                                        campaign=campaign, challenge=challenge, channel=post_curated_info['channel'],
                                        votes=post_curated_info['votes'], re_posts=post_curated_info['re_posts'],
                                        bookmarks=post_curated_info['bookmarks'], status=status)
        post_to_save.save(force_insert=True)
        if not temporal:
            self._discard_temporal_post(post_curated_info['author'], challenge)
        return post_to_save

    # Discard any temporal post existing within 'challenge' and posted by 'author'
    def _discard_temporal_post(self, author, challenge):
        try:
            temp_posts = ContributionPost.objects.filter(challenge=challenge, author=author.id, status='TE')
            for post in temp_posts:
                post.discard()
            return True
        except ContributionPost.DoesNotExist:
            return False

    def _author_has_extrainfo(self, post):
        author = self.channel.get_author(post)
        return author.get_extra_info()

    def _increment_author_wrong_input(self, post):
        author = self.channel.get_author(post)
        author.add_input_mistake()

    def _increment_author_wrong_request(self, post):
        author = self.channel.get_author(post)
        author.add_request_mistake()

    def _get_author_wrong_input_counter(self, post):
        author = self.channel.get_author(post)
        return author.get_input_mistakes()

    def _get_author_wrong_request_counter(self, post):
        author = self.channel.get_author(post)
        return author.get_request_mistakes()

    def _ban_author(self, post):
        author = self.channel.get_author(post)
        author.ban()

    def _send_reply(self, post, initiative, challenge, message, extra=None):
        msg = None
        author_username = self.channel.get_author_username(post)
        author_id = self.channel.get_author_id(post)
        current_datetime = time.strftime(self.settings['datetime_format'])
        type_msg = ""
        post_id = self.channel.get_id_post(post)
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
            payload = {'parent_post_id': self.channel.get_parent_post_id(post), 'type_msg': type_msg,
                       'post_id': post_id, 'initiative_id': initiative.id, 'author_username': author_username,
                       'author_id': author_id, 'campaign_id': challenge.campaign.id, 'challenge_id': challenge.id,
                       'initiative_short_url': short_url}
            payload_json = json.dumps(payload)
            self.channel.queue_message(message=msg, type_msg="RE", recipient_id=post_id, payload=payload_json)

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


class SocialNetwork():
    __metaclass__  = abc.ABCMeta
    initiatives = None
    accounts = None
    hashtags = None
    msg_duplicate_code = 187
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
    def _send_direct_message(self, message, author_username, payload):
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
    def get_author_username(self, post):
        """Get the username (screen-name) of the post author"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_type_post(self, message):
        """Whether it is a new post or a reply"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_text_post(self, post):
        """Return the text of the post"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_id_post(self, post):
        """Return the id of the post"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_parent_post_id(self, post):
        """Return the id of the post that the current post is in reply to """
        raise NotImplementedError

    @abc.abstractmethod
    def get_info_post(self, post):
        """Return the id, datetime, text, url, author, initiative, channel, votes, re_posts and bookmarks of the post"""
        raise NotImplementedError

    @abc.abstractmethod
    def build_url_post(self, post):
        """Build and return the url of the post"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_author(self, post):
        """Return the author of the post. Here information about the author is taken from the database"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_author_id(self, post):
        """Return the id author of the post. Here the id of the author is taken from the post itself"""
        raise NotImplementedError

    @abc.abstractmethod
    def register_new_author(self, post):
        """Register in the database a new author"""
        raise NotImplementedError

    @abc.abstractmethod
    def has_initiative_hashtags(self, post):
        """Check whether the text of the post has the hashtags the identifies the initiative"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_challenge_info(self, post, initiative):
        """Return information about the challenge"""
        raise NotImplementedError

    def disconnect(self):
        # Kill process that manages the message queue
        try:
            os.kill(self.pid_messenger, signal.SIGKILL)
            logger.info("Messenger has been stopped")
        except Exception as e:
            logger.error("The process running the messenger does not exist")
        # Kill the process that listens the firehose of Twitter
        try:
            os.kill(self.pid_listener, signal.SIGKILL)
            logger.info("Listener has been stopped")
        except Exception as e:
            logger.error("The process running the listener does not exist")
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
                    res = self._send_direct_message(msg_to_dispatch.message_text, payload_hash['author_username'], payload_hash)
                if res['delivered']:
                    msg_to_dispatch.delete()
                else:
                    if res['response'][0]['code'] == self.msg_duplicate_code:
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
        app_post = AppPost(id_in_channel=channel.get_id_post(response), datetime=timezone.now(),
                           text=channel.get_text_post(response), url=channel.build_url_post(response),
                           app_parent_post=app_parent_post, initiative=initiative, campaign=campaign,
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
            self.save_post_db(payload, response, self)
            return {'delivered': True, 'response': response}
        except tweepy.TweepError as e:
            reason = ast.literal_eval(e.reason)
            logger.error("The post couldn't be delivered. Reason: %s" % reason[0]['message'])
            return {'delivered': False, 'response': reason}

    def _send_direct_message(self, message, author_username, payload):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        try:
            response = api.send_direct_message(screen_name=author_username, text=message)
            logger.info("The message '%s' has been sent directly to %s through Twitter" % (message, author_username))
            self.save_post_db(payload, response, self)
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
            self.save_post_db(payload, response, self)
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
            return api.destroy_status(post.id_str)
        except tweepy.TweepError, e:
            logger.error("The post %s couldn't be destroyed. %s" % (post.id_str, e.reason))

    def get_info_user(self, id_user):
        api = tweepy.API(auth_handler=self.auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        return api.get_user(id_user)

    def get_type_post(self, post):
        if post.in_reply_to_status_id_str is None:
            return 'status', None
        else:
            return 'reply', post.in_reply_to_status_id_str

    def get_text_post(self, post):
        return post.text.encode('utf-8')

    def get_id_post(self, post):
        return post.id_str

    def get_parent_post_id(self, post):
        return post.in_reply_to_status_id_str

    def get_info_post(self, post):
        return {'id': post.id_str, 'datetime': post.created_at, 'text': post.text.encode('utf-8'),
                'url': self.build_url_post(post), 'author': self.get_author(post), 'channel': self.channel, 'votes': 0,
                're_posts': post.retweet_count, 'bookmarks': post.favorite_count}

    def build_url_post(self, post):
        return self.channel.url + post.author.screen_name + "/status/" + post.id_str

    def get_author(self, post):
        try:
            return Author.objects.get(id_in_channel=post.author.id_str, channel=self.channel.id)
        except Author.DoesNotExist:
            return None

    def get_author_id(self, post):
        return post.author.id_str

    def get_author_username(self, post):
        return "@" + post.author.screen_name

    def register_new_author(self, post):
        author_post = post.author
        if author_post.description:
            author_desc = author_post.description.encode('utf-8')
        else:
            author_desc = None

        new_author = Author(name=author_post.name.encode('utf-8'), screen_name=author_post.screen_name,
                            id_in_channel=author_post.id_str, channel=self.channel,
                            friends=author_post.friends_count, followers=author_post.followers_count,
                            url=self.channel.url + post.author.screen_name, description=author_desc,
                            language=author_post.lang, posts_count=author_post.statuses_count)
        new_author.save(force_insert=True)
        return new_author

    def has_initiative_hashtags(self, post):
        for initiative in self.initiatives:
            initiative_hashtag = initiative.hashtag
            for post_hashtag in post.entities['hashtags']:
                if post_hashtag['text'].lower().strip() == initiative_hashtag.lower().strip():
                    return initiative
        return None

    def get_challenge_info(self, post, initiative):
        campaigns = initiative.campaign_set.all()
        for campaign in campaigns:
            challenges = campaign.challenge_set.all()
            for challenge in challenges:
                challenge_hashtag = challenge.hashtag
                for post_hashtag in post.entities['hashtags']:
                    if post_hashtag['text'].lower().strip() == challenge_hashtag.lower().strip():
                        return challenge
        return None


class TwitterListener(tweepy.StreamListener):
    manager = None

    def __init__(self, manager):
        super(TwitterListener, self).__init__()
        self.manager = manager

    def on_status(self, status):
        self.manager.manage_post(status)
        return True

    def on_error(self, status_code):
        logger.error("Error in the firehose, status code: %s" % str(status_code))
        return True  # To continue listening

    def on_timeout(self):
        logger.warning("Got timeout from the firehose")
        return True  # To continue listening
