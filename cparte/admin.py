from django.contrib import admin
from django.utils import timezone
from django.utils.formats import localize
from django.utils.html import format_html
from cparte.models import Initiative, Campaign, Challenge, Channel, Setting, ExtraInfo, Message, AppPost, Twitter, \
                          ContributionPost, Account

import logging


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
    list_display = ('id', 'name', 'organizer', 'hashtag', 'account', 'url', 'language')
    ordering = ('id',)


class SettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'value')


class ExtraInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'style_answer', 'format_answer')


class MessageInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'body', 'key_terms', 'category', 'answer_terms', 'campaign', 'initiative')

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
            obj.save()
        else:
            raise Exception("The limit of the message body cannot exceed the channel's length for messages %s" %
                            obj.channel.max_length_msgs)


class AppPostAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,        {'fields': ['text', 'initiative', 'campaign', 'challenge', 'channel', 'category']})
    ]
    list_display = ('datetime', 'text', 'channel', 'url', 'initiative', 'campaign', 'challenge')

    def queryset(self, request):
        qs = super(AppPostAdmin, self).queryset(request)
        return qs.filter(category="EN")

    def save_model(self, request, obj, form, change):
        ch = Channel.objects.get(name=obj.channel.name)
        if obj.channel.name == "Twitter":
            social_network = Twitter(ch.consumer_key, ch.consumer_secret, ch.access_token, ch.access_token_secret)
        else:
            raise Exception("Unknown channel named %s" % obj.channel.name)

        if social_network:
            social_network.authenticate()
            if len(obj.text) <= ch.max_length_msgs:
                response = social_network.post_public(obj.text)
                if response is not None:
                    logger.info("The post has been published into the channel %s" % obj.channel.name)
                    app_post = AppPost(id_in_channel=social_network.get_id_post(response), datetime=timezone.now(),
                                       text=obj.text, url=social_network.build_url_post(response), app_parent_post=None,
                                       contribution_parent_post=None, initiative=obj.initiative, campaign=obj.campaign,
                                       challenge=obj.challenge, channel=ch, votes=0, re_posts=0, bookmarks=0,
                                       delivered=True, category=obj.category)
                    app_post.save(force_insert=True)
                    logger.info("The post has been saved into the DB")
                else:
                    raise Exception("Error when trying to publish the post into the channel %s" % obj.channel.name)
            else:
                raise Exception("The length of the message exceed the channel's limit (%s) for messages" % ch.max_length_msgs)
        else:
            raise Exception("The social network object couldn't be created")


class ContributionPostAdmin(admin.ModelAdmin):
    list_display = ('datetime', 'author', 'zipcode', 'contribution', 'full_text', 'initiative', 'campaign', 'challenge', 'channel',
                    'view')
    list_display_links = ('contribution',)

    def view(self, obj):
        return format_html("<a href=\"" + obj.url + "\" target=\"_blank\">Link</a>")

    def zipcode(self, obj):
        return obj.author.zipcode

    def has_add_permission(self, request):
        return False


class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled', 'app_account_id', 'status', 'row_actions')

    def row_actions(self, obj):
        if obj.status:
            return """<a href="/cparte/listen/{0}" class="btn btn-success btn-xs disabled">On</a> |
                      <a href="/cparte/hangup/{0}" class="btn btn-danger btn-xs">Off</a>""" \
                      .format(obj.name)
        else:
            return """<a href="/cparte/listen/{0}" class="btn btn-success btn-xs">On</a> |
                      <a href="/cparte/hangup/{0}" class="btn btn-danger btn-xs disabled">Off</a>""" \
                      .format(obj.name)
    row_actions.short_description = 'Actions'
    row_actions.allow_tags = True


class AccountAdmin(admin.ModelAdmin):
    list_display = ('owner','id_in_channel','handler','url','channel')

class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('id','name','initiative','campaign','hashtag','style_answer','format_answer','max_length_answer')
    ordering = ('id',)

    def initiative(self, obj):
        return obj.campaign.initiative.name


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