try:
    import redis
except ImportError:
    print 'redis not installed, pub/sub disabled.'
    redis = None
from truck import BusObject
from weakref import proxy
from gi.repository import Gdk


class MessagingBus(BusObject):
    def __init__(self, app):
        self.app = proxy(app)
        super(MessagingBus, self).__init__('org.dunai.vkplayer')

    def on_request_state_handler(self):
        self.broadcast('state_changed', [self.app.player.is_playing, self.app.current_title_string])

    def on_play_pause_handler(self, data):
        def action():
            if self.app.player.is_playing:
                self.app._on_pause_clicked()
            else:
                self.app._on_play_clicked()
        Gdk.threads_add_idle(0, action)

    def on_play_random_handler(self, data):
        Gdk.threads_add_idle(0, self.app._on_random_clicked)


# import dbus
# import dbus.service
# import dbus.mainloop.glib
# from weakref import proxy
# from gi.repository import Gdk

# import json
# from threading import Thread
# from select import select
# import os
# import socket

# # class MessagingBus(dbus.service.Object):
# #     def __init__(self, app):
# #         dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

# #         self.app = proxy(app)

# #         self.session_bus = dbus.SessionBus()
# #         bus_name = dbus.service.BusName('org.dunai.vkplayer', bus=dbus.SessionBus())
# #         dbus.service.Object.__init__(self, bus_name, '/org/dunai/vkplayer')

# #         self.is_playing = False
# #         self.current_song = 'Idle'

# #         # super(MessagingBus, self).__init__()

# #     @dbus.service.method("org.dunai.vkplayer")  # , in_signature='s', out_signature='as')
# #     def get_current_song(self):
# #         return (self.is_playing, self.current_song)

# #     @dbus.service.method("org.dunai.vkplayer")  # , in_signature='s', out_signature='as')
# #     def play_pause(self):
# #         def action():
# #             if self.app.player.is_playing:
# #                 self.app._on_pause_clicked()
# #             else:
# #                 self.app._on_play_clicked()
# #         Gdk.threads_add_idle(0, action)

# #     @dbus.service.method("org.dunai.vkplayer")  # , in_signature='s', out_signature='as')
# #     def play_random(self):
# #         Gdk.threads_add_idle(0, self.app._on_random_clicked)

# #     @dbus.service.signal(dbus_interface='org.dunai.vkplayer', signature='bs')
# #     def song_changed(self, is_playing, new_title):
# #         self.is_playing = is_playing
# #         self.current_song = new_title


# class MessagingBus(Thread):
#     SOCK_FILE = '/tmp/vkplayer.sock'

#     def __init__(self, app):
#         super(MessagingBus, self).__init__()

#         self.app = proxy(app)
#         self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#         if os.path.exists(MessagingBus.SOCK_FILE):
#             os.unlink(MessagingBus.SOCK_FILE)
#         self.sock.bind(MessagingBus.SOCK_FILE)
#         # self.sock.settimeout(1)
#         self.sock.listen(5)

#         self.sockets = [self.sock]

#         self.running = True

#     def run(self):
#         while self.running:
#             iready, oready, eready = select(self.sockets, [], [], 1)
#             for sock in iready:
#                 print '.....'
#                 if sock is self.sock:
#                     client, info = self.sock.accept()
#                     self.sockets.append(client)
#                     print 'Connected', client
#                 else:
#                     print 'Can read'
#                     data = sock.recv(1024).strip()
#                     print 'Read {} bytes: {}'.format(len(data), data)
#                     if data:
#                         for line in filter(None, data.split()):
#                             response = self._process_line(line)
#                             if response is not None:
#                                 try:
#                                     sock.send(self._serialize(response))
#                                     print 'Sent', response
#                                 except:
#                                     print 'Write failed'
#                     else:
#                         print 'Dropped', sock
#                         self.sockets.remove(sock)
#             else:
#                 pass
#             # try:
#             #     sock, info = self.sock.accept()
#             # except:
#             #     continue
#             # else:
#             #     self.process
#             #     print sock, info

#     def _process_line(self, line):
#         try:
#             # data = json.loads(line)

#             if line == 'get_current_song':
#                 return 'current_song', self.app.player.is_playing, self.app.current_title_string
#             elif line == 'play_pause':
#                 def action():
#                     if self.app.player.is_playing:
#                         self.app._on_pause_clicked()
#                     else:
#                         self.app._on_play_clicked()
#                 Gdk.threads_add_idle(0, action)
#             elif line == 'play_random':
#                 Gdk.threads_add_idle(0, self.app._on_random_clicked)
#             else:
#                 print 'Unknown command:', line
#         except Exception as e:
#             print e.message
#             return

#     def broadcast(self, *args):
#         for sock in self.sockets:
#             if sock != self.sock:
#                 print 'Sending', args, 'to', sock
#                 try:
#                     sock.send(self._serialize(args))
#                 except:
#                     print 'Write failed'

#     def _serialize(self, payload):
#         return ':::'.join(map(unicode, [
#             (int(x) if isinstance(x, bool) else x)
#             for x
#             in payload
#         ])).encode('utf-8') + '\n'

#     def stop(self):
#         self.running = False
