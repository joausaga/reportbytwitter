from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from django.contrib import messages
from cparte.models import Initiative, Campaign, Challenge, Channel, Setting, ExtraInfo, Message, AppPost, Twitter, \
                          ContributionPost, Account, MetaChannel, SharePost

import logging
import json
import pickle


logger = logging.getLogger(__name__)


class ChallengeInline(admin.StackedInline):
    model = Challenge
    extra = 1


class CampaignAdmin(admin.ModelAdmin):
    inlines = [ChallengeInline]
    list_display = ('id','name', 'initiative', 'list_challenges')
    ordering = ('id',)
    filter_horizontal = ('messages',)

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


class InitiativeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organizer', 'hashtag', 'account', 'url', 'language', 'social_sharing_message')
    ordering = ('id',)

    def save_model(self, request, obj, form, change):
        if obj.social_sharing_message is not None:
            if obj.account.channel.max_length_msgs is None:
                obj.save()
            else:
                if len(obj.social_sharing_message) <= obj.account.channel.max_length_msgs:
                    obj.save()
                else:
                    self.message_user(request,
                                      "The social sharing message must not be longer than %s characters, which is "
                                      "maximum length allowed by the channel %s associated to the account" %
                                      (obj.account.channel.max_length_msgs, obj.account.channel.name),
                                      level=messages.ERROR)
        else:
            obj.save()


class SettingAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'description', 'value')
    ordering = ('id',)


class ExtraInfoAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'description', 'style_answer', 'format_answer')
    ordering = ('id',)


class MessageInfoAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'body', 'key_terms', 'category', 'answer_terms', 'campaign', 'initiative')
    ordering = ('id',)
    list_filter = ['language']

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

    def save_model(self, request, obj, form, change):
        if obj.channel.max_length_msgs is None or len(obj.body) <= obj.channel.max_length_msgs:
            msg = obj.body.split()
            key_terms = obj.key_terms.split()
            not_found_term = ""
            for term in key_terms:
                found = False
                for word in msg:
                    if term.lower() == word.lower():
                        found = True
                if not found:
                    not_found_term = term
                    break
            if not_found_term:
                self.message_user(request, "The key term: %s is not included in the message" % not_found_term,
                                  level=messages.ERROR)
            else:
                obj.save()
        else:
            self.message_user(request, "The limit of the message body cannot exceed the channel's length for messages "
                                       "%s" % obj.channel.max_length_msgs, level=messages.ERROR)


class AppPostAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,{'fields': ['text', 'initiative', 'campaign', 'challenge', 'channel', 'category']})
    ]
    list_display = ('id','datetime', 'text', 'channel', 'url', 'initiative', 'campaign', 'challenge')
    ordering = ('datetime',)

    def queryset(self, request):
        qs = super(AppPostAdmin, self).queryset(request)
        return qs.filter(category="EN")

    def save_model(self, request, obj, form, change):
        ch = Channel.objects.get(name=obj.channel.name)
        if obj.channel.name == "Twitter":
            social_network = Twitter()
        else:
            raise Exception("Unknown channel named %s" % obj.channel.name)

        if social_network:
            social_network.authenticate()
            if len(obj.text) <= ch.max_length_msgs:
                payload = {'parent_post_id': None, 'type_msg': obj.category,
                           'post_id': None, 'initiative_id': obj.initiative.id,
                           'campaign_id': obj.campaign.id, 'challenge_id': obj.challenge.id}
                payload_json = json.dumps(payload)
                social_network.queue_message(message=obj.text, type_msg="PU", payload=payload_json)
                obj.save()
            else:
                raise Exception("The length of the message exceed the channel's limit (%s) for messages" % ch.max_length_msgs)
        else:
            raise Exception("The social network object couldn't be created")


class ContributionPostAdmin(admin.ModelAdmin):
    list_display = ('datetime', 'author', 'zipcode', 'contribution', 'full_text', 'initiative', 'campaign', 'challenge',
                    'channel', 'votes', 're_posts', 'bookmarks', 'source', 'view')
    list_display_links = ('contribution',)
    ordering = ('datetime',)
    list_filter = ['initiative', 'campaign', 'challenge', 'channel']

    def queryset(self, request):
        qs = super(ContributionPostAdmin, self).queryset(request)
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

    def queryset(self, request):
        qs = super(ChannelAdmin, self).queryset(request)
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
    list_display = ('id','datetime', 'text', 'channel', 'url', 'initiative', 'votes', 're_posts', 'bookmarks',
                    'similarity', 'view')
    ordering = ('datetime',)
    list_filter = ['initiative', 'channel']

    def view(self, obj):
        return format_html("<a href=\"" + obj.url + "\" target=\"_blank\">Link</a>")

    def has_add_permission(self, request):
        return False

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