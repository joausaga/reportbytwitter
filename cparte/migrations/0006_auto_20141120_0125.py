# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cparte', '0005_auto_20141118_0502'),
    ]

    operations = [
        migrations.RenameField(
            model_name='channel',
            old_name='pid',
            new_name='streaming_pid',
        ),
        migrations.AddField(
            model_name='channel',
            name='session_info',
            field=models.TextField(null=True, editable=False),
            preserve_default=True,
        ),
    ]
