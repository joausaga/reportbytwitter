from django.test import TestCase
from cparte.models import PostManager, Twitter, Setting
import ConfigParser
import re

import tweepy


class TwitterTestCase(TestCase):
    fixtures = ['cparte.json']
    url = "https://twitter.com/"
    config = ConfigParser.ConfigParser()
    config.read('cparte/config')

    def setUp(self):
        auth = tweepy.OAuthHandler(self.config.get('twitter_api','consumer_key'), self.config.get('twitter_api','consumer_secret'))
        auth.set_access_token(self.config.get('twitter_api','token'), self.config.get('twitter_api','token_secret'))
        api = tweepy.API(auth)
        api.retry_count = 2
        api.retry_delay = 5

        self.testing_posts = self.get_array_testing_tweets()
        tweet_ids = self.get_id_testing_tweets()
        statuses = api.statuses_lookup(tweet_ids)
        self.save_testing_statuses(statuses)

        twitter = Twitter()
        twitter.set_initiatives([1])
        twitter.set_accounts([1])
        self.manager = PostManager(twitter)
        self.limit_incorrect_inputs = Setting.objects.get(name="limit_wrong_inputs").get_casted_value()
        self.limit_incorrect_requests = Setting.objects.get(name="limit_wrong_requests").get_casted_value()

    # Add here id of testing tweets
    def get_array_testing_tweets(self):
        return [{'id': "513014488925077505", 'type': 'correct_post_new_user_new_challenge', 'status': ''},
                {'id': "513014347379908608", 'type': 'incorrect_post_new_user_new_challenge', 'status': ''},
                {'id': "509884504974950401", 'type': 'correct_post_existing_user_new_challenge', 'status': ''},
                {'id': "513022343044542464", 'type': 'incorrect_post_existing_user_new_challenge', 'status': ''},
                {'id': "509053831166980096", 'type': 'correct_post_existing_user_answered_challenge', 'status': ''},
                {'id': "513020781341573120", 'type': 'incorrect_post_existing_user_answered_challenge', 'status': ''}]

    def get_id_testing_tweets(self):
        tweet_ids = []
        for tweet in self.testing_posts:
            tweet_ids.append(tweet['id'])
        return tweet_ids

    def save_testing_statuses(self, statuses):
        for status in statuses:
            for tweet in self.testing_posts:
                if tweet['id'] == status.id_str:
                    tweet['status'] = status

    def to_dict(self, status):
        try:
            if status.retweeted_status:
                retweet = self.get_tweet_dict(status.retweeted_status)
            else:
                retweet = None
        except AttributeError:
            retweet = None
        status_dict = self.get_tweet_dict(status)
        status_dict["org_post"] = retweet

        return status_dict

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
                           "followers": author.followers_count, "groups": author.listed_count}
                }

    def build_url_post(self, status):
        return self.url + status.author.screen_name + "/status/" + status.id_str

    def build_hashtags_array(self, status):
        hashtags = []
        for hashtag in status.entities['hashtags']:
            hashtags.append(hashtag['text'].lower().strip())
        return hashtags

class TestAppBehavior(TwitterTestCase):

    def test_manage_post_new_user_correct_answer_to_new_challenge(self):
        # Input: post from a new author and containing a correct answer
        # Output: a message asking for extra info
        correct_post_new_user_new_challenge = None
        for testing_post in self.testing_posts:
            if testing_post['type'] == "correct_post_new_user_new_challenge":
                correct_post_new_user_new_challenge = self.to_dict(testing_post['status'])
        output = self.manager.manage_post(correct_post_new_user_new_challenge)
        self.assertNotEqual(output.category, None)
        self.assertEqual(output.category, "request_author_extrainfo")

    def test_manage_post_new_user_incorrect_answer_to_new_challenge(self):
        # Input: post from a new author and containing an unexpected answer
        # Output: a message notifying the author that his/her contribution is in an incorrect format
        incorrect_post_new_user_new_challenge = None
        for testing_post in self.testing_posts:
            if testing_post['type'] == "incorrect_post_new_user_new_challenge":
                incorrect_post_new_user_new_challenge = self.to_dict(testing_post['status'])
        output = self.manager.manage_post(incorrect_post_new_user_new_challenge)
        self.assertNotEqual(output.category, None)
        self.assertEqual(output.category, "incorrect_answer")

    def test_manage_post_existing_user_correct_answer_to_new_challenge(self):
        # Input: post from an existing author and containing an expected answer
        # Output: a message thanking the author for his/her contribution
        correct_post_existing_user_new_challenge = None
        for testing_post in self.testing_posts:
            if testing_post['type'] == "correct_post_existing_user_new_challenge":
                correct_post_existing_user_new_challenge = self.to_dict(testing_post['status'])
        output = self.manager.manage_post(correct_post_existing_user_new_challenge)
        self.assertNotEqual(output.category, None)
        self.assertEqual(output.category, "thanks_contribution")

    def test_manage_post_existing_user_correct_answer_to_previously_answered_challenge(self):
        # Input: post from an existing author and containing an expected answer to a previously answered challenge
        # Output: a message asking the author to change his/her previous contribution
        correct_post_existing_user_answered_challenge = None
        for testing_post in self.testing_posts:
            if testing_post['type'] == "correct_post_existing_user_answered_challenge":
                correct_post_existing_user_answered_challenge = self.to_dict(testing_post['status'])
        output = self.manager.manage_post(correct_post_existing_user_answered_challenge)
        self.assertNotEqual(output.category, None)
        self.assertEqual(output.category, "ask_change_contribution")

    def test_manage_post_existing_user_incorrect_answer_to_new_challenge(self):
        # Input: post from an existing author and containing an unexpected answer
        # Output: a message notifying the author that his/her contribution is in an incorrect format
        incorrect_post_existing_user_new_challenge = None
        for testing_post in self.testing_posts:
            if testing_post['type'] == "incorrect_post_existing_user_new_challenge":
                incorrect_post_existing_user_new_challenge = self.to_dict(testing_post['status'])
        output = self.manager.manage_post(incorrect_post_existing_user_new_challenge)
        self.assertNotEqual(output.category, None)
        self.assertEqual(output.category, "incorrect_answer")

    def test_manage_post_existing_user_incorrect_answer_to_previously_answered_challenge(self):
        # Input: post from an existing author and containing an expected answer
        # Output: a message notifying the author that his/her contribution is in an incorrect format
        incorrect_post_existing_user_answered_challenge = None
        for testing_post in self.testing_posts:
            if testing_post['type'] == "incorrect_post_existing_user_answered_challenge":
                incorrect_post_existing_user_answered_challenge = self.to_dict(testing_post['status'])
        output = self.manager.manage_post(incorrect_post_existing_user_answered_challenge)
        self.assertNotEqual(output.category, None)
        self.assertEqual(output.category, "incorrect_answer")