from django.db import models
from django.utils import timezone

import social_network
import logging
import post_manager

logger = logging.getLogger(__name__)


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
    pid = models.CharField(max_length=50, editable=False, null=True)

    def __unicode__(self):
        return self.name

    def connect(self, pid):
        self.status = True
        self.pid = pid
        self.save()

    def disconnect(self):
        if self.status:
            self.pid = ""
            self.status = False
            self.save()
        else:
            logger.info("Channel already off!")


class Account(models.Model):
    owner = models.CharField(max_length=50)
    id_in_channel = models.CharField(max_length=50)
    handler = models.CharField(max_length=50)
    url = models.URLField()
    channel = models.ForeignKey(Channel)
    consumer_key = models.CharField(max_length=100)
    consumer_secret = models.CharField(max_length=100)
    token = models.CharField(max_length=100)
    token_secret = models.CharField(max_length=100)

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
                    ('already_answered_unchangeable_challenge', 'Participant already answered an unchangeable challenge'),
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
    hashtag = models.CharField(unique=True, max_length=14, help_text="Max length 14 characters (do not include '#')")
    url = models.URLField(null=True, blank=True)
    language = models.CharField(max_length=3, choices=LANGUAGES)
    account = models.ForeignKey(Account)
    social_sharing_message = models.CharField(max_length=200, blank=True, null=True,
                                              help_text="Default text for social sharing buttons")

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
    answers_from_same_author = models.IntegerField(default=1, help_text="Number of allowed answers from the same "
                                                                        "author. Use -1 for not limit")
    url = models.URLField(null=True, blank=True)
    accept_changes = models.BooleanField(default=True)

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
    source = models.CharField(max_length=100, null=True)

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


class SharePost(models.Model):
    id_in_channel = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    text = models.TextField()
    url = models.URLField()
    author = models.ForeignKey(Author)
    initiative = models.ForeignKey(Initiative)
    campaign = models.ForeignKey(Campaign)
    challenge = models.ForeignKey(Challenge)
    channel = models.ForeignKey(Channel)
    votes = models.IntegerField(default=0)      # e.g. +1 in Google+, like in Facebook
    re_posts = models.IntegerField(default=0)   # e.g. Share in Facebook, RT in Twitter
    bookmarks = models.IntegerField(default=0)  # e.g. Favourite in Twitter
    similarity = models.IntegerField(default=0)


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


# Social Network Middleware Channel
class ChannelMiddleware():
    twitter = None
    facebook = None
    gplus = None

    def __init__(self):
        enabled_channels = Channel.objects.filter(enabled=True)
        for channel in enabled_channels:
            if channel.name.lower() == "twitter":
                self.twitter = social_network.Twitter(self)
            elif channel.name.lower() == "facebook":
                self.facebook = social_network.Facebook(self)
            elif channel.name.lower() == "googleplus":
                self.gplus = social_network.GooglePlus(self)
            else:
                logger.error("Unknown channel: %s" % channel.name)
        self.post_manager = post_manager.PostManager(self)

    def set_initiatives(self, initiative_ids, channel_name):
        initiatives = None
        hashtags = None
        account_ids = []
        for id_initiative in initiative_ids:
            try:
                initiative = Initiative.objects.get(pk=id_initiative)
            except Initiative.DoesNotExist:
                e_msg = "Does not exist an initiative identified with the id %s" % id_initiative
                logger.critical(e_msg)
                raise Exception(e_msg)

            if initiatives:
                initiatives.append(initiative)
                hashtags.append(initiative.hashtag)
            else:
                initiatives = [initiative]
                hashtags = [initiative.hashtag]
            account_ids.append(initiative.account.id)

            # Add to the array of hashtags the hashtags of the initiative's campaigns
            for campaign in initiative.campaign_set.all():
                if campaign.hashtag is not None:
                    hashtags.append(campaign.hashtag)
                # Add to the array of hashtags the hashtags of the campaign's challenges
                for challenge in campaign.challenge_set.all():
                    hashtags.append(challenge.hashtag)
        accounts = self.set_accounts(account_ids)

        if channel_name.lower() == "twitter":
            self.twitter.set_initiatives(initiatives)
            self.twitter.set_hashtags(hashtags)
            self.twitter.set_accounts(accounts)
        elif channel_name.lower() == "facebook":
            self.facebook.set_initiatives(initiatives)
            self.facebook.set_hashtags(hashtags)
            self.facebook.set_accounts(accounts)
        elif channel_name.lower() == "googleplus":
            self.gplus.set_initiatives(initiatives)
            self.gplus.set_hashtags(hashtags)
            self.gplus.set_accounts(accounts)
        else:
            logger.error("Unknown channel: %s" % channel_name)

    @staticmethod
    def set_accounts(account_ids):
        accounts = []
        for id_account in account_ids:
            try:
                accounts.append(Account.objects.get(pk=id_account).id_in_channel)
            except Account.DoesNotExist:
                e_msg = "Does not exist an account identified with the id %s" % id_account
                logger.critical(e_msg)
                raise Exception(e_msg)
        return accounts

    def get_account_ids(self, channel_name):
        if channel_name.lower() == "twitter":
            return self.twitter.get_accounts()
        elif channel_name.lower() == "facebook":
            return self.facebook.get_accounts()
        elif channel_name.lower() == "googleplus":
            return self.gplus.get_accounts()
        else:
            logger.error("Unknown channel: %s" % channel_name)
            return None

    def send_message(self, message, type_msg, recipient_id, payload, channel_name):

        if channel_name.lower() == "twitter":
            ret = self.twitter.send_message(message, type_msg, recipient_id, payload)
            url = self.twitter.get_url()
            channel = self.twitter
            channel_obj = self.twitter.get_channel_obj()
        elif channel_name.lower() == "facebook":
            ret = self.facebook.send_message(message, type_msg, recipient_id, payload)
            url = self.facebook.get_url()
            channel = self.facebook
            channel_obj = self.facebook.get_channel_obj()
        elif channel_name.lower() == "googleplus":
            ret = self.gplus.send_message(message, type_msg, recipient_id, payload)
            url = self.gplus.get_url()
            channel = self.gplus
            channel_obj = self.gplus.get_channel_obj()
        else:
            logger.error("Unknown channel: %s" % channel_name)
            return
        if ret and ret['delivered']:
            response_dict = self.to_dict(ret['response'], url)
            app_post = self.save_post_db(payload, response_dict, channel_obj)
            if app_post.id is None:
                if channel.delete_post(response_dict) is not None:
                    logger.error("The app post couldn't be saved into the db, so its corresponding post was deleted "
                                 "from %s" % channel_name)
                else:
                    logger.critical("The app post couldn't be saved into the db, but its corresponding post couldn't be "
                                    "delete from %s. The app may be in an inconsistent state" % channel_name)
            else:
                logger.info("The app post with the id: %s was created" % app_post.id)

    @staticmethod
    def to_dict(post, url):
        return {"id": post.id_str, "text": post.text,
                "url": url + post.author.screen_name + "/status/" + post.id_str}

    @staticmethod
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

    def get_channel_obj(self, channel_name):
        channel_obj = None

        if channel_name.lower() == "twitter":
            channel_obj = self.twitter.get_channel_obj()
        elif channel_name.lower() == "facebook":
            channel_obj = self.facebook.get_channel_obj()
        elif channel_name.lower() == "googleplus":
            channel_obj = self.gplus.get_channel_obj()
        else:
            logger.error("Unknown channel: %s" % channel_name)

        return channel_obj

    def get_author_obj(self, author, channel_name):
        try:
            channel_obj = self.get_channel_obj(channel_name)
            return Author.objects.get(id_in_channel=author["id"], channel=channel_obj.id)
        except Author.DoesNotExist:
            return None

    def register_new_author(self, author, channel_name):
        channel_obj = self.get_channel_obj(channel_name)
        new_author = Author(name=author["name"], screen_name=author["screen_name"], id_in_channel=author["id"],
                            channel=channel_obj, friends=author["friends"], followers=author["followers"],
                            url=author["url"], description=author["description"], language=author["language"],
                            posts_count=author["posts_count"])
        new_author.save(force_insert=True)
        return new_author

    def channel_enabled(self, channel_name):
        if channel_name.lower() == "twitter" and self.twitter:
            return True
        elif channel_name.lower() == "facebook" and self.facebook:
            return True
        elif channel_name.lower() == "googleplus" and self.gplus:
            return True
        else:
            logger.error("Unknown channel: %s" % channel_name)
            return False

    def listen(self, initiative_ids, channel_name):
        channel_name = channel_name.lower()
        channel = Channel.objects.get(name=channel_name)

        self.set_initiatives(initiative_ids, channel_name)
        if channel_name.lower() == "twitter":
            logger.info("Start listening Twitter channel")
            task = self.twitter.listen.delay()
            task_id = task.id
        elif channel_name.lower() == "facebook":
            self.facebook.listen()
            task_id = None
        elif channel_name.lower() == "googleplus":
            self.gplus.listen()
            task_id = None
        else:
            logger.error("Unknown channel: %s" % channel_name)
            return None
        channel.connect(task_id)

    def disconnect(self, channel_name):
        channel_name = channel_name.lower()
        try:
            ch = Channel.objects.get(name=channel_name)
            task_id = ch.pid
            if channel_name.lower() == "twitter":
                self.twitter.hangup()
            elif channel_name.lower() == "facebook":
                self.facebook.hangup()
            elif channel_name.lower() == "googleplus":
                self.gplus.hangup()
            else:
                logger.error("Unknown channel: %s" % channel_name)
                return None
            ch.disconnect()
            return task_id
        except Channel.DoesNotExist:
            logger.error("Cannot disconnect, channel %s does not exists" % channel_name)

    # Check whether the text of the post has the hashtags the identifies the initiative
    def has_initiative_hashtags(self, post, channel_name):
        initiatives = None

        if channel_name.lower() == "twitter":
            initiatives = self.twitter.get_initiatives()
        elif channel_name.lower() == "facebook":
            initiatives = self.facebook.get_initiatives()
        elif channel_name.lower() == "googleplus":
            initiatives = self.gplus.get_initiatives()
        else:
            logger.error("Unknown channel: %s" % channel_name)

        for initiative in initiatives:
            initiative_hashtag = initiative.hashtag
            for post_hashtag in post['hashtags']:
                if post_hashtag == initiative_hashtag.lower().strip():
                    return initiative
        return None

    def process_post(self, post):
        self.post_manager.manage_post(post)


