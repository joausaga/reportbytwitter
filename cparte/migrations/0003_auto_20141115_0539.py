# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cparte', '0002_challenge_accept_changes'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='channel',
            name='pid_messenger',
        ),
        migrations.AlterField(
            model_name='challenge',
            name='answers_from_same_author',
            field=models.IntegerField(default=1, help_text=b'Number of allowed answers from the same author. Use -1 for not limit'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='message',
            name='category',
            field=models.CharField(max_length=100, choices=[(b'thanks_contribution', b'Express thanks for a contribution'), (b'incorrect_answer', b'Incorrect answer'), (b'ask_change_contribution', b'Ask whether participant wants to change a previous contribution'), (b'thanks_change', b'Express thanks for changing a contribution'), (b'contribution_cannot_save', b'Notify that a contribution cannot be saved'), (b'limit_answers_reached', b'Notify that the limit of answers has been reached'), (b'request_author_extrainfo', b'Ask for participant extra information'), (b'incorrect_author_extrainfo', b'Incorrect participant extra information'), (b'author_banned', b'Notify the author that he/she was banned'), (b'not_understandable_change_contribution_reply', b'Not understandable reply to the request aboutchanging a previous contribution'), (b'already_answered_unchangeable_challenge', b'Participant already answered an unchangeable challenge')]),
            preserve_default=True,
        ),
    ]
