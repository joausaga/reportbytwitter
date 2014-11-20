from django.db import models

LANGUAGES = (
    ('en', 'English'),
    ('es', 'Spanish'),
    ('it', 'Italian')
)


class Channel(models.Model):
    name = models.CharField(max_length=50)
    enabled = models.BooleanField(default=False)
    status = models.BooleanField(default=False, blank=True, editable=False)
    url = models.URLField(null=True)
    max_length_msgs = models.IntegerField(null=True, blank=True, help_text="Maximum length of messages to send through"
                                                                           "this channel from the application. Leave it"
                                                                           " blank for unlimited lengths.")
    streaming_pid = models.CharField(max_length=50, editable=False, null=True)
    session_info = models.TextField(editable=False, null=True)

    def __unicode__(self):
        return self.name

    def connect(self, streaming_pid, session_info):
        self.status = True
        self.streaming_pid = streaming_pid
        self.session_info = session_info
        self.save()

    def disconnect(self):
        if self.status:
            self.streaming_pid = ""
            self.session_info = ""
            self.status = False
            self.save()


class Account(models.Model):
    owner = models.CharField(max_length=50)
    id_in_channel = models.CharField(max_length=50)
    handler = models.CharField(max_length=50)
    url = models.URLField()
    channel = models.ForeignKey(Channel)
    consumer_key = models.CharField(max_length=100)
    consumer_secret = models.CharField(max_length=100)
    token = models.CharField(max_length=100)
    token_secret = models.CharField(max_length=100)

    def __unicode__(self):
        return self.owner


class Message(models.Model):
    name = models.CharField(max_length=50)
    body = models.TextField()
    key_terms = models.CharField(max_length=100)
    CATEGORIES = (
                    ('thanks_contribution', 'Express thanks for a contribution'),
                    ('incorrect_answer', 'Incorrect answer'),
                    ('ask_change_contribution', 'Ask whether participant wants to change a previous contribution'),
                    ('thanks_change', 'Express thanks for changing a contribution'),
                    ('contribution_cannot_save', 'Notify that a contribution cannot be saved'),
                    ('limit_answers_reached', 'Notify that the limit of answers has been reached'),
                    ('request_author_extrainfo', 'Ask for participant extra information'),
                    ('incorrect_author_extrainfo', 'Incorrect participant extra information'),
                    ('author_banned', 'Notify the author that he/she was banned'),
                    ('not_understandable_change_contribution_reply', 'Not understandable reply to the request about'
                                                                     'changing a previous contribution'),
                    ('already_answered_unchangeable_challenge', 'Participant already answered an unchangeable challenge'),
    )
    category = models.CharField(max_length=100, choices=CATEGORIES)
    answer_terms = models.CharField(max_length=10, null=True, blank=True, help_text="Max length 10 characters")
    language = models.CharField(max_length=3, choices=LANGUAGES)
    channel = models.ForeignKey(Channel)

    def __unicode__(self):
        return self.name


class ExtraInfo(models.Model):
    name = models.CharField(max_length=15, help_text="Max length 15 characters")
    description = models.TextField(null=True)
    STYLE_ANSWER = (
        ('FR', 'Free'),
        ('ST', 'Structured')
    )
    style_answer = models.CharField(max_length=20, choices=STYLE_ANSWER)
    format_answer = models.CharField(max_length=50, null=True, blank=True, help_text="A regular expression or blank in "
                                                                                     "case of freestyle answers")
    messages = models.ManyToManyField(Message)

    def __unicode__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True)
    screen_name = models.CharField(max_length=100)
    id_in_channel = models.CharField(max_length=50)
    channel = models.ForeignKey(Channel)
    language = models.CharField(max_length=10, null=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    zipcode = models.CharField(max_length=10, null=True, blank=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    banned = models.BooleanField(editable=False, default=False)
    input_mistakes = models.IntegerField(editable=False, default=0)
    request_mistakes = models.IntegerField(editable=False, default=0)
    friends = models.IntegerField(editable=False, default=0)
    followers = models.IntegerField(editable=False, default=0)
    groups = models.IntegerField(editable=False, default=0)
    posts_count = models.IntegerField(editable=False, default=0)
    url = models.URLField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    def reset_mistake_flags(self):
        self.input_mistakes = 0
        self.request_mistakes = 0
        self.save()

    def is_banned(self):
        return self.banned

    def ban(self):
        self.banned = True
        self.save()

    def add_input_mistake(self):
        self.input_mistakes += 1
        self.save()

    def add_request_mistake(self):
        self.request_mistakes += 1
        self.save()

    def get_input_mistakes(self):
        return self.input_mistakes

    def get_request_mistakes(self):
        return self.request_mistakes

    def get_extra_info(self):
        return self.zipcode

    def set_extra_info(self, extra_info):
        self.zipcode = extra_info  # For CRC extra_info equals zipcode
        self.save()


class Initiative(models.Model):
    name = models.CharField(max_length=100)
    organizer = models.CharField(max_length=50)
    hashtag = models.CharField(unique=True, max_length=14, help_text="Max length 14 characters (do not include '#')")
    url = models.URLField(null=True, blank=True)
    language = models.CharField(max_length=3, choices=LANGUAGES)
    account = models.ForeignKey(Account)
    social_sharing_message = models.CharField(max_length=200, blank=True, null=True,
                                              help_text="Default text for social sharing buttons")

    def __unicode__(self):
        return self.name


class Campaign(models.Model):
    name = models.CharField(max_length=100)
    initiative = models.ForeignKey(Initiative)
    hashtag = models.CharField(max_length=14, null=True, blank=True,
                               help_text="Max length 14 characters (do not include '#')")
    url = models.URLField(null=True, blank=True)
    extrainfo = models.ForeignKey(ExtraInfo, blank=True, null=True)
    messages = models.ManyToManyField(Message)

    def __unicode__(self):
        return self.name


class Challenge(models.Model):
    name = models.CharField(max_length=100)
    campaign = models.ForeignKey(Campaign)
    hashtag = models.CharField(max_length=14, help_text="Max length 14 characters (do not include '#')")
    STYLE_ANSWER = (
        ('FR', 'Free'),
        ('ST', 'Structured')
    )
    style_answer = models.CharField(max_length=20, choices=STYLE_ANSWER)
    format_answer = models.CharField(max_length=50, null=True, blank=True,
                                     help_text="A regular expression or blank in case of freestyle answers")
    max_length_answer = models.IntegerField(null=True, blank=True)
    answers_from_same_author = models.IntegerField(default=1, help_text="Number of allowed answers from the same "
                                                                        "author. Use -1 for not limit")
    url = models.URLField(null=True, blank=True)
    accept_changes = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name


class ContributionPost(models.Model):
    id_in_channel = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    contribution = models.TextField()
    full_text = models.TextField()
    url = models.URLField()
    author = models.ForeignKey(Author)
    in_reply_to = models.CharField(max_length=50, null=True)
    initiative = models.ForeignKey(Initiative)
    campaign = models.ForeignKey(Campaign)
    challenge = models.ForeignKey(Challenge)
    channel = models.ForeignKey(Channel)
    votes = models.IntegerField(default=0)      # e.g. +1 in Google+, like in Facebook
    re_posts = models.IntegerField(default=0)   # e.g. Share in Facebook, RT in Twitter
    bookmarks = models.IntegerField(default=0)  # e.g. Favourite in Twitter
    STATUS = (('TE', 'Temporal'), ('PE', 'Permanent'), ('DI', 'Discarded'))
    status = models.CharField(max_length=3, choices=STATUS)
    source = models.CharField(max_length=100, null=True)

    def __unicode__(self):
        return self.url

    def preserve(self):
        self.status = "PE"
        self.save()

    def discard(self):
        self.status = "DI"
        self.save()

    def temporal(self):
        if self.status == "TE":
            return True
        else:
            return False


class AppPost(models.Model):
    id_in_channel = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    text = models.TextField()
    url = models.URLField(null=True)
    app_parent_post = models.ForeignKey('self', null=True)
    contribution_parent_post = models.ForeignKey(ContributionPost, null=True)
    initiative = models.ForeignKey(Initiative)
    campaign = models.ForeignKey(Campaign)
    challenge = models.ForeignKey(Challenge)
    channel = models.ForeignKey(Channel)
    votes = models.IntegerField(default=0)          # e.g. +1 in Google+, like in Facebook
    re_posts = models.IntegerField(default=0)       # e.g. Share in Facebook, RT in Twitter
    bookmarks = models.IntegerField(default=0)      # e.g. Favourite in Twitter
    delivered = models.BooleanField(default=True)
    CATEGORIES = (('EN', 'Engagement'), ('PR', 'Promotion'))
    category = models.CharField(max_length=3, choices=CATEGORIES)
    payload = models.TextField(null=True, editable=False)
    answered = models.BooleanField(default=False)
    recipient_id = models.CharField(max_length=50, null=True, editable=False)

    def __unicode__(self):
        if self.url:
            return self.url
        else:
            return self.text

    def do_answer(self):
        self.answered = True
        self.save()


class SharePost(models.Model):
    id_in_channel = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    text = models.TextField()
    url = models.URLField()
    author = models.ForeignKey(Author)
    initiative = models.ForeignKey(Initiative)
    campaign = models.ForeignKey(Campaign)
    challenge = models.ForeignKey(Challenge)
    channel = models.ForeignKey(Channel)
    votes = models.IntegerField(default=0)      # e.g. +1 in Google+, like in Facebook
    re_posts = models.IntegerField(default=0)   # e.g. Share in Facebook, RT in Twitter
    bookmarks = models.IntegerField(default=0)  # e.g. Favourite in Twitter
    similarity = models.IntegerField(default=0)