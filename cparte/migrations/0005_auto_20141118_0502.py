# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cparte', '0004_auto_20141115_0645'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='msgqueue',
            name='channel',
        ),
        migrations.DeleteModel(
            name='MsgQueue',
        ),
        migrations.DeleteModel(
            name='Setting',
        ),
    ]
