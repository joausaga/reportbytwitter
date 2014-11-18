from django.conf import settings
from celery import current_app
from celery.contrib.methods import task_method

import abc
import ast
import ConfigParser
import logging
import models
import os
import re
import tweepy


logger = logging.getLogger(__name__)


# Abstract Class. All Social Networks must inherit from it.
class SocialNetwork():
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def listen(self):
        """Listen the channel"""
        raise NotImplementedError

    @abc.abstractmethod
    def send_message(self, message, type_msg, payload, recipient_id):
        """Send message through the channel"""
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

    @staticmethod
    @abc.abstractmethod
    def auth_initiative_writer(initiative_id):
        """Authenticate post writer"""
        raise NotImplementedError

    @abc.abstractmethod
    def set_initiatives(self, initiatives):
        """Set social network initiatives"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_initiatives(self):
        """Get initiatives associated to social network"""
        raise NotImplementedError

    @abc.abstractmethod
    def set_accounts(self, accounts):
        """Set social network accounts"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_accounts(self):
        """Get accounts associated to social network"""
        raise NotImplementedError

    @abc.abstractmethod
    def set_hashtags(self, hashtags):
        """Set social network hashtags"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_url(self):
        """Get social network url"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_channel_obj(self):
        """Get channel ORM model object"""
        raise NotImplementedError

    @abc.abstractmethod
    def hangup(self):
        """Disconnect the streaming"""
        raise NotImplementedError


"""
Twitter
"""


class Twitter(SocialNetwork):
    auth_handler = None
    channel_obj = None
    config = None
    initiatives = None
    accounts = None
    hashtags = None
    middleware = None
    stream = None

    def __init__(self, middleware):
        self.channel_obj = models.Channel.objects.get(name="twitter")
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.join(settings.BASE_DIR, "cparte/config"))
        # Authenticate
        self.auth_handler = tweepy.OAuthHandler(self.config.get('twitter_api', 'consumer_key'),
                                                self.config.get('twitter_api', 'consumer_secret'))
        self.auth_handler.set_access_token(self.config.get('twitter_api', 'token'),
                                           self.config.get('twitter_api', 'token_secret'))
        self.middleware = middleware

    @current_app.task(filter=task_method)
    def listen(self):
        # Initialize listener
        listener = TwitterListener(self.middleware)
        self.stream = tweepy.Stream(self.auth_handler, listener)
        self.stream.filter(follow=self.accounts, track=self.hashtags)

    def send_message(self, message, type_msg, payload, recipient_id):
        auth_writer = self.auth_initiative_writer(payload["initiative_id"])
        if auth_writer:
            api = tweepy.API(auth_handler=auth_writer, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
            try:
                # Public Posts
                if type_msg == "PU":
                    response = api.update_status(status=message)
                    logger.info("The post '%s' has been published through Twitter" % message)
                # Reply
                elif type_msg == "RE":
                    response = api.update_status(status=message, in_reply_to_status_id=recipient_id)
                    logger.info("The post '%s' has been sent to %s through Twitter" % (message, payload['author_username']))
                # Direct message
                else:
                    author_id = payload['author_id']
                    response = api.send_direct_message(user_id=author_id, text=message)
                    logger.info("The message '%s' has been sent directly to %s through Twitter" % (message, author_id))
                return {'delivered': True, 'response': response}
            except tweepy.TweepError as e:
                reason = ast.literal_eval(e.reason)
                logger.error("The post '%s' couldn't be delivered. Reason: %s" % (message, reason[0]['message']))
                return {'delivered': False, 'response': reason}
        else:
            logger.error("The write couldn't be authenticated, the message couldn't be sent.")
            return None

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

    @staticmethod
    def auth_initiative_writer(initiative_id):
        try:
            ini = models.Initiative.objects.get(pk=initiative_id)
            auth_handler = tweepy.OAuthHandler(ini.account.consumer_key, ini.account.consumer_secret)
            auth_handler.set_access_token(ini.account.token, ini.account.token_secret)
            return auth_handler
        except models.Initiative.DoesNotExist:
            logger.error("Couldn't find the initiative. The initiative writer couldn't be authenticated so the message "
                         "won't be delivered")
            return None

    def set_initiatives(self, initiatives):
        self.initiatives = initiatives

    def get_initiatives(self):
        return self.initiatives

    def set_accounts(self, accounts):
        self.accounts = accounts

    def get_accounts(self):
        return self.accounts

    def set_hashtags(self, hashtags):
        self.hashtags = hashtags

    def get_url(self):
        return self.channel_obj.url

    def get_channel_obj(self):
        return self.channel_obj

    def hangup(self):
        if self.stream:
            self.stream.disconnect()


class TwitterListener(tweepy.StreamListener):
    middleware = None
    url = "https://twitter.com/"

    def __init__(self, middleware):
        super(TwitterListener, self).__init__()
        self.middleware = middleware

    def on_status(self, status):
        try:
            if status.retweeted_status:
                retweet = self.get_tweet_dict(status.retweeted_status)
            else:
                retweet = None
        except AttributeError:
            retweet = None
        status_dict = self.get_tweet_dict(status)
        status_dict["org_post"] = retweet
        self.middleware.process_post(status_dict)
        return True

    def get_tweet_dict(self, status):
        author = status.author
        # Extract tweet source
        source = re.sub("(<[a|A][^>]*>|</[a|A]>)", "", status.source)
        # Source is equal to Twitter for Websites if the tweet was posted through twitter social sharing button
        if source == "Twitter for Websites":
            through_sharing_button = True
        else:
            through_sharing_button = False

        return {"id": status.id_str, "text": status.text, "parent_id": status.in_reply_to_status_id_str,
                "datetime": status.created_at, "url": self.build_url_post(status), "votes": 0,
                "re_posts": status.retweet_count, "bookmarks": status.favorite_count,
                "hashtags": self.build_hashtags_array(status), "source": source,
                "sharing_post": through_sharing_button,
                "author": {"id": author.id_str, "name": author.name, "screen_name": author.screen_name,
                           "print_name": "@" + author.screen_name, "url": self.url + author.screen_name,
                           "description": author.description, "language": author.lang,
                           "posts_count": author.statuses_count, "friends": author.friends_count,
                           "followers": author.followers_count, "groups": author.listed_count},
                "channel": "twitter"
                }

    def build_url_post(self, status):
        return self.url + status.author.screen_name + "/status/" + status.id_str

    def build_hashtags_array(self, status):
        hashtags = []
        for hashtag in status.entities['hashtags']:
            hashtags.append(hashtag['text'].lower().strip())
        return hashtags

    def on_error(self, error_code):
        url_error_explanations = "https://dev.twitter.com/streaming/overview/connecting"
        error_title = ""

        if error_code == 401:
            error_title = "Unauthorized"
        elif error_code == 403:
            error_title = "Forbidden"
        elif error_code == 404:
            error_title = "Unknown"
        elif error_code == 406:
            error_title = "Not Acceptable"
        elif error_code == 413:
            error_title = "Too Long"
        elif error_code == 416:
            error_title = "Range Unacceptable"
        elif error_code == 420:
            error_title = "Rate Limited"
        elif error_code == 503:
            error_title = "Service Unavailable"

        logger.critical("Error %s (%s) in the firehose. For further explanation check: %s" %
                        (str(error_code), error_title, url_error_explanations))
        return True  # To continue listening

    def on_timeout(self):
        logger.warning("Got timeout from the firehose")
        return True  # To continue listening

    def on_disconnect(self, notice):
        notice_name = ""
        notice_description = ""

        try:
            if notice["code"] == 1:
                notice_name = "Shutdown"
                notice_description = "The feed was shutdown (possibly a machine restart)"
            elif notice["code"] == 2:
                notice_name = "Duplicate stream"
                notice_description = "The same endpoint was connected too many times."
            elif notice["code"] == 4:
                notice_name = "Stall"
                notice_description = "The client was reading too slowly and was disconnected by the server."
            elif notice["code"] == 5:
                notice_name = "Normal"
                notice_description = "The client appeared to have initiated a disconnect."
            elif notice["code"] == 7:
                notice_name = "Admin logout"
                notice_description = "The same credentials were used to connect a new stream and the oldest was " \
                                     "disconnected."
            elif notice["code"] == 9:
                notice_name = "Max message limit"
                notice_description = "The stream connected with a negative count parameter and was disconnected " \
                                     "after all backfill was delivered."
            elif notice["code"] == 10:
                notice_name = "Stream exception"
                notice_description = "An internal issue disconnected the stream."
            elif notice["code"] == 11:
                notice_name = "Broker stall"
                notice_description = "An internal issue disconnected the stream."
            elif notice["code"] == 12:
                notice_name = "Shed load"
                notice_description = "The host the stream was connected to became overloaded and streams were " \
                                     "disconnected to balance load. Reconnect as usual."

            logger.critical("The stream was disconnected. Message %s. Code: %s. Reason: %s. Description: %s" %
                            (notice_name, notice["code"], notice["reason"], notice_description))
        except Exception as e:
            logger.critical("Error in the method on_disconnect. Message: %s" % e)
        return True  # To continue listening


"""
Facebook
"""


class Facebook(SocialNetwork):
    auth_handler = None
    channel_obj = None
    config = None
    initiatives = None
    accounts = None
    hashtags = None
    middleware = None
    stream = None

    def __init__(self, middleware):
        self.middleware = middleware
        raise NotImplementedError

    def listen(self):
        raise NotImplementedError

    def send_message(self, message, type_msg, payload, recipient_id):
        raise NotImplementedError

    def get_post(self, id_post):
        raise NotImplementedError

    def delete_post(self, post):
        raise NotImplementedError

    def get_info_user(self, id_user):
        raise NotImplementedError

    @staticmethod
    def auth_initiative_writer(initiative_id):
        raise NotImplementedError

    def set_initiatives(self, initiatives):
        raise NotImplementedError

    def get_initiatives(self):
        raise NotImplementedError

    def set_accounts(self, accounts):
        raise NotImplementedError

    def get_accounts(self):
        raise NotImplementedError

    def set_hashtags(self, hashtags):
        raise NotImplementedError

    def get_url(self):
        raise NotImplementedError

    def get_channel_obj(self):
        raise NotImplementedError

    def hangup(self):
        raise NotImplementedError


"""
Google Plus
"""


class GooglePlus(SocialNetwork):
    auth_handler = None
    channel_obj = None
    config = None
    initiatives = None
    accounts = None
    hashtags = None
    middleware = None
    stream = None

    def __init__(self, middleware):
        self.middleware = middleware
        raise NotImplementedError

    def listen(self):
        raise NotImplementedError

    def send_message(self, message, type_msg, payload, recipient_id):
        raise NotImplementedError

    def get_post(self, id_post):
        raise NotImplementedError

    def delete_post(self, post):
        raise NotImplementedError

    def get_info_user(self, id_user):
        raise NotImplementedError

    @staticmethod
    def auth_initiative_writer(initiative_id):
        raise NotImplementedError

    def set_initiatives(self, initiatives):
        raise NotImplementedError

    def get_initiatives(self):
        raise NotImplementedError

    def set_accounts(self, accounts):
        raise NotImplementedError

    def get_accounts(self):
        raise NotImplementedError

    def set_hashtags(self, hashtags):
        raise NotImplementedError

    def get_url(self):
        raise NotImplementedError

    def get_channel_obj(self):
        raise NotImplementedError

    def hangup(self):
        raise NotImplementedError