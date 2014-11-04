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

        campaign = self.instance
        msgs = campaign.messages.all()
        exists_unchangeable_challenge = False
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cleaned_data = form.cleaned_data
            accept_changes = cleaned_data.get("accept_changes")
            if not accept_changes and accept_changes is not None:
                exists_unchangeable_challenge = True
                break
        if exists_unchangeable_challenge:
            exists_unchangeable_challenge_msg = False
            for message in msgs:
                if message.category == "already_answered_unchangeable_challenge":
                    exists_unchangeable_challenge_msg = True
                    break
            if not exists_unchangeable_challenge_msg:
                msg = "Please include the message that is going to be used to reply participants that try to change " \
                      "their answers to the following challenge."
                raise forms.ValidationError(_(msg))


class ChallengeInline(admin.StackedInline):
    model = Challenge
    extra = 1
    formset = ChallengeFormSet


class CampaignForm(forms.ModelForm):

    class Meta:
        model = Campaign
        fields = ('name', 'initiative', 'hashtag', 'url', 'extrainfo', 'messages')

    def clean(self):
        cleaned_data = super(CampaignForm, self).clean()
        challenges = self.instance.challenge_set.all()
        msgs = cleaned_data.get('messages')
        exists_unchangeable_challenge = False
        unchangeable_challenge = ""
        for form in self.forms:
            print form.cleaned_data

        # for challenge in challenges:
        #     if not challenge.accept_changes:
        #         exists_unchangeable_challenge = True
        #         unchangeable_challenge = challenge.name
        #         break
        # if exists_unchangeable_challenge:
        #     exists_unchangeable_challenge_msg = False
        #     for message in msgs:
        #         if message.category == "already_answered_unchangeable_challenge":
        #             exists_unchangeable_challenge_msg = True
        #             break
        #     if not exists_unchangeable_challenge_msg:
        #         msg = "Please add a message to reply in case a participant answers more than once the challenge '" \
        #               "%(challenge)s', which only accepts an unique answer."
        #         raise forms.ValidationError(_(msg),params={'challenge': unchangeable_challenge})


class CampaignAdmin(admin.ModelAdmin):
    inlines = [ChallengeInline]
    list_display = ('id','name', 'initiative', 'list_challenges')
    ordering = ('id',)
    filter_horizontal = ('messages',)
    #form = CampaignForm

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