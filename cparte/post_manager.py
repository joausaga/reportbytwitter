from apiclient.discovery import build
from django.utils import timezone
from django.conf import settings

import ConfigParser
import logging
import models
import re
import os
import time
import traceback

logger = logging.getLogger(__name__)


# The class that does all the magic. All the business logic is encapsulated here
class PostManager():
    ch_middleware = None
    settings = {}
    url_shortener = None
    NO_LIMIT_ANSWERS = -1
    NOTIFICATION_MESSAGE = "NT"
    ENGAGE_MESSAGE = "EN"
    STRUCTURED_ANSWER = "ST"
    FREE_ANSWER = "FR"

    def __init__(self, middleware):
        self.ch_middleware = middleware
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(settings.BASE_DIR, "cparte/config"))
        self._set_settings()
        if self.settings['short_url']:
            self.url_shortener = build(serviceName=self.settings['urlshortener_api_name'],
                                       version=self.settings['urlshortener_api_version'],
                                       developerKey=config.get('url_shortener', 'key'))
        else:
            self.url_shortener = None

    def _set_settings(self):
        try:
            self.settings['limit_wrong_inputs'] = models.Setting.objects.get(name="limit_wrong_inputs").get_casted_value()
            self.settings['limit_wrong_requests'] = models.Setting.objects.get(name="limit_wrong_requests").get_casted_value()
            self.settings['datetime_format'] = models.Setting.objects.get(name="datetime_format").value
            self.settings['urlshortener_api_name'] = models.Setting.objects.get(name="gurlshortener_api_name").value
            self.settings['urlshortener_api_version'] = models.Setting.objects.get(name="gurlshortener_api_version").value
            self.settings['short_url'] = models.Setting.objects.get(name="short_url").get_casted_value()
        except models.Setting.DoesNotExist as e:
            e_msg = "Unknown setting %s, the post manager cannot be started" % e
            logger.critical(e_msg)
            raise Exception(e_msg)

    def manage_post(self, post):
        try:
            author_obj = self.ch_middleware.get_author_obj(post["author"], post["channel"])
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
            initiative = self.ch_middleware.has_initiative_hashtags(post, post["channel"])
            within_initiative = True if initiative else False
            challenge = self._get_challenge_info(post, initiative) if within_initiative else None
            if author_id in self.ch_middleware.get_account_ids(post["channel"]):
                if initiative and challenge and author_id == initiative.account.id_in_channel:
                    #Save the message if it was already saved
                    self._save_app_post(post, initiative, challenge)
                    logger.info("App post placed from channel's client was saved")
                    return None
            else:
                if within_initiative and challenge:
                    if post["sharing_post"]:
                        # Save sharing post if it wasn't already saved
                        self._save_sharing_post(post, author_obj, challenge)
                        logger.info("The social sharing post '%s' was saved" % post["text"])
                        return None  # We're not interested in processing posts placed through the social sharing buttons
                    else:
                        # Check if the post is a re-post and if the original post's text correspond to the
                        # initiative's social sharing button message
                        if post["org_post"]:
                            if self._contains_social_sharing_msg(post["org_post"], initiative):
                                logger.info("A social sharing post was re-posted!")
                                return None  # So far, we're not interested in processing re-posted sharing posts
                        else:
                            if self._contains_social_sharing_msg(post, initiative):
                                # We want only the "new text" contained in the post, so we can remove the part
                                # corresponding to the predefined social sharing message
                                attached_txt = self._extract_attached_txt(initiative.social_sharing_message, post["text"])
                                len_attached_txt = len(attached_txt)
                                if len_attached_txt > 0:
                                    post["text"] = attached_txt
                                else:
                                    logger.info("There is none text attached to the social sharing msg")
                                    return None
        else:
            try:
                # Searching for the post in the app db
                app_parent_post = models.AppPost.objects.get(id_in_channel=parent_post_id)
                # Check whether the category of the root post is engagement (EN).
                # Posts in this category are intended to engage the public into the initiative challenges
                within_initiative = app_parent_post.category == self.ENGAGE_MESSAGE and \
                                    app_parent_post.app_parent_post is None
                challenge = app_parent_post.challenge if within_initiative else None
            except models.AppPost.DoesNotExist:
                # Check if the post is a reply to social sharing post
                try:
                    social_sharing_post = models.SharePost.objects.get(id_in_channel=parent_post_id)
                    within_initiative = True
                    challenge = social_sharing_post.challenge
                except models.SharePost.DoesNotExist:
                    return None  # We're not interested in processing replies that were not posted to the app posts

        if within_initiative and challenge:
            if author_obj is None:
                author_obj = self.ch_middleware.register_new_author(post["author"], post["channel"])
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

    # Return information about the challenge
    def _get_challenge_info(self, post, initiative):
        campaigns = initiative.campaign_set.all()
        for campaign in campaigns:
            challenges = campaign.challenge_set.all()
            for challenge in challenges:
                challenge_hashtag = challenge.hashtag
                for post_hashtag in post['hashtags']:
                    if post_hashtag == challenge_hashtag.lower().strip():
                        return challenge
        return None

    def _get_parent_post_message(self, text_post, campaign):
        messages = list(campaign.messages.all())
        if campaign.extrainfo is not None:
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
            self._preserve_author_temporal_posts(author, post["channel"])
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
            old_post = models.ContributionPost.objects.get(challenge=challenge, author=author_obj.id, status="PE")
            # Temporal Post
            new_post = models.ContributionPost.objects.filter(challenge=challenge, author=author_obj.id, status="TE").\
                       order_by('-datetime').first()
            new_post.preserve()  # Preserve the newest (temporal)
            old_post.discard()  # Discard the oldest (permanent)
            self._discard_temporal_post(author_obj, challenge)  # Discard the remaining temporal posts related to 'challenge'
            message = campaign.messages.get(category="thanks_change")
            self._send_reply(post, campaign.initiative, challenge, message, new_post)
            author_obj.reset_mistake_flags()
            return message
        except (models.ContributionPost.DoesNotExist, models.ContributionPost.MultipleObjectsReturned) as e:
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
                    if challenge.accept_changes:
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
                        # Send a message saying that he/she has already answered the challenge
                        message = campaign.messages.get(category="already_answered_unchangeable_challenge")
                        self._send_reply(post, campaign.initiative, challenge, message)
                        logger.info("The participant %s has answered the unchangeable challenge %s" % (author["name"],
                                                                                                       challenge.name))
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
            return models.ContributionPost.objects.filter(challenge=challenge, author=author_obj.id, status='PE').\
                   order_by('-datetime')
        except models.ContributionPost.DoesNotExist:
            return None

    def _save_post(self, post, author_obj, curated_input, challenge, temporal):
        channel_obj = self.ch_middleware.get_channel_obj(post["channel"])
        campaign = challenge.campaign
        initiative = campaign.initiative
        if temporal:
            status = 'TE'
        else:
            status = 'PE'
        post_to_save = models.ContributionPost(id_in_channel=post["id"],
                                               datetime=timezone.make_aware(post["datetime"], timezone.get_default_timezone()),
                                               contribution=curated_input, full_text=post["text"], url=post["url"],
                                               author=author_obj, in_reply_to=post["parent_id"], initiative=initiative,
                                               campaign=campaign, challenge=challenge, channel=channel_obj, votes=post["votes"],
                                               re_posts=post["re_posts"], bookmarks=post["bookmarks"], status=status,
                                               source=post["source"])
        post_to_save.save(force_insert=True)
        if not temporal:
            self._discard_temporal_post(author_obj, challenge)
        return post_to_save

    # Discard any temporal post existing within 'challenge' and posted by 'author'
    def _discard_temporal_post(self, author_obj, challenge):
        try:
            temp_posts = models.ContributionPost.objects.filter(challenge=challenge, author=author_obj.id, status='TE')
            for post in temp_posts:
                post.discard()
            return True
        except models.ContributionPost.DoesNotExist:
            return False

    # Preserve author's posts that were saved as temporal because of the lack of his/her extra info
    def _preserve_author_temporal_posts(self, author, channel):
        author_obj = self.ch_middleware.get_author_obj(author, channel)
        try:
            temp_posts = models.ContributionPost.objects.filter(author=author_obj.id, status='TE')
            for post in temp_posts:
                try:
                    app_post = models.AppPost.objects.get(contribution_parent_post=post.id, answered=False)
                    message_sent = self._get_parent_post_message(app_post.text, app_post.campaign)
                    if message_sent.category == "request_author_extrainfo":
                        campaign = app_post.campaign
                        challenge = app_post.challenge
                        post.preserve()
                        app_post.do_answer()
                        message = campaign.messages.get(category="thanks_contribution")
                        post_dict = {"id": post.id_in_channel, "parent_id": post.in_reply_to, "author": author}
                        self._send_reply(post_dict, campaign.initiative, challenge, message)
                except models.AppPost.DoesNotExist, models.AppPost.MultipleObjectsReturned:
                    pass
            return True
        except models.ContributionPost.DoesNotExist:
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
        elif message.category == "already_answered_unchangeable_challenge":
            msg = message.body % (author_username, current_datetime)
            type_msg = "NT"
        if msg is not None:
            payload = {'parent_post_id': post["parent_id"], 'type_msg': type_msg,
                       'post_id': post["id"], 'initiative_id': initiative.id, 'author_username': author_username,
                       'author_id': author_id, 'campaign_id': challenge.campaign.id, 'challenge_id': challenge.id,
                       'initiative_short_url': short_url}
            #payload_json = json.dumps(payload)
            self.ch_middleware.send_message(message=msg, type_msg="RE", recipient_id=post["id"], payload=payload,
                                            channel_name=post["channel"])

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

    # Check whether the post contains at least an 'x' percentage of the social sharing message words.
    def _contains_social_sharing_msg(self, post, initiative):
        # It determines the minimum percentage of words that the 2 texts must share to be considered similar
        similarity_per = 60

        if initiative.social_sharing_message:
            similarity_factor = self._calculate_text_similarity(initiative.social_sharing_message, post["text"])
            if similarity_factor >= similarity_per:
                return True
            else:
                return False
        else:
            return False

    # Take two texts and calculate their similarity based on the percentage of words they share
    def _calculate_text_similarity(self, text1, text2):
        similarity_counter = 0
        len_text1 = len(text1.split())
        text1 = self._to_unicode(text1).lower()
        text2 = self._to_unicode(text2).lower()

        for word_post in text2.split():
            for word_def in text1.split():
                if word_post == word_def:
                    similarity_counter += 1
                    break

        return (similarity_counter * 100) / len_text1

    # Extract the attached text from the original post
    def _extract_attached_txt(self, txt_org_post, txt_repost):
        new_txt = ""

        for word_repost in txt_repost.split():
            found = False
            for word_org in txt_org_post.split():
                if self._to_unicode(word_org) == self._to_unicode(word_repost):
                    found = True
                    break
            if not found:
                new_txt += word_repost + " "
        new_txt = new_txt.strip()  # Remove trailing space

        return new_txt

    def _save_sharing_post(self, post, author_obj, challenge):
        if not models.SharePost.objects.filter(id_in_channel=post["id"]).exists():
            if author_obj is None:
                author_obj = self.ch_middleware.register_new_author(post["author"], post["channel"])
            channel_obj = self.ch_middleware.get_channel_obj(post["channel"])
            campaign = challenge.campaign
            initiative = campaign.initiative
            similarity = self._calculate_text_similarity(initiative.social_sharing_message, post["text"])
            post_to_save = models.SharePost(id_in_channel=post["id"],
                                            datetime=timezone.make_aware(post["datetime"], timezone.get_default_timezone()),
                                            text=post["text"], url=post["url"],
                                            author=author_obj, initiative=initiative,
                                            campaign=campaign, challenge=challenge, channel=channel_obj, votes=post["votes"],
                                            re_posts=post["re_posts"], bookmarks=post["bookmarks"], similarity=similarity)
            post_to_save.save(force_insert=True)

    # Save app posts placed directly through the channel clients
    def _save_app_post(self, post, initiative, challenge):
        if not models.AppPost.objects.filter(id_in_channel=post["id"]).exists():
            campaign = challenge.campaign
            channel_obj = self.ch_middleware.get_channel_obj(post["channel"])
            app_post = models.AppPost(id_in_channel=post["id"], datetime=timezone.make_aware(post["datetime"], timezone.get_default_timezone()),
                                      text=post["text"], url=post["url"], app_parent_post=None, initiative=initiative,
                                      campaign=campaign, contribution_parent_post=None, challenge=challenge, channel=channel_obj,
                                      votes=post["votes"], re_posts=post["re_posts"], bookmarks=post["bookmarks"],
                                      delivered=True, category="EN", payload=None, recipient_id=None, answered=False)
            app_post.save(force_insert=True)
