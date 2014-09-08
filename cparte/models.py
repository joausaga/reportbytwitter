from django.db import models
from django.utils import timezone

import tweepy
import abc
import re
import time
import logging


logger = logging.getLogger(__name__)


""" Data Models
"""


class Channel(models.Model):
    name = models.CharField(max_length=50)
    enabled = models.BooleanField(default=False)
    status = models.BooleanField(default=False, blank=True, editable=False)
    consumer_key = models.CharField(max_length=100)
    consumer_secret = models.CharField(max_length=100)
    access_token = models.CharField(max_length=100)
    access_token_secret = models.CharField(max_length=100)
    url = models.URLField(null=True)
    app_account_id = models.CharField(max_length=50)
    max_length_msgs = models.IntegerField(null=True, blank=True, help_text="Maximum length of messages to send through"
                                                                           "this channel from the application. Leave it "
                                                                           "blank for unlimited lengths.")

    def __unicode__(self):
        return self.name

    def on(self):
        self.status = True
        self.save()

    def off(self):
        self.status = False
        self.save()


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
    channel = models.ForeignKey(Channel)

    def __unicode__(self):
        return self.name


class Setting(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(null=True)
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
    screen_name = models.CharField(max_length=100)
    id_in_channel = models.CharField(max_length=50)
    channel = models.ForeignKey(Channel)
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
    name = models.CharField(max_length=50)
    organizer = models.CharField(max_length=50)
    hashtag = models.CharField(max_length=14, help_text="Max length 14 characters (do not include '#')")
    url = models.URLField(null=True, blank=True)

    def __unicode__(self):
        return self.name


class Campaign(models.Model):
    name = models.CharField(max_length=50)
    initiative = models.ForeignKey(Initiative)
    hashtag = models.CharField(max_length=14, null=True, blank=True,
                               help_text="Max length 14 characters (do not include '#')")
    url = models.URLField(null=True, blank=True)
    extrainfo = models.ForeignKey(ExtraInfo, blank=True, null=True)
    messages = models.ManyToManyField(Message)

    def __unicode__(self):
        return self.name


class Challenge(models.Model):
    name = models.CharField(max_length=50)
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
    temporal = models.BooleanField(default=True)
    votes = models.IntegerField(default=0)      # e.g. +1 in Google+, like in Facebook
    re_posts = models.IntegerField(default=0)   # e.g. Share in Facebook, RT in Twitter
    bookmarks = models.IntegerField(default=0)  # e.g. Favourite in Twitter

    def __unicode__(self):
        return self.url

    def preserve(self):
        self.temporal = False
        self.save()


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
    CATEGORIES = (('NT', 'Notification'), ('TH', 'Thanks'), ('EN', 'Engagement'), ('PR', 'Promotion'))
    category = models.CharField(max_length=3, choices=CATEGORIES)

    def __unicode__(self):
        if self.url:
            return self.url
        else:
            return self.text


""" Domain Models
"""


class MetaChannel():
    channels = {'twitter': None, 'facebook': None, 'google_plus': None, 'instagram': None}

    @classmethod
    def authenticate(cls, channel, initiative_name):
        channel_name = channel.name.lower()
        initiative = Initiative.objects.get(name=initiative_name)
        if channel_name == "twitter":
            cls.channels[channel_name] = Twitter(channel.consumer_key, channel.consumer_secret, channel.access_token,
                                                 channel.access_token_secret, initiative)
        else:
            logger.error("Unknown channel: %s" % channel_name)
            return
        cls.channels[channel_name].authenticate()

    @classmethod
    def broadcast(cls, message):
        for name in cls.channels.iterkeys():
            if cls.channels[name]:
                cls.channels[name].post_public(message)

    @classmethod
    def post_public(cls, channels, message):
        for channel in channels:
            channel = channel.lower()
            if cls.channels[channel]:
                cls.channels[channel].post_public(message)
            else:
                logger.error("The channel %s is unavailable, cannot post into it" % channel)

    @classmethod
    def send_direct_message(cls, channel_name, recipient, message):
        channel_name = channel_name.lower()
        if cls.channels[channel_name]:
            cls.channels[channel_name].send_direct_message(recipient, message)
        else:
            logger.error("The channel %s is unavailable, cannot send direct message through it" % channel_name)

    @classmethod
    def reply_to(cls, channel_name, id_message, new_message):
        channel_name = channel_name.lower()
        if cls.channels[channel_name]:
            cls.channels[channel_name].reply_to(id_message, new_message)
        else:
            logger.error("The channel %s is unavailable, cannot post to a user through it" % channel_name)

    @classmethod
    def get_post(cls, channel_name, id_post):
        channel_name = channel_name.lower()
        if cls.channels[channel_name]:
            cls.channels[channel_name].get_post(id_post)
        else:
            logger.error("The channel %s is unavailable, cannot get a post" % channel_name)

    @classmethod
    def get_info_user(cls, channel_name, id_user):
        channel_name = channel_name.lower()
        if cls.channels[channel_name]:
            cls.channels[channel_name].get_info_user(id_user)
        else:
            logger.error("The channel %s is unavailable, cannot get info about a user" % channel_name)

    @classmethod
    def listen(cls, channel_name, followings):
        channel_name = channel_name.lower()
        if cls.channels[channel_name.lower()]:
            cls.channels[channel_name].listen(followings)
        else:
            logger.error("The channel %s is unavailable, cannot be listened" % channel_name)

    @classmethod
    def disconnect(cls, channel_name):
        channel_name = channel_name.lower()
        if cls.channels[channel_name]:
            cls.channels[channel_name].disconnect()
        else:
            logger.error("The channel %s is unavailable, cannot disconnect it" % channel_name)


class PostManager():
    channel = None
    settings = {}
    NO_LIMIT_ANSWERS = -1
    NOTIFICATION_MESSAGE = "NT"
    ENGAGE_MESSAGE = "EN"
    STRUCTURED_ANSWER = "ST"
    FREE_ANSWER = "FR"

    def __init__(self, channel):
        self.channel = channel
        self._set_settings()

    def _set_settings(self):
        try:
            self.settings['limit_wrong_inputs'] = Setting.objects.get(name="limit_wrong_inputs").get_casted_value()
            self.settings['limit_wrong_requests'] = Setting.objects.get(name="limit_wrong_requests").get_casted_value()
            self.settings['datetime_format'] = Setting.objects.get(name="datetime_format").value
        except Setting.DoesNotExist as e:
            e_msg = "Unknown setting %s, the post manager cannot be started" % e
            logger.critical(e_msg)
            raise Exception(e_msg)

    def manage_post(self, post):
        author = self.channel.get_author(post)
        if author is None or not author.is_banned():
            type_post = self.channel.get_type_post(post)
            if type_post[0] == "reply" or type_post[0] == "status":
                self._do_manage(post, author, type_post[1])
            else:
                logger.warninig("The type %s of the message is unknown. Message text: '%s'" %
                                (type_post[0], self.channel.get_text_post(post)))
        else:
            logger.info("The post was ignore, its author, called %s, is in the black list" % author.screen_name)

    def _do_manage(self, post, author, parent_post_id=None):
        app_parent_post = None

        if parent_post_id is None:
            if self.channel.get_author_id(post) == self.channel.get_app_account_id():
                return  # So far, I'm not interested in processing my own posts
            else:
                within_initiative = self.channel.has_initiative_hashtags(post)
                challenge = self.channel.get_challenge_info(post) if within_initiative else None
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
                return  # I'm not interested in processing replies that were not posted to the app posts

        if within_initiative and challenge:
            if author is None:
                author = self.channel.register_new_author(post)
            logger.info("Post from %s within the initiative: %s, campaign: %s, challenge: %s" %
                        (author.screen_name, challenge.campaign.initiative.name, challenge.campaign.name, challenge.name))
            self._process_input(post, challenge, parent_post_id)
        elif parent_post_id is not None:  # It is a reply but not to a challenge post
            if app_parent_post and app_parent_post.category == self.NOTIFICATION_MESSAGE:
                # Only process replies that were made to app posts categorized as notification (NT)
                message = self._get_parent_post_message(app_parent_post.text, app_parent_post.campaign)
                if message:
                    if message.category == "request_author_extrainfo":
                        # It is a reply to an extra info request
                        self._process_extra_info(post, app_parent_post)
                    elif message.category == "incorrect_answer":
                        # It is a reply to a wrong input notification
                        author = self.channel.get_author(post)
                        if not author.is_banned():
                            self._process_input(post, app_parent_post.challenge, parent_post_id)
                    elif message.category == "ask_change_contribution":
                        temp_contribution = self._get_contribution_post(app_parent_post)
                        # It is a reply to a question about changing previous input
                        answer_terms = message.answer_terms.split()
                        found_term = False
                        for answer_term in answer_terms:
                            if answer_term in self.channel.get_text_post(post).lower():
                                found_term = True
                        if found_term:
                            self._update_contribution(post, app_parent_post)
                        else:
                            new_message = app_parent_post.campaign.messages.get(category="not_understandable_change_contribution_reply")
                            self._send_reply(post, initiative=app_parent_post.initiative, challenge=app_parent_post.challenge,
                                             message=new_message)
                            # If we cannot understand the answer we reply saying that and delete the temporal post
                            temp_contribution.delete()
                    elif message.category == "incorrect_author_extrainfo":
                        # It is a reply to a wrong extra info notification
                        self._process_extra_info(post, app_parent_post)
                    else:
                        logger.info("Unknown message category. Text: %s" % app_parent_post.text)
                else:
                    logger.info("Impossible to determine to which app message this post '%s' belongs to" %
                                app_parent_post.text)
            else:
                logger.error("App parent post does not exist, the post: '%s' will be ignored" %
                             self.channel.get_text_post(post))

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
            self._save_temporal_post(post, extra_info, app_parent_post)
        else:
            self._increment_author_wrong_request(post)
            if self._get_author_wrong_request_counter(post) > self.settings['limit_wrong_requests']:
                if self._get_author_wrong_request_counter(post) - self.settings['limit_wrong_requests'] == 1:
                    logger.info("The participant %s has exceed the limit of wrong requests, his/her last contribution "
                                "will be deleted" % self.channel.get_author(post).name)
                    # A notification message will be sent only after the first time the limit was exceed
                    message = campaign.messages.get(category="contribution_cannot_save")
                    self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message)
                    # Delete the "incomplete" contribution
                    contribution_post = self._get_contribution_post(app_parent_post)
                    contribution_post.delete()
                else:
                    logger.info("The participant %s has exceed the limit of %s wrong requests, the message will be "
                                "ignored" % (self.channel.get_author(post).name), self.settings['limit_wrong_requests'])
            else:
                logger.info("%s's reply is in an incorrect format" % self.channel.get_author(post).name)
                message = campaign.extrainfo.messages.get(category="incorrect_author_extrainfo")
                self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge,message=message)

    def _save_temporal_post(self, post, extra_info, app_parent_post):
        author = self.channel.get_author(post)
        author.set_extra_info(extra_info)
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        post_db = self._get_contribution_post(app_parent_post)
        post_db.preserve()
        message = campaign.messages.get(category="thanks_contribution")
        self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message)
        author.reset_mistake_flags()

    def _update_contribution(self, post, app_parent_post):
        author = self.channel.get_author(post)
        campaign = app_parent_post.campaign
        challenge = app_parent_post.challenge
        contributions = ContributionPost.objects.filter(challenge=challenge, author=author.id)
        if len(contributions) == 2:
            old_post = contributions[0] if not contributions[0].temporal else contributions[1]
            new_post = contributions[0] if contributions[0].temporal else contributions[1]
            new_post.preserve()  # Preserve the newest
            message = campaign.messages.get(category="thanks_change")
            self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message,
                             extra=new_post)
            old_post.delete()  # Delete the oldest
            author.reset_mistake_flags()
        else:
            logger.critical("The number of contributions (%s) of the author %s does not satisfy the challenge's "
                            "required number (2). Until fixing the problem the contribution of this author will not be"
                            "updated" % (len(contributions), author.name))

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
                existing_posts = self._has_already_posted(post, challenge)
                if len(existing_posts) > 0:
                    if challenge.answers_from_same_author == 1:
                        # Allow changes only if the number of allowed answers is 1
                        if len(existing_posts) == 1:
                            # In theory (?) it should exist only one
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
                            else:
                                logger.info("The new contribution: %s is equal as the already existing" % curated_input)
                        else:
                            logger.critical("The challenge %s allows only one contribution per participant but the %s "
                                            "has more than one contribution saved in the db. Please delete one of them"
                                            % (challenge.name, self.channel.get_author(post).name))
                    else:
                        if len(existing_posts) <= challenge.answers_from_same_author:
                            # Save participant's answer if the participant is still under the limit of allowed answers
                            self._do_process_input(post, campaign, challenge, curated_input, parent_post_id)
                        else:
                            # Send a message saying that he/she has reached the limit of allowed answers
                            message = campaign.messages.get(category="limit_answers_reached")
                            self._send_reply(post, initiative=campaign.initiative, challenge=challenge, message=message)
                            self.channel.get_author(post).reset_mistake_flags()
                            logger.info("The participant %s has reached the limit of %s contributions allowed in the "
                                        "challenge %s" % (self.channel.get_author(post).name,
                                                          challenge.answers_from_same_author, challenge.name))
                else:
                    self._do_process_input(post, campaign, challenge, curated_input, parent_post_id)
            else:
                self._do_process_input(post, campaign, challenge, curated_input, parent_post_id)
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
            else:
                logger.info("The contribution '%s' of the participant %s does not satisfy the format required by the "
                            "challenge %s" % (self.channel.get_text_post(post), self.channel.get_author(post).name,
                                              challenge.name))
                # Reply saying that his/her input was wrong
                message = campaign.messages.get(category="incorrect_answer")
                self._send_reply(post=post, initiative=campaign.initiative, challenge=challenge, message=message)

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

    def _validate_input(self, post, challenge):
        curated_text = self.channel.get_text_post(post).encode('utf-8')
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
            return ContributionPost.objects.filter(challenge=challenge, author=author.id)
        except ContributionPost.DoesNotExist:
            return None

    def _save_post(self, post, curated_input, parent_post_id, challenge, temporal):
        post_curated_info = self.channel.get_info_post(post)
        campaign = challenge.campaign
        post_to_save = ContributionPost(id_in_channel=post_curated_info['id'],
                                        datetime=timezone.make_aware(post_curated_info['datetime'],
                                                                     timezone.get_default_timezone()),
                                        contribution=curated_input, full_text=post_curated_info['text'],
                                        url=post_curated_info['url'], author=post_curated_info['author'],
                                        in_reply_to=parent_post_id, initiative=post_curated_info['initiative'],
                                        campaign=campaign, challenge=challenge, channel=post_curated_info['channel'],
                                        votes=post_curated_info['votes'], re_posts=post_curated_info['re_posts'],
                                        bookmarks=post_curated_info['bookmarks'], temporal=temporal)
        post_to_save.save(force_insert=True)
        return post_to_save

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
        current_datetime = time.strftime(self.settings['datetime_format'])
        type_msg = ""

        if message.category == "thanks_contribution":
            msg = message.body % (author_username, challenge.hashtag, initiative.url)
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
            msg = message.body % (author_username, challenge.hashtag, extra.contribution, initiative.url)
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
            response = self.channel.reply_to(post, msg)
            if response:
                logger.info("Sent the post '%s' to %s through %s" % (msg, author_username, self.channel.get_name()))
                self._save_app_post(post, response, initiative, challenge, type_msg)
            else:
                logger.error("The message '%s' couldn't be delivered to %s" % (msg, author_username))

    def _save_app_post(self, post, response, initiative, challenge, type_msg):
        parent_post_id = self.channel.get_parent_post_id(post)
        post_id = self.channel.get_id_post(post)
        if parent_post_id is not None:
            app_parent_post = AppPost.objects.get(id_in_channel=parent_post_id)
            try:
                contribution_parent_post = ContributionPost.objects.get(id_in_channel=post_id)
            except ContributionPost.DoesNotExist:
                contribution_parent_post = None
        else:
            app_parent_post = None
            contribution_parent_post = ContributionPost.objects.get(id_in_channel=post_id)
        app_post = AppPost(id_in_channel=self.channel.get_id_post(response), datetime=timezone.now(),
                           text=response.text, url=self.channel.build_url_post(response),
                           app_parent_post=app_parent_post, initiative=initiative, campaign=challenge.campaign,
                           contribution_parent_post=contribution_parent_post, challenge=challenge,
                           channel=self.channel.get_channel_obj(), votes=0, re_posts=0, bookmarks=0, delivered=True,
                           category=type_msg)
        app_post.save(force_insert=True)
        if app_post.id is None:
            if self.channel.delete_post(response) is not None:
                logger.error("The app post couldn't be saved into the db, so its corresponding post was deleted from "
                             "%s" % self.channel.get_name())
            else:
                logger.critical("The app post couldn't be saved into the db, but its corresponding post couldn't be "
                                "delete from %s. The app may be in an inconsistent state" % self.channel.get_name())
        else:
            logger.info("The app post with the id: %s was created" % app_post.id)


class SocialNetwork():
    __metaclass__  = abc.ABCMeta

    @abc.abstractmethod
    def authenticate(self):
        """Authenticate into the channel"""

    @abc.abstractmethod
    def listen(self, users):
        """Listen the channel"""

    @abc.abstractmethod
    def post_public(self, message):
        """Post a public messages into the channel"""

    @abc.abstractmethod
    def send_direct_message(self, id_user, message):
        """Send a private message to a particular user"""

    @abc.abstractmethod
    def reply_to(self, post, message):
        """Reply to an existing post"""

    @abc.abstractmethod
    def get_post(self, id_post):
        """Get a post previously published in the channel and identified by id_post"""

    @abc.abstractmethod
    def delete_post(self, id_post):
        """Delete the post identified by id_post"""

    @abc.abstractmethod
    def get_info_user(self, id_user):
        """Get information about a particular user"""

    @abc.abstractmethod
    def get_author_username(self, post):
        """Get the username (screen-name) of the post author"""

    @abc.abstractmethod
    def get_type_post(self, message):
        """Whether it is a new post or a reply"""

    @abc.abstractmethod
    def get_text_post(self, post):
        """Return the text of the post"""

    @abc.abstractmethod
    def get_id_post(self, post):
        """Return the id of the post"""

    @abc.abstractmethod
    def get_parent_post_id(self, post):
        """Return the id of the post that the current post is in reply to """

    @abc.abstractmethod
    def get_info_post(self, post):
        """Return the id, datetime, text, url, author, initiative, channel, votes, re_posts and bookmarks of the post"""

    @abc.abstractmethod
    def build_url_post(self, post):
        """Build and return the url of the post"""

    @abc.abstractmethod
    def get_author(self, post):
        """Return the author of the post. Here information about the author is taken from the database"""

    @abc.abstractmethod
    def get_author_id(self, post):
        """Return the id author of the post. Here the id of the author is taken from the post itself"""

    @abc.abstractmethod
    def register_new_author(self, post):
        """Register in the database a new author"""

    @abc.abstractmethod
    def has_initiative_hashtags(self, post):
        """Check whether the text of the post has the hashtags the identifies the initiative"""

    @abc.abstractmethod
    def get_challenge_info(self, post):
        """Return information about the challenge"""

    @abc.abstractmethod
    def disconnect(self):
        """Disconnect the established connection"""

    @abc.abstractmethod
    def get_app_account_id(self):
        """Return the id of the account bound to the application"""

    @abc.abstractmethod
    def get_channel_obj(self):
        """Return the model object associated to the channel"""

    @abc.abstractmethod
    def get_name(self):
        """Return the name of the channel"""


class Twitter(SocialNetwork):
    auth_handler = None
    consumer_key = None
    consumer_secret = None
    access_token = None
    access_token_secret = None
    api = None
    channel = None
    initiative = None
    stream = None

    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, initiative):
        self.channel = Channel.objects.get(name="twitter")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.initiative = initiative

    def authenticate(self):
        self.auth_handler = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        self.auth_handler.set_access_token(self.access_token, self.access_token_secret)
        self.api = tweepy.API(self.auth_handler)

    def listen(self, followings):
        hashtags = [self.initiative.hashtag]
        for campaign in self.initiative.campaign_set.all():
            if campaign.hashtag is not None:
                hashtags.append(campaign.hashtag)
            for challenge in campaign.challenge_set.all():
                hashtags.append(challenge.hashtag)

        manager = PostManager(self)
        listener = TwitterListener(manager)
        self.stream = tweepy.Stream(self.auth_handler, listener)
        self.stream.filter(follow=followings, track=hashtags, async=True)
        self.channel.on()
        logger.info("Starting to listen Twitter Stream")

    def post_public(self, message):
        try:
            return self.api.update_status(status=message)
        except tweepy.TweepError, e:
            logger.error("The post couldn't be delivered. %s" % e.reason)
            return None

    def send_direct_message(self, id_user, message):
        try:
            return self.api.send_direct_message(user_id=id_user,text=message)
        except tweepy.TweepError, e:
            logger.error("The post couldn't be delivered. %s" % e.reason)
            return None

    def reply_to(self, post, message):
        try:
            return self.api.update_status(status=message, in_reply_to_status_id=post.id_str)
        except tweepy.TweepError, e:
            logger.error("The post couldn't be delivered. %s" % e.reason)
            return None

    def get_post(self, id_post):
        return self.api.get_status(id_post)

    def delete_post(self, post):
        try:
            return self.api.destroy_status(post.id_str)
        except tweepy.TweepError, e:
            logger.error("The post %s couldn't be destroyed. %s" % (post.id_str, e.reason))

    def get_info_user(self, id_user):
        return self.api.get_user(id_user)

    def get_type_post(self, post):
        if post.in_reply_to_status_id_str is None:
            return 'status', None
        else:
            return 'reply', post.in_reply_to_status_id_str

    def get_text_post(self, post):
        return post.text

    def get_id_post(self, post):
        return post.id_str

    def get_parent_post_id(self, post):
        return post.in_reply_to_status_id_str

    def get_info_post(self, post):
        return {'id': post.id_str, 'datetime': post.created_at, 'text': post.text, 'url': self.build_url_post(post),
                'author': self.get_author(post), 'initiative': self.initiative, 'channel': self.channel, 'votes': 0,
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
        new_author = Author(name=author_post.name, screen_name=author_post.screen_name,
                            id_in_channel=author_post.id_str, channel=self.channel,
                            friends=author_post.friends_count, followers=author_post.followers_count,
                            url=self.channel.url + post.author.screen_name)
        new_author.save(force_insert=True)
        return new_author

    def has_initiative_hashtags(self, post):
        initiative_hashtag = self.initiative.hashtag
        for post_hashtag in post.entities['hashtags']:
            if post_hashtag['text'].lower().strip() == initiative_hashtag.lower().strip():
                return True
        return False

    def get_challenge_info(self, post):
        campaigns = self.initiative.campaign_set.all()
        for campaign in campaigns:
            challenges = campaign.challenge_set.all()
            for challenge in challenges:
                challenge_hashtag = challenge.hashtag
                for post_hashtag in post.entities['hashtags']:
                    if post_hashtag['text'].lower().strip() == challenge_hashtag.lower().strip():
                        return challenge
        return None

    def disconnect(self):
        if self.stream is not None:
            self.stream.disconnect()
            self.channel.off()
            logger.info("Twitter channel has been disconnected...")
        else:
            logger.debug("Twitter channel is already disconnected")

    def get_app_account_id(self):
        return self.channel.app_account_id

    def get_channel_obj(self):
        return self.channel

    def get_name(self):
        return self.channel.name


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