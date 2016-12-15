import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Keybinder', '3.0')
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, Keybinder
from settings import Settings
from login import get_token
from api import VKApi, ITunesApi
from messaging import MessagingBus
from player import Player
from threading import Thread
from random import randint
from notifications import notify
from re import sub
try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = None
import os

DIR = os.path.dirname(os.path.abspath(__file__))


Gdk.threads_init()


class App(object):
    def __init__(self):
        self.settings = Settings()
        self.vk = None
        self.itunes = ITunesApi()
        self.player = Player()
        self.ipc = MessagingBus(self)
        self.player.start()
        self.song_length = 0
        self.current_song_iter = None
        self.current_title_string = 'Idle'
        self.is_seeking = False

        self.settings.acquire()
        if not self.settings.cp.has_option('general', 'volume'):
            self.settings.cp.set('general', 'volume', '1.0')
        self.last_volume = self.settings.cp.getfloat('general', 'volume')
        self.settings.release()

        self.player.on_download_started_cb = lambda *args: Gdk.threads_add_idle(0, lambda: self._on_download_started(*args))
        self.player.on_progress_update_cb = lambda *args: Gdk.threads_add_idle(0, lambda: self._on_progress_update(*args))
        self.player.on_download_finished_cb = lambda *args: Gdk.threads_add_idle(0, lambda: self._on_download_finished(*args))

    def start(self):
        if setproctitle:
            setproctitle('vkplayer')

        self.ipc.start()
        self.ipc.broadcast('state_changed', [self.player.is_downloading, self.player.is_playing, self.current_title_string])

        self.window = Gtk.Window()
        self.window.resize(600, 400)
        self.window.set_title('VK audio player')

        self.window.set_icon_from_file(os.path.join(DIR, 'icons/icon128.png'))

        self.accels = Gtk.AccelGroup()

        self.vbox = Gtk.VBox()
        self.window.add(self.vbox)

        # self.window.modify_bg(Gtk.StateFlags.NORMAL, Gdk.color_parse('#CCCCCC'))

        self.header = Gtk.HBox()
        # self.header.override_background_color(Gtk.StateFlags.NORMAL | Gtk.StateFlags.ACTIVE | Gtk.StateFlags.INSENSITIVE, color)
        self.header_left = Gtk.HBox()
        self.header_right = Gtk.VBox()
        self.header.pack_start(self.header_left, False, True, 0)
        self.header.pack_start(self.header_right, True, True, 0)
        self.vbox.pack_start(self.header, False, True, 0)

        self.controls = Gtk.HBox(spacing=8)
        self.controls.set_border_width(8)
        self.header_right.pack_start(self.controls, False, True, 0)

        img = Gtk.Image()
        img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.join(DIR, 'icons/icon-play-128.png'),
            width=48, height=48,
            preserve_aspect_ratio=False
        ))

        self.play = Gtk.Button('', image=img)
        self.play.set_always_show_image(True)
        self.play.set_relief(Gtk.ReliefStyle.NONE)
        self.play.connect('clicked', self._on_play_clicked)
        self.controls.pack_start(self.play, False, True, 0)

        img = Gtk.Image()
        img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.join(DIR, 'icons/icon-pause-128.png'),
            width=48, height=48,
            preserve_aspect_ratio=False
        ))

        self.pause = Gtk.Button('', image=img)
        self.pause.set_always_show_image(True)
        self.pause.set_relief(Gtk.ReliefStyle.NONE)
        self.pause.connect('clicked', self._on_pause_clicked)
        self.controls.pack_start(self.pause, False, True, 0)

        img = Gtk.Image()
        img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.join(DIR, 'icons/icon-shuffle-128.png'),
            width=48, height=48,
            preserve_aspect_ratio=False
        ))

        self.random = Gtk.Button('', image=img)
        self.random.set_always_show_image(True)
        self.random.set_relief(Gtk.ReliefStyle.NONE)
        self.random.connect('clicked', self._on_random_clicked)
        self.controls.pack_start(self.random, False, True, 0)

        self.controls.pack_start(Gtk.HSeparator(), False, True, 0)

        self.cover = Gtk.Image()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.join(DIR, 'icons/cover512.jpg'),
            width=144, height=144,
            preserve_aspect_ratio=False
        )
        self.cover.set_from_pixbuf(pixbuf)
        # self.cover.connect('clicked', self._on_random_clicked)
        self.cover.set_size_request(144, 144)
        self.header_left.pack_start(self.cover, False, True, 0)

        self.seek_panel = Gtk.VBox()
        self.controls.pack_start(self.seek_panel, True, True, 0)

        self.seek_labels = Gtk.HBox()
        self.seek_panel.pack_start(self.seek_labels, True, True, 10)

        self.track_title = Gtk.Label('', halign=Gtk.Align.START, valign=Gtk.Align.END)
        self.track_title.set_use_markup(True)
        self.track_title.set_markup('<span font="Roboto 24" weight="300">Idle</span>')
        self.seek_labels.pack_start(self.track_title, True, True, 0)

        self.track_time = Gtk.Label('05:00', halign=Gtk.Align.END, valign=Gtk.Align.END)
        self.track_time.set_use_markup(True)
        self.track_time.set_markup('<span font="Roboto 24" weight="100">05:00</span>')
        self.seek_labels.pack_start(self.track_time, True, True, 0)

        self.seek_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(0, 0, 1, 1, 0, 0))

        self.seek_bar.set_draw_value(False)
        self.seek_bar.set_sensitive(False)
        self.seek_panel.pack_start(self.seek_bar, True, True, 0)

        self.seek_bar.connect('button-press-event', self._on_seek_start)
        self.seek_bar.connect('button-release-event', self._on_seek_end)

        self.precache_progress = Gtk.ProgressBar()
        self.seek_panel.pack_start(self.precache_progress, True, True, 0)

        self.volume_scale = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=Gtk.Adjustment(1, 0, 1, 0.05, 0.05, 0.05), valign=Gtk.Align.CENTER)
        self.volume_scale.set_inverted(True)
        self.volume_scale.connect('value_changed', lambda *args: self.player.set_volume(self.volume_scale.get_value()))
        self.volume_scale.set_draw_value(False)
        self.volume_scale.set_size_request(-1, 64)
        self.volume_scale.set_value(self.last_volume)
        self.controls.pack_start(self.volume_scale, False, True, 0)

        # self.vbox.pack_start(Gtk.VSeparator(), False, True, 0)

        #

        self.search_panel = Gtk.HBox(spacing=8)
        self.search_panel.set_border_width(8)
        self.header_right.pack_start(self.search_panel, False, True, 0)

        self.refresh = Gtk.Button('My audio')
        self.refresh.connect('clicked', self._on_refresh_clicked)
        accelerator = '<Ctrl>m'
        key, mod = Gtk.accelerator_parse(accelerator)
        self.refresh.add_accelerator('activate', self.accels, key, mod, Gtk.AccelFlags.VISIBLE)
        self.search_panel.pack_start(self.refresh, False, True, 0)

        self.search_panel.pack_start(Gtk.HSeparator(), False, True, 0)

        self.query = Gtk.Entry(placeholder_text='Search music')
        self.query.connect('activate', self._on_search_clicked)
        accelerator = '<Ctrl>f'
        key, mod = Gtk.accelerator_parse(accelerator)
        self.query.add_accelerator('grab-focus', self.accels, key, mod, Gtk.AccelFlags.VISIBLE)
        self.search_panel.pack_start(self.query, True, True, 0)

        self.search = Gtk.Button('Search')
        self.search.connect('clicked', self._on_search_clicked)
        self.search_panel.pack_start(self.search, False, True, 0)

        #

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        self.vbox.pack_start(self.scroll, True, True, 0)

        self.spinner = Gtk.Spinner()
        self.vbox.pack_start(self.spinner, True, False, 0)

        self.playlist = Gtk.TreeView()
        self.scroll.add(self.playlist)

        self.playlist.connect('row-activated', self._on_row_activated)

        self.playlist_store = Gtk.ListStore(str, str, str, str, int, int, int, bool)
        self.playlist.set_model(self.playlist_store)

        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_MEDIA_PLAY, 32)

        col = Gtk.TreeViewColumn("", Gtk.CellRendererPixbuf(icon_name='media-playback-start'), visible=7)
        col.set_expand(False)
        self.playlist.append_column(col)

        col = Gtk.TreeViewColumn("Artist", Gtk.CellRendererText(ellipsize=True, family='Roboto, DejaVu Sans', weight=500), text=1)
        # col.set_expand(True)
        col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col.set_fixed_width(250)
        self.playlist.append_column(col)

        col = Gtk.TreeViewColumn("Title", Gtk.CellRendererText(ellipsize=True, family='Roboto, DejaVu Sans'), text=0)
        col.set_expand(True)
        self.playlist.append_column(col)

        col = Gtk.TreeViewColumn("Duration", Gtk.CellRendererText(), text=2)
        col.set_expand(False)
        self.playlist.append_column(col)

        self.vbox.show_all()
        self.window.add_accel_group(self.accels)
        self.window.maximize()
        self.window.show_all()

        seek_height = max(self.seek_bar.get_allocation().height, self.precache_progress.get_allocation().height)
        self.seek_bar.set_size_request(-1, seek_height)
        self.precache_progress.set_size_request(-1, seek_height)

        self.window.connect('delete-event', self._show_or_hide)

        get_token(self.window, self._on_token_ready)

        self.set_busy(False)

        self._update()

        self._on_download_finished()

        Keybinder.init()
        Keybinder.bind('<Ctrl><Alt>Return', self._on_random_clicked)
        Keybinder.bind('<Ctrl><Alt>Backspace', lambda *args: (self._on_pause_clicked if self.player.is_playing else self._on_play_clicked)())
        Keybinder.bind('XF86AudioPlay', self._on_play_clicked)
        Keybinder.bind('XF86AudioPause', self._on_pause_clicked)
        Keybinder.bind('XF86AudioNext', self._on_random_clicked)

        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_from_file(os.path.join(DIR, 'icons/play.png'))
        self.status_icon.connect('popup-menu', self._on_popup_menu)
        self.status_icon.connect('activate', self._show_or_hide)

        Gtk.main()
        self.player.stop()

    def _on_popup_menu(self, icon, button, time):
        menu = Gtk.Menu()

        show = Gtk.ImageMenuItem()
        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_ADD, Gtk.IconSize.MENU)
        show.set_image(img)
        show.set_label("Show/hide player")
        quit = Gtk.ImageMenuItem()
        img = Gtk.Image()
        img.set_from_stock(Gtk.STOCK_QUIT, Gtk.IconSize.MENU)
        quit.set_image(img)
        quit.set_label("Quit")

        show.connect("activate", self._show_or_hide)
        quit.connect("activate", self.quit)

        menu.append(show)
        menu.append(quit)

        menu.show_all()

        menu.popup(None, None, None, self.status_icon, button, time)

    def _show_or_hide(self, *args):
        if self.window.get_property('visible'):
            self.window.hide()
        else:
            self.window.show()
        return True

    def _start_login_force(self):
        get_token(self.window, self._on_token_ready, True)

    def _on_token_ready(self, access_token):
        def cb(success):
            if not success:
                return self._start_login_force()
            else:
                self.refresh.set_label(u' '.join(self.vk.data[key] for key in ('first_name', 'last_name')))
                self._on_refresh_clicked()

        self.vk = VKApi(access_token)
        self.vk.load_my_info(lambda success: Gdk.threads_add_idle(0, lambda: cb(success)))

    def _refresh(self):
        def cb(data):
            self.ipc.broadcast('state_changed', [self.player.is_downloading, self.player.is_playing, self.current_title_string])
            if 'error' in data.keys():
                return self._start_login_force()
            Gdk.threads_add_idle(0, lambda: self._populate_playlist(data['response']))

        self.vk.audio_get(cb)

    def _populate_playlist(self, songs):
        self.set_busy(False)
        self.playlist_store.clear()
        for song in songs:
            song_duration = '%02d:%02d' % (
                song['duration'] / 60,
                song['duration'] % 60
            )
            self.playlist_store.append((song['title'], song['artist'], song_duration, song['url'], song['duration'], song['owner_id'], song['aid'], False))

    def _on_refresh_clicked(self, *args):
        self.ipc.broadcast('state_changed', [True, False, 'Refreshing...'])
        self.set_busy(True)
        Thread(target=self._refresh).start()

    def _on_play_clicked(self, *args):
        if self.player.is_downloading:
            return
        self.player.play()
        self.ipc.broadcast('state_changed', [self.player.is_downloading, self.player.is_playing, self.current_title_string])

    def _on_pause_clicked(self, *args):
        if self.player.is_downloading:
            return
        self.player.pause()
        self.ipc.broadcast('state_changed', [self.player.is_downloading, self.player.is_playing, self.current_title_string])

    def _on_random_clicked(self, *args):
        model = self.playlist.get_model()
        id_ = randint(0, len(model) - 1)
        path = Gtk.TreePath(id_)
        iter_ = model.get_iter(path)
        self._play_song_at_iter(iter_)

    def _on_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        iter_ = model.get_iter(path)
        self._play_song_at_iter(iter_)

    def _play_song_at_iter(self, iter_):
        if self.current_song_iter is not None:
            self.playlist.get_model().set_value(self.current_song_iter, 7, False)
        self.playlist.get_model().set_value(iter_, 7, True)

        self.playlist.scroll_to_cell(self.playlist.get_model().get_path(iter_))
        self.playlist.get_selection().select_iter(iter_)
        self.current_song_iter = iter_
        title, artist, duration_text, url, duration, owner_id, aid, is_playing = [self.playlist.get_model().get_value(iter_, x) for x in xrange(0, 8)]
        title_string = u'{} - {}'.format(artist.decode('utf-8'), title.decode('utf-8')).strip()
        self.current_title_string = title_string
        title_string_html = u'<b>{}</b> - {}'.format(artist.decode('utf-8'), title.decode('utf-8')).strip()
        notify('media-playback-start', 'Now playing', u'<b>{}</b> - {}'.format(artist.decode('utf-8'), title.decode('utf-8')).strip(), timeout=5000)
        # self.track_title.set_text(title_string)
        self.track_title.set_markup(u'<span font="Roboto 24" weight="300">{}</span>'.format(title_string_html))
        self.window.set_title(title_string)
        self.track_time.set_text('<span font="Roboto 24" weight="100">{}</span>'.format(duration_text))
        self.song_length = duration
        self.player.play(u'{}_{}'.format(owner_id, aid), url)
        self.seek_bar.set_adjustment(Gtk.Adjustment(0, 0, duration, 0.1, 5, 0))
        self.seek_bar.set_value(0)

        self.ipc.broadcast('state_changed', [self.player.is_downloading, self.player.is_playing, self.current_title_string])

        title_string_cleaned = sub('\s+', ' ', sub(r'\[[^\]]+\]', '', sub(r'\([^\)]+\)', '', title_string)))
        # print 'Fetching album art for', title_string_cleaned
        Thread(target=lambda: self.itunes.search(self._on_song_info_loaded, term=title_string_cleaned)).start()

    def _update(self):
        try:
            if self.current_song_iter is not None:
                progress = self.player.get_play_progress()
                if not self.is_seeking:
                    self.seek_bar.set_value(progress)

                if self.player.is_finished:
                    model = self.playlist.get_model()
                    next_iter = model.iter_next(self.current_song_iter)

                    self._play_song_at_iter(next_iter)

                self.track_time.set_markup('<span font="Roboto 24" weight="100">{}</span>'.format(
                    '%02d:%02d / %02d:%02d' % (
                        int(progress) / 60,
                        int(progress) % 60,
                        self.song_length / 60,
                        self.song_length % 60
                    )
                ))
            if self.last_volume != self.volume_scale.get_value():
                self.last_volume = self.volume_scale.get_value()
                self.settings.acquire()
                self.settings.cp.set('general', 'volume', self.last_volume)
                self.settings.release()
        except:
            raise
        finally:
            Gdk.threads_add_timeout(0, 100, self._update)

    def _on_song_info_loaded(self, data):
        if data['resultCount'] > 0:
            result = data['results'][0]
            artworkUrl = result['artworkUrl100']

            file = Gio.File.new_for_uri(artworkUrl)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                file.read(cancellable=None),
                width=144, height=144,
                preserve_aspect_ratio=False,
                cancellable=None
            )
        else:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                os.path.join(DIR, 'icons/cover512.jpg'),
                width=144, height=144,
                preserve_aspect_ratio=False
            )
        Gdk.threads_add_idle(0, lambda: self.cover.set_from_pixbuf(pixbuf))

    def _on_seek_start(self, *args):
        self.is_seeking = True

    def _on_seek_end(self, *args):
        self.player.pause()
        self.player.seek(self.seek_bar.get_value())
        self.player.play()
        self.is_seeking = False

    def _on_download_started(self):
        self.seek_bar.set_visible(False)
        self.precache_progress.set_visible(True)

    def _on_progress_update(self, read, length):
        self.precache_progress.set_fraction(float(read) / length)

    def _on_download_finished(self):
        self.player.is_downloading = False
        self.seek_bar.set_visible(True)
        self.precache_progress.set_visible(False)
        self.ipc.broadcast('state_changed', [self.player.is_downloading, self.player.is_playing, self.current_title_string])

    def set_busy(self, is_busy):
        self.spinner.set_visible(is_busy)
        self.scroll.set_visible(not is_busy)
        self.window.set_sensitive(not is_busy)
        if is_busy:
            self.spinner.start()
        else:
            self.spinner.stop()

    def _on_search_clicked(self, *args):
        self.ipc.broadcast('state_changed', [True, False, 'Searching...'])
        self.set_busy(True)
        Thread(target=self._search).start()

    def _search(self):
        def cb(data):
            self.ipc.broadcast('state_changed', [self.player.is_downloading, self.player.is_playing, self.current_title_string])
            if 'error' in data:
                return self._start_login_force()
            Gdk.threads_add_idle(0, lambda: self._populate_playlist(data['response'][1:]))
            Gdk.threads_add_idle(0, lambda: self.playlist.grab_focus())

        self.vk.audio_search(cb, q=self.query.get_text())

    def play_next(self):
        model = self.playlist.get_model()
        next_iter = model.iter_next(self.current_song_iter)

        self._play_song_at_iter(next_iter)

    def play_prev(self):
        model = self.playlist.get_model()

        prev_iter = None
        iter = model.get_iter_first()

        current_path = model.get_path(self.current_song_iter)

        while True:
            prev_iter = iter
            iter = model.iter_next(iter)
            if not iter:
                return
            if model.get_path(iter) == current_path:
                self._play_song_at_iter(prev_iter)
                return

    def quit(self, *args):
        self.ipc.stop()
        Gtk.main_quit()
