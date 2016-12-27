from log import logger
try:
    from redobject import RedObject
except ImportError:
    logger.warn('redis and/or redtruck not installed, pub/sub disabled.')
    RedObject = None
from weakref import proxy
from gi.repository import Gdk


if RedObject:
    class MessagingBus(RedObject):
        def __init__(self, app):
            self.app = proxy(app)
            super(MessagingBus, self).__init__('org.dunai.vkplayer')

        def on_request_state_handler(self, data):
            self.broadcast('state_changed', [self.app.player.is_downloading, self.app.player.is_playing, self.app.current_title_string])

        def on_play_pause_handler(self, data):
            def action():
                if self.app.player.is_playing:
                    self.app._on_pause_clicked()
                else:
                    self.app._on_play_clicked()
            Gdk.threads_add_idle(0, action)

        def on_play_random_handler(self, data):
            Gdk.threads_add_idle(0, self.app._on_random_clicked)

        def on_play_prev_handler(self, data):
            Gdk.threads_add_idle(0, self.app.play_prev)

        def on_play_next_handler(self, data):
            Gdk.threads_add_idle(0, self.app.play_next)

else:
    class MessagingBus(object):
        def __init__(self, *args, **kwargs):
            pass

        def start(self, *args, **kwargs):
            pass

        def broadcast(self, *args, **kwargs):
            pass
