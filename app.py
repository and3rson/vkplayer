from gi.repository import Gtk, Gdk
# import Gtk
from login import get_token
from api import VKApi
from player import Player
from threading import Thread
from random import randint

Gdk.threads_init()


class App(object):
    def __init__(self):
        self.vk = None
        self.player = Player()
        self.player.start()
        self.song_length = 0
        self.current_song_iter = None
        self.is_seeking = False

        self.player.on_download_started = lambda *args: Gdk.threads_add_idle(0, lambda: self._on_download_started(*args))
        self.player.on_progress_update = lambda *args: Gdk.threads_add_idle(0, lambda: self._on_progress_update(*args))
        self.player.on_download_finished = lambda *args: Gdk.threads_add_idle(0, lambda: self._on_download_finished(*args))

    def start(self):
        self.window = Gtk.Window()
        self.window.resize(600, 400)
        # self.window.set_border_width(8)

        self.vbox = Gtk.VBox()
        self.window.add(self.vbox)

        self.controls = Gtk.HBox(spacing=8)
        self.controls.set_border_width(8)
        self.vbox.pack_start(self.controls, False, True, 0)

        self.play = Gtk.Button('Play')
        self.play.connect('clicked', self._on_play_clicked)
        self.controls.pack_start(self.play, False, True, 0)

        self.pause = Gtk.Button('Pause')
        self.pause.connect('clicked', self._on_pause_clicked)
        self.controls.pack_start(self.pause, False, True, 0)

        self.random = Gtk.Button('Random')
        self.random.connect('clicked', self._on_random_clicked)
        self.controls.pack_start(self.random, False, True, 0)

        self.controls.pack_start(Gtk.HSeparator(), False, True, 0)

        self.seek_panel = Gtk.VBox()
        self.controls.pack_start(self.seek_panel, True, True, 0)

        self.seek_labels = Gtk.HBox()
        self.seek_panel.pack_start(self.seek_labels, True, True, 0)

        self.track_title = Gtk.Label('Foo - Bar', halign=Gtk.Align.START, valign=Gtk.Align.END)
        self.seek_labels.pack_start(self.track_title, True, True, 0)

        self.track_time = Gtk.Label('05:00', halign=Gtk.Align.END, valign=Gtk.Align.END)
        self.seek_labels.pack_start(self.track_time, True, True, 0)

        self.seek_bar = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(0, 0, 1, 1, 0, 0))
        # self.seek_bar.set_update_policy(Gtk.Range.UPDATE_DISCONTINUOUS)
        # print self.seek_bar.set_range(0, 1, 2)
        # self.seek_bar.set_step(0.001)
        self.seek_bar.set_draw_value(False)
        self.seek_bar.set_sensitive(False)
        self.seek_panel.pack_start(self.seek_bar, True, True, 0)

        self.seek_bar.connect('button-press-event', self._on_seek_start)
        self.seek_bar.connect('button-release-event', self._on_seek_end)

        self.precache_progress = Gtk.ProgressBar()
        self.seek_panel.pack_start(self.precache_progress, True, True, 0)

        # self.vbox.pack_start(Gtk.VSeparator(), False, True, 0)

        #

        self.search_panel = Gtk.HBox(spacing=8)
        self.search_panel.set_border_width(8)
        self.vbox.pack_start(self.search_panel, False, True, 0)

        self.refresh = Gtk.Button('My audio')
        self.refresh.connect('clicked', self._on_refresh_clicked)
        self.search_panel.pack_start(self.refresh, False, True, 0)

        self.search_panel.pack_start(Gtk.HSeparator(), False, True, 0)

        self.query = Gtk.Entry(placeholder_text='Search music')
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
        col = Gtk.TreeViewColumn("Title", Gtk.CellRendererText(ellipsize=True), text=0)
        col.set_expand(True)
        self.playlist.append_column(col)
        col = Gtk.TreeViewColumn("Artist", Gtk.CellRendererText(ellipsize=True), text=1)
        col.set_expand(True)
        self.playlist.append_column(col)
        col = Gtk.TreeViewColumn("Duration", Gtk.CellRendererText(), text=2)
        col.set_expand(False)
        self.playlist.append_column(col)

        # self.playlist_store.append(('a', 'b', 'c'))
        # self.playlist_store.append(('a', 'b', 'c'))
        # self.playlist_store.append(('a', 'b', 'c'))
        # self.playlist.set_model(self.playlist_store)

        self.window.show_all()

        seek_height = max(self.seek_bar.get_allocation().height, self.precache_progress.get_allocation().height)
        self.seek_bar.set_size_request(-1, seek_height)
        self.precache_progress.set_size_request(-1, seek_height)

        def on_close(win):
            if win == self.window:
                Gtk.main_quit()

        self.window.connect('destroy', on_close)

        get_token(self.window, self._on_token_ready)

        self.set_busy(False)

        self._update()

        self._on_download_finished()

        Gtk.main()
        self.player.stop()

    def _on_token_ready(self, access_token):
        self.vk = VKApi(access_token)

    def _refresh(self):
        songs = self.vk.audio_get()['response']
        Gdk.threads_add_idle(0, lambda: self._populate_playlist(songs))

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
        self.set_busy(True)
        Thread(target=self._refresh).start()

    def _on_play_clicked(self, *args):
        self.player.play()

    def _on_pause_clicked(self, *args):
        self.player.pause()

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
        self.track_title.set_text(u'{} - {}'.format(title, artist))
        self.track_time.set_text(duration_text)
        self.song_length = duration
        self.player.play('{}_{}'.format(owner_id, aid), url)
        self.seek_bar.set_adjustment(Gtk.Adjustment(0, 0, duration, 0.1, 5, 0))
        self.seek_bar.set_value(0)

    def _update(self):
        if self.current_song_iter is not None:
            progress = self.player.get_play_progress()
            # self.seek_bar.set_fraction((progress / self.song_length) if self.song_length > 0 else 0)
            # self.seek_bar.set_adjustment()
            if not self.is_seeking:
                self.seek_bar.set_value(progress)

            if self.song_length - progress < 1:
                model = self.playlist.get_model()
                next_iter = model.iter_next(self.current_song_iter)

                self._play_song_at_iter(next_iter)

            self.track_time.set_text('%02d:%02d / %02d:%02d' % (
                int(progress) / 60,
                int(progress) % 60,
                self.song_length / 60,
                self.song_length % 60
            ))

                # self._on_row_activated(self.playlist, , None)
        Gdk.threads_add_timeout(0, 100, self._update)

    def _on_seek_start(self, *args):
        self.is_seeking = True
        # self.seek_bar

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
        self.seek_bar.set_visible(True)
        self.precache_progress.set_visible(False)

    def set_busy(self, is_busy):
        self.spinner.set_visible(is_busy)
        self.scroll.set_visible(not is_busy)
        self.window.set_sensitive(not is_busy)
        if is_busy:
            self.spinner.start()
        else:
            self.spinner.stop()

    def _on_search_clicked(self, *args):
        self.set_busy(True)
        Thread(target=self._search).start()

    def _search(self):
        songs = self.vk.audio_search(q=self.query.get_text())['response'][1:]
        Gdk.threads_add_idle(0, lambda: self._populate_playlist(songs))

    # @classmethod
    # def login_finished(access_token):
        # print 'Token:', access_token

        # def _login_finished(self, access_token):
        # start_login_process(login_finished)
