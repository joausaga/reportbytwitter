from django.apps import AppConfig

import models

channel_middleware = None


class CparteApp(AppConfig):
    name = 'cparte'
    verbose_name = "CParte"

    def ready(self):
        # Instantiating the social network middleware channel
        global channel_middleware
        channel_middleware = models.ChannelMiddleware()


