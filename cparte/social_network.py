from django.conf import settings
from celery import current_app
from celery.contrib.methods import task_method

import abc
import ast
import channel_middleware
import ConfigParser
import logging
import models
import os
import re
import signal
import tweepy


logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Abstract Class. All Social Networks must inherit from it.
# ----------------------------------------------------------
class SocialNetwork():
    __metaclass__ = abc.ABCMeta

    @staticmethod
    @abc.abstractmethod
    def authenticate():
        """Authenticate to the channel"""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def listen(accounts, hashtags):
        """Listen the channel"""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def send_message(message, type_msg, payload, recipient_id, channel_url):
        """Send message through the channel"""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def get_post(id_post):
        """Get a post previously published in the channel and identified by id_post"""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def delete_post(id_post):
        """Delete the post identified by id_post"""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def get_info_user(id_user):
        """Get information about a particular user"""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def auth_initiative_writer(initiative_id):
        """Authenticate post writer"""
        raise NotImplementedError

    @staticmethod
    def to_dict(post, url):
        """Get a dictionary with the information of the post"""
        raise NotImplementedError

#---------------------------------
# Twitter Client
#---------------------------------


class Twitter(SocialNetwork):
    initiatives = None
    accounts = None
    hashtags = None

    @staticmethod
    def authenticate():
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(settings.BASE_DIR, "cparte/config"))
        # Authenticate
        auth_handler = tweepy.OAuthHandler(config.get('twitter_api', 'consumer_key'),
                                           config.get('twitter_api', 'consumer_secret'))
        auth_handler.set_access_token(config.get('twitter_api', 'token'),
                                      config.get('twitter_api', 'token_secret'))
        return auth_handler

    @current_app.task(filter=task_method)
    def listen(accounts, hashtags):
        auth_handler = Twitter.authenticate()
        listener = TwitterListener()
        #stream = tweepy.Stream(auth_handler, listener)
        stream = TwitterClientWrapper(auth_handler, listener)
        stream.filter(follow=accounts, track=hashtags, stall_warnings=True)

    @staticmethod
    def send_message(message, type_msg, payload, recipient_id, channel_url):
        auth_writer = Twitter.auth_initiative_writer(payload["initiative_id"])
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
                return {'delivered': True, 'response': Twitter.to_dict(response, channel_url)}
            except tweepy.TweepError as e:
                reason = ast.literal_eval(e.reason)
                logger.error("The post '%s' couldn't be delivered. Reason: %s" % (message, reason[0]['message']))
                return {'delivered': False, 'response': reason}
        else:
            logger.error("The write couldn't be authenticated, the message couldn't be sent.")
            return None

    @staticmethod
    def get_post(id_post):
        auth_handler = Twitter.authenticate()
        api = tweepy.API(auth_handler=auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        return api.get_status(id_post)

    @staticmethod
    def delete_post(post):
        auth_handler = Twitter.authenticate()
        api = tweepy.API(auth_handler=auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        try:
            return api.destroy_status(post["id"])
        except tweepy.TweepError, e:
            logger.error("The post %s couldn't be destroyed. %s" % (post["id"], e.reason))

    @staticmethod
    def get_info_user(id_user):
        auth_handler = Twitter.authenticate()
        api = tweepy.API(auth_handler=auth_handler, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
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

    @staticmethod
    def to_dict(post, url):
        return {"id": post.id_str, "text": post.text, "url": url + post.author.screen_name + "/status/" + post.id_str}


# Tweepy Stream Class Wrapper
# Created to define a handler to manage the SIGTERM signal sent by
# celery task revoke
class TwitterClientWrapper(tweepy.Stream):

    def __init__(self, auth_handler, listener):
        super(TwitterClientWrapper, self).__init__(auth_handler, listener)
        signal.signal(signal.SIGTERM, self.signal_term_handler)

    def signal_term_handler(self, signal, frame):
        logger.info("Disconnecting twitter streaming...")
        self.disconnect()
        self._thread.join()  # Not sure why this works (self._thread shouldn't exist). Magic!


class TwitterListener(tweepy.StreamListener):
    url = "https://twitter.com/"

    def __init__(self):
        super(TwitterListener, self).__init__()

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
        channel_middleware.process_post(status_dict, "twitter")
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

    def on_warning(self, notice):
        logger.warning("Got the following warning message: %s" % notice["message"])

#---------------------------------
# Facebook Client
#---------------------------------


class Facebook(SocialNetwork):

    @staticmethod
    def listen(accounts, hashtags):
        raise NotImplementedError

    @staticmethod
    def send_message(message, type_msg, payload, recipient_id, channel_url):
        raise NotImplementedError

    @staticmethod
    def get_post(id_post):
        raise NotImplementedError

    @staticmethod
    def delete_post(post):
        raise NotImplementedError

    @staticmethod
    def get_info_user(id_user):
        raise NotImplementedError

    @staticmethod
    def auth_initiative_writer(initiative_id):
        raise NotImplementedError

    @staticmethod
    def to_dict(post, url):
        raise NotImplementedError

#---------------------------------
# Google Plus Client
#---------------------------------


class GooglePlus(SocialNetwork):

    @staticmethod
    def listen(accounts, hashtags):
        raise NotImplementedError

    @staticmethod
    def send_message(message, type_msg, payload, recipient_id, channel_url):
        raise NotImplementedError

    @staticmethod
    def get_post(id_post):
        raise NotImplementedError

    @staticmethod
    def delete_post(post):
        raise NotImplementedError

    @staticmethod
    def get_info_user(id_user):
        raise NotImplementedError

    @staticmethod
    def auth_initiative_writer(initiative_id):
        raise NotImplementedError

    @staticmethod
    def to_dict(post, url):
        raise NotImplementedError