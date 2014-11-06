from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from django.contrib import messages
from django import forms
from django.forms.models import BaseInlineFormSet
from cparte.models import Initiative, Campaign, Challenge, Channel, Setting, ExtraInfo, Message, AppPost, Twitter, \
                          ContributionPost, Account, MetaChannel, SharePost

import logging
import json
import pickle
import gettext

MESSAGE_TAGS = {
    messages.SUCCESS: 'alert-success success',
    messages.WARNING: 'alert-warning warning',
    messages.ERROR: 'alert-danger error'
}

logger = logging.getLogger(__name__)

_ = gettext.gettext


class ChallengeFormSet(BaseInlineFormSet):

    def clean(self):
        super(ChallengeFormSet, self).clean()
        msg_ids = self.data.getlist('messages')  # Get ids of current choosen messages
        self._validate_unchangeable_challenges(msg_ids)
        self._validate_incorrect_contribution_msg(msg_ids)
        self._validate_limit_contributions(msg_ids)
        self._validate_changeable_challenges(msg_ids)
        self._validate_structured_challenges()

    # Check if a message to reply in case an unchangeable challenge is answered more than once was included into the
    # campaign's message list
    def _validate_unchangeable_challenges(self, msg_ids):
        exists_unchangeable_challenge = False
        cleaned_data = None

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cleaned_data = form.cleaned_data
            accept_changes = cleaned_data.get("accept_changes")
            limit_answers = cleaned_data.get("answers_from_same_author")
            if not accept_changes and accept_changes is not None and limit_answers == 1:
                exists_unchangeable_challenge = True
                break
        if exists_unchangeable_challenge:
            exists_unchangeable_challenge_msg = False
            messages = Message.objects.filter(pk__in=msg_ids)
            for message in messages:
                if message.category == "already_answered_unchangeable_challenge":
                    exists_unchangeable_challenge_msg = True
                    break
            if not exists_unchangeable_challenge_msg:
                msg = "Please include in the list of chosen messages a message to reply participants that try to change " \
                      "their answers to the following challenge."
                raise forms.ValidationError(_(msg))
            else:
                return cleaned_data

    # Check if a message to reply in case of an incorrect answer was included into the campaign's message list
    def _validate_incorrect_contribution_msg(self, msg_ids):
        exists_structured_challenge = False
        cleaned_data = None

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cleaned_data = form.cleaned_data
            style_challenge = cleaned_data.get("style_answer")
            if style_challenge == "ST":  # Structured
                exists_structured_challenge = True
                break
        if exists_structured_challenge:
            exists_incorrect_format_msg = False
            exists_banned_msg = False
            messages = Message.objects.filter(pk__in=msg_ids)
            for message in messages:
                if message.category == "incorrect_answer":
                    exists_incorrect_format_msg = True
                if message.category == "author_banned":
                    exists_banned_msg = True
            if not exists_incorrect_format_msg:
                msg = "Please include into the list of chosen messages a message to notify participants that their " \
                      "answers do not have the required format."
                raise forms.ValidationError(_(msg))
            elif not exists_banned_msg:
                msg = "Please include into the list of chosen messages a message to notify participants that were " \
                      "banned because they have passed the limit of incorrect answers."
                raise forms.ValidationError(_(msg))
            else:
                return cleaned_data

    # Check if a message to notify participants that their number of contributions has reached the limit was included
    # into the campaign's message list
    def _validate_limit_contributions(self, msg_ids):
        exists_limited_answers_challenge = False
        cleaned_data = None

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cleaned_data = form.cleaned_data
            limit_answers = cleaned_data.get("answers_from_same_author")
            accept_changes = cleaned_data.get("accept_changes")
            if limit_answers > 1 or (limit_answers == 1 and (not accept_changes and accept_changes is not None)):
                exists_limited_answers_challenge = True
                break
        if exists_limited_answers_challenge:
            exists_limited_answers_notification_msg = False
            messages = Message.objects.filter(pk__in=msg_ids)
            for message in messages:
                if message.category == "limit_answers_reached":
                    exists_limited_answers_notification_msg = True
                    break
            if not exists_limited_answers_notification_msg:
                msg = "Please include into the list of chosen messages a message to notify participants that they " \
                      "have reached the limit of contributions."
                raise forms.ValidationError(_(msg))
            else:
                return cleaned_data

    # Check if messages to manage changes in contributions were include into the campaign's message list
    def _validate_changeable_challenges(self, msg_ids):
        exists_changeable_challenges = False
        cleaned_data = None

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cleaned_data = form.cleaned_data
            accept_changes = cleaned_data.get("accept_changes")
            if accept_changes and accept_changes is not None:
                exists_changeable_challenges = True
                break
        if exists_changeable_challenges:
            exists_ask_change_contribution_msg = False
            exists_thanking_change_msg = False
            exists_not_understandable_change_msg = False
            messages = Message.objects.filter(pk__in=msg_ids)
            for message in messages:
                if message.category == "ask_change_contribution":
                    exists_ask_change_contribution_msg = True
                if message.category == "thanks_change":
                    exists_thanking_change_msg = True
                if message.category == "not_understandable_change_contribution_reply":
                    exists_not_understandable_change_msg = True
            if not exists_ask_change_contribution_msg:
                msg = "Please include into the list of chosen messages a message to ask a participant whether he/she " \
                      "wants to change his/her contribution."
                raise forms.ValidationError(_(msg))
            elif not exists_thanking_change_msg:
                msg = "Please include into the list of chosen messages a message to thank participants for their change."
                raise forms.ValidationError(_(msg))
            elif not exists_not_understandable_change_msg:
                msg = "Please include into the list of chosen messages a message to notify a participant that his/her " \
                      "answers to the request about changing a previous contribution was not understandable."
                raise forms.ValidationError(_(msg))
            else:
                return cleaned_data

    # Check if the structured challenges have defined a format for their answers
    def _validate_structured_challenges(self):
        cleaned_data = None

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cleaned_data = form.cleaned_data
            style_answer = cleaned_data.get("style_answer")
            format_answer = cleaned_data.get("format_answer")
            if style_answer == "ST" and format_answer == "":
                msg = "Please define the expected format of the answers for this challenge."
                raise forms.ValidationError(_(msg))
        return cleaned_data


class ChallengeInline(admin.StackedInline):
    model = Challenge
    extra = 0
    formset = ChallengeFormSet


class CampaignForm(forms.ModelForm):

    class Meta:
        model = Campaign
        fields = '__all__'

    def clean(self):
        cleaned_data = super(CampaignForm, self).clean()
        self._validate_thanking_msg(cleaned_data)
        self._validate_msg_languages(cleaned_data)

    # Check if a thanking message was included into the campaign's message list
    def _validate_thanking_msg(self, cleaned_data):
        msgs = cleaned_data.get("messages").all()
        exists_thanking_msg = False
        for message in msgs:
            if message.category == "thanks_contribution":
                exists_thanking_msg = True
                break
        if not exists_thanking_msg:
            msg = "Please include into the messages list a message to thank participants for their contributions."
            raise forms.ValidationError(_(msg))
        else:
            return cleaned_data

    # Check if all the messages are in the same language
    def _validate_msg_languages(self, cleaned_data):
        msgs = cleaned_data.get("messages").all()
        lang = msgs[0].language
        for message in msgs:
            if message.language != lang:
                msg = "All the messages have to be in the same language."
                raise forms.ValidationError(_(msg))


class CampaignAdmin(admin.ModelAdmin):
    inlines = [ChallengeInline]
    list_display = ('id','name', 'initiative', 'list_challenges')
    ordering = ('id',)
    filter_horizontal = ('messages',)
    form = CampaignForm

    def list_challenges(self, obj):
        challenges = obj.challenge_set.all()
        num_challenges = len(challenges)
        count_challenge = 1
        str_challenges = ""
        for challenge in challenges:
            if count_challenge < num_challenges:
                str_challenges += challenge.name.encode('utf-8') + ", "
            else:
                str_challenges += challenge.name.encode('utf-8')
            count_challenge += 1
        return str_challenges
    list_challenges.short_description = 'Challenges'


class InitiativeForm(forms.ModelForm):

    class Meta:
        model = Initiative
        fields = ('name', 'organizer', 'hashtag', 'url', 'language', 'account', 'social_sharing_message')

    def clean(self):
        cleaned_data = super(InitiativeForm, self).clean()
        account = cleaned_data.get("account")
        ss_msg = cleaned_data.get("social_sharing_message")

        if ss_msg is not None:
            if account.channel.max_length_msgs is not None:
                if len(ss_msg) > account.channel.max_length_msgs:
                    msg = "The social sharing message is longer than %(max_character)s characters, which is %(channel)s " \
                          "message length limit."
                    raise forms.ValidationError(_(msg),params={'max_character': account.channel.max_length_msgs,
                                                               'channel': account.channel.name})
                else:
                    return cleaned_data
            else:
                return cleaned_data
        else:
            return cleaned_data


class InitiativeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organizer', 'hashtag', 'account', 'url', 'language', 'social_sharing_message')
    ordering = ('id',)
    form = InitiativeForm


class SettingAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'description', 'value')
    ordering = ('id',)


class ExtraInfoAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'description', 'style_answer', 'format_answer')
    ordering = ('id',)


class MessageInfoForm(forms.ModelForm):

    class Meta:
        model = Message
        fields = ('name', 'body', 'key_terms', 'category', 'answer_terms', 'language', 'channel')

    def clean(self):
        cleaned_data = super(MessageInfoForm, self).clean()
        body = cleaned_data.get("body")
        channel = cleaned_data.get("channel")
        key_terms = cleaned_data.get("key_terms")
        category = cleaned_data.get("category")
        answer_terms = cleaned_data.get("answer_terms")

        if channel.max_length_msgs is None or len(body) <= channel.max_length_msgs:
            msg = body.split()
            key_terms = key_terms.split()
            not_found_term = ""
            for term in key_terms:
                found = False
                for word in msg:
                    word = word.rstrip('?:!.,;')  # Remove punctuation symbols
                    if term.lower() == word.lower():
                        found = True
                if not found:
                    not_found_term = term
                    break
            if not_found_term:
                msg = "The key term %(term)s is not included in the body of the message."
                raise forms.ValidationError(_(msg), params={'term': not_found_term})
            else:
                if category == "ask_change_contribution" and answer_terms == "":
                    msg = "Please define in answer terms field the terms you expect as a reply to the question about" \
                          "changing a previous contribution."
                    raise forms.ValidationError(_(msg))
                else:
                    return cleaned_data
        else:
            msg = "The length of the body is longer than %(max_length)s characters, which is %(channel)s message length " \
                  "limit."
            raise forms.ValidationError(_(msg), params={'max_length': channel.max_length_msgs, 'channel': channel.name})


class MessageInfoAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'body', 'key_terms', 'category', 'answer_terms', 'campaign', 'initiative')
    ordering = ('id',)
    list_filter = ['language']
    form = MessageInfoForm

    def campaign(self, obj):
        campaigns = obj.campaign_set.all()
        campaign_names = ""
        for c in campaigns:
            campaign_names += c.name + " "
        return campaign_names

    def initiative(self, obj):
        campaigns = obj.campaign_set.all()
        initiative_names = ""
        for c in campaigns:
            initiative_names += c.initiative.name + " "
        return initiative_names


class AppPostForm(forms.ModelForm):

    class Meta:
        model = AppPost
        fields = ('text', 'initiative', 'campaign', 'challenge', 'channel', 'category')

    def clean(self):
        cleaned_data = super(AppPostForm, self).clean()
        channel = cleaned_data.get("channel")
        text = cleaned_data.get("text")

        if len(text) > channel.max_length_msgs:
            msg = "The length of the text is longer than %(max_length)s characters, which is %(channel)s message " \
                  "length limit."
            raise forms.ValidationError(_(msg), params={'max_length': channel.max_length_msgs, 'channel': channel.name})


class AppPostAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['text', 'initiative', 'campaign', 'challenge', 'channel', 'category']})
    ]
    list_display = ('id','datetime', 'text', 'channel', 'url', 'initiative', 'campaign', 'challenge')
    ordering = ('datetime',)
    form = AppPostForm

    def get_queryset(self, request):
        qs = super(AppPostAdmin, self).get_queryset(request)
        return qs.filter(category="EN")

    def save_model(self, request, obj, form, change):
        if obj.channel.name == "Twitter":
            social_network = Twitter()
        else:
            raise Exception("Unknown channel named %s" % obj.channel.name)

        if social_network:
            payload = {'parent_post_id': None, 'type_msg': obj.category,
                       'post_id': None, 'initiative_id': obj.initiative.id,
                       'campaign_id': obj.campaign.id, 'challenge_id': obj.challenge.id,
                       'author_id': None, 'initiative_short_url': None}
            payload_json = json.dumps(payload)
            social_network.queue_message(message=obj.text, type_msg="PU", payload=payload_json)
        else:
            raise Exception("The social network object couldn't be created")


class ContributionPostAdmin(admin.ModelAdmin):
    list_display = ('datetime', 'author', 'zipcode', 'contribution', 'full_text', 'initiative', 'campaign', 'challenge',
                    'channel', 'votes', 're_posts', 'bookmarks', 'source', 'view')
    list_display_links = ('contribution',)
    ordering = ('datetime',)
    list_filter = ['initiative', 'campaign', 'challenge', 'channel']

    def get_queryset(self, request):
        qs = super(ContributionPostAdmin, self).get_queryset(request)
        return qs.filter(status="PE")

    def view(self, obj):
        return format_html("<a href=\"" + obj.url + "\" target=\"_blank\">Link</a>")

    def zipcode(self, obj):
        return obj.author.zipcode

    def has_add_permission(self, request):
        return False


class ChannelAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'enabled', 'status', 'row_actions')
    ordering = ('id',)

    def get_queryset(self, request):
        qs = super(ChannelAdmin, self).get_queryset(request)
        # Create a persistent object that will manage the enabled social network channels
        if not 'meta_channel' in request.session:
            channels = []
            for channel in qs:
                if channel.enabled:
                    channels.append(channel.name.lower())
            mt = MetaChannel(channels)
            request.session['meta_channel'] = pickle.dumps(mt)
        return qs

    def row_actions(self, obj):
        if hasattr(settings, 'URL_PREFIX') and settings.URL_PREFIX:
            listen_url_href = """{0}/cparte/listen/{1}""".format(settings.URL_PREFIX, obj.name)
            hangup_url_href = """{0}/cparte/hangup/{1}""".format(settings.URL_PREFIX, obj.name)
        else:
            listen_url_href = """/cparte/listen/{0}""".format(obj.name)
            hangup_url_href = """/cparte/hangup/{0}""".format(obj.name)
        if obj.status:
            return """<a href={0} class="btn btn-success btn-xs disabled">On</a> |
                      <a href={1} class="btn btn-danger btn-xs">Off</a>""" \
                      .format(listen_url_href, hangup_url_href)
        else:
            return """<a href={0} class="btn btn-success btn-xs">On</a> |
                      <a href={1} class="btn btn-danger btn-xs disabled">Off</a>""" \
                      .format(listen_url_href, hangup_url_href)
    row_actions.short_description = 'Actions'
    row_actions.allow_tags = True


class AccountAdmin(admin.ModelAdmin):
    list_display = ('id','owner','id_in_channel','handler','url','channel')
    ordering = ('id',)


class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('id','name','initiative','campaign','hashtag','style_answer','format_answer','max_length_answer')
    ordering = ('id',)

    def initiative(self, obj):
        return obj.campaign.initiative.name


class SharePostAdmin(admin.ModelAdmin):
    list_display = ('id','datetime', 'author', 'text', 'channel', 'url', 'initiative', 'votes', 're_posts', 'bookmarks',
                    'similarity_per', 'view')
    ordering = ('datetime',)
    list_filter = ['initiative', 'channel']

    def view(self, obj):
        return format_html("<a href=\"" + obj.url + "\" target=\"_blank\">Link</a>")

    def has_add_permission(self, request):
        return False

    def similarity_per(self, obj):
        return "%s%%" % obj.similarity
    similarity_per.short_description = 'Similarity'

admin.site.register(Initiative, InitiativeAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(Channel, ChannelAdmin)
admin.site.register(Message, MessageInfoAdmin)
admin.site.register(ExtraInfo, ExtraInfoAdmin)
admin.site.register(Setting, SettingAdmin)
admin.site.register(AppPost, AppPostAdmin)
admin.site.register(ContributionPost, ContributionPostAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(SharePost, SharePostAdmin)