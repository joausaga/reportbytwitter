# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('owner', models.CharField(max_length=50)),
                ('id_in_channel', models.CharField(max_length=50)),
                ('handler', models.CharField(max_length=50)),
                ('url', models.URLField()),
                ('consumer_key', models.CharField(max_length=100)),
                ('consumer_secret', models.CharField(max_length=100)),
                ('token', models.CharField(max_length=100)),
                ('token_secret', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AppPost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('id_in_channel', models.CharField(max_length=50)),
                ('datetime', models.DateTimeField()),
                ('text', models.TextField()),
                ('url', models.URLField(null=True)),
                ('votes', models.IntegerField(default=0)),
                ('re_posts', models.IntegerField(default=0)),
                ('bookmarks', models.IntegerField(default=0)),
                ('delivered', models.BooleanField(default=True)),
                ('category', models.CharField(max_length=3, choices=[(b'EN', b'Engagement'), (b'PR', b'Promotion')])),
                ('payload', models.TextField(null=True, editable=False)),
                ('answered', models.BooleanField(default=False)),
                ('recipient_id', models.CharField(max_length=50, null=True, editable=False)),
                ('app_parent_post', models.ForeignKey(to='cparte.AppPost', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(null=True)),
                ('screen_name', models.CharField(max_length=100)),
                ('id_in_channel', models.CharField(max_length=50)),
                ('language', models.CharField(max_length=10, null=True)),
                ('country', models.CharField(max_length=50, null=True, blank=True)),
                ('city', models.CharField(max_length=50, null=True, blank=True)),
                ('zipcode', models.CharField(max_length=10, null=True, blank=True)),
                ('national_id', models.CharField(max_length=20, null=True, blank=True)),
                ('address', models.CharField(max_length=200, null=True, blank=True)),
                ('phone', models.CharField(max_length=20, null=True, blank=True)),
                ('email', models.EmailField(max_length=254, null=True, blank=True)),
                ('banned', models.BooleanField(default=False, editable=False)),
                ('input_mistakes', models.IntegerField(default=0, editable=False)),
                ('request_mistakes', models.IntegerField(default=0, editable=False)),
                ('friends', models.IntegerField(default=0, editable=False)),
                ('followers', models.IntegerField(default=0, editable=False)),
                ('groups', models.IntegerField(default=0, editable=False)),
                ('posts_count', models.IntegerField(default=0, editable=False)),
                ('url', models.URLField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('hashtag', models.CharField(help_text=b"Max length 14 characters (do not include '#')", max_length=14, null=True, blank=True)),
                ('url', models.URLField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Challenge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('hashtag', models.CharField(help_text=b"Max length 14 characters (do not include '#')", max_length=14)),
                ('style_answer', models.CharField(max_length=20, choices=[(b'FR', b'Free'), (b'ST', b'Structured')])),
                ('format_answer', models.CharField(help_text=b'A regular expression or blank in case of freestyle answers', max_length=50, null=True, blank=True)),
                ('max_length_answer', models.IntegerField(null=True, blank=True)),
                ('answers_from_same_author', models.IntegerField(default=1, help_text=b'Number of answers allowed from the same author. Use -1 for not limit')),
                ('url', models.URLField(null=True, blank=True)),
                ('campaign', models.ForeignKey(to='cparte.Campaign')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('enabled', models.BooleanField(default=False)),
                ('status', models.BooleanField(default=False, editable=False)),
                ('url', models.URLField(null=True)),
                ('max_length_msgs', models.IntegerField(help_text=b'Maximum length of messages to send throughthis channel from the application. Leave it blank for unlimited lengths.', null=True, blank=True)),
                ('pid', models.IntegerField(default=-1, editable=False)),
                ('pid_messenger', models.IntegerField(default=-1, null=True, editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContributionPost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('id_in_channel', models.CharField(max_length=50)),
                ('datetime', models.DateTimeField()),
                ('contribution', models.TextField()),
                ('full_text', models.TextField()),
                ('url', models.URLField()),
                ('in_reply_to', models.CharField(max_length=50, null=True)),
                ('votes', models.IntegerField(default=0)),
                ('re_posts', models.IntegerField(default=0)),
                ('bookmarks', models.IntegerField(default=0)),
                ('status', models.CharField(max_length=3, choices=[(b'TE', b'Temporal'), (b'PE', b'Permanent'), (b'DI', b'Discarded')])),
                ('source', models.CharField(max_length=100, null=True)),
                ('author', models.ForeignKey(to='cparte.Author')),
                ('campaign', models.ForeignKey(to='cparte.Campaign')),
                ('challenge', models.ForeignKey(to='cparte.Challenge')),
                ('channel', models.ForeignKey(to='cparte.Channel')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExtraInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Max length 15 characters', max_length=15)),
                ('description', models.TextField(null=True)),
                ('style_answer', models.CharField(max_length=20, choices=[(b'FR', b'Free'), (b'ST', b'Structured')])),
                ('format_answer', models.CharField(help_text=b'A regular expression or blank in case of freestyle answers', max_length=50, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Initiative',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('organizer', models.CharField(max_length=50)),
                ('hashtag', models.CharField(help_text=b"Max length 14 characters (do not include '#')", unique=True, max_length=14)),
                ('url', models.URLField(null=True, blank=True)),
                ('language', models.CharField(max_length=3, choices=[(b'en', b'English'), (b'es', b'Spanish'), (b'it', b'Italian')])),
                ('account', models.ForeignKey(to='cparte.Account')),
                ('social_sharing_message', models.CharField(help_text=b'Default text for social sharing buttons', max_length=200, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('body', models.TextField()),
                ('key_terms', models.CharField(max_length=100)),
                ('category', models.CharField(max_length=100, choices=[(b'thanks_contribution', b'Express thanks for a contribution'), (b'incorrect_answer', b'Incorrect answer'), (b'ask_change_contribution', b'Ask whether participant wants to change a previous contribution'), (b'thanks_change', b'Express thanks for changing a contribution'), (b'contribution_cannot_save', b'Notify that a contribution cannot be saved'), (b'limit_answers_reached', b'Notify that the limit of answers has been reached'), (b'request_author_extrainfo', b'Ask for participant extra information'), (b'incorrect_author_extrainfo', b'Incorrect participant extra information'), (b'author_banned', b'Notify the author that he/she was banned'), (b'not_understandable_change_contribution_reply', b'Not understandable reply to the request aboutchanging a previous contribution')])),
                ('answer_terms', models.CharField(help_text=b'Max length 10 characters', max_length=10, null=True, blank=True)),
                ('language', models.CharField(max_length=3, choices=[(b'en', b'English'), (b'es', b'Spanish'), (b'it', b'Italian')])),
                ('channel', models.ForeignKey(to='cparte.Channel')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MsgQueue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('message_text', models.TextField()),
                ('recipient_id', models.CharField(max_length=100, null=True)),
                ('type', models.CharField(max_length=3, choices=[(b'PU', b'Public'), (b'RE', b'Reply'), (b'DM', b'Direct Message')])),
                ('payload', models.TextField(null=True)),
                ('channel', models.ForeignKey(to='cparte.Channel')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Setting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField(null=True, blank=True)),
                ('value', models.TextField()),
                ('type', models.CharField(max_length=3, choices=[(b'INT', b'Integer'), (b'STR', b'String')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SharePost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('id_in_channel', models.CharField(max_length=50)),
                ('datetime', models.DateTimeField()),
                ('text', models.TextField()),
                ('url', models.URLField()),
                ('votes', models.IntegerField(default=0)),
                ('re_posts', models.IntegerField(default=0)),
                ('bookmarks', models.IntegerField(default=0)),
                ('similarity', models.IntegerField(default=0)),
                ('author', models.ForeignKey(to='cparte.Author')),
                ('campaign', models.ForeignKey(to='cparte.Campaign')),
                ('challenge', models.ForeignKey(to='cparte.Challenge')),
                ('channel', models.ForeignKey(to='cparte.Channel')),
                ('initiative', models.ForeignKey(to='cparte.Initiative')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='extrainfo',
            name='messages',
            field=models.ManyToManyField(to='cparte.Message'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contributionpost',
            name='initiative',
            field=models.ForeignKey(to='cparte.Initiative'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='campaign',
            name='extrainfo',
            field=models.ForeignKey(blank=True, to='cparte.ExtraInfo', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='campaign',
            name='initiative',
            field=models.ForeignKey(to='cparte.Initiative'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='campaign',
            name='messages',
            field=models.ManyToManyField(to='cparte.Message'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='author',
            name='channel',
            field=models.ForeignKey(to='cparte.Channel'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='apppost',
            name='campaign',
            field=models.ForeignKey(to='cparte.Campaign'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='apppost',
            name='challenge',
            field=models.ForeignKey(to='cparte.Challenge'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='apppost',
            name='channel',
            field=models.ForeignKey(to='cparte.Channel'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='apppost',
            name='contribution_parent_post',
            field=models.ForeignKey(to='cparte.ContributionPost', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='apppost',
            name='initiative',
            field=models.ForeignKey(to='cparte.Initiative'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='channel',
            field=models.ForeignKey(to='cparte.Channel'),
            preserve_default=True,
        ),
    ]
