# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cparte', '0003_auto_20141115_0539'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='pid',
            field=models.CharField(max_length=50, null=True, editable=False),
            #preserve_default=True,
        ),
    ]
