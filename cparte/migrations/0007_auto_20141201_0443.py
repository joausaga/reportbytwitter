# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cparte', '0006_auto_20141120_0125'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='last_message',
            field=models.DateTimeField(null=True, editable=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='channel',
            name='max_length_msgs',
            field=models.IntegerField(help_text=b'Maximum length of messages to send through this channel from the application. Leave it blank for unlimited lengths.', null=True, blank=True),
            preserve_default=True,
        ),
    ]
