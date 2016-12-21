import os
import vlc
from threading import Thread
import urllib2
from settings import Settings


class Downloader(Thread):
    def __init__(self, audio_id, url, progress_callback, result_callback):
        super(Downloader, self).__init__()

        self.audio_id = audio_id

        self.url = url
        self.progress_callback = progress_callback
        self.result_callback = result_callback
        self.daemon = True
        self.alive = True

    def stop(self):
        self.alive = False

    def run(self):
        response = urllib2.urlopen(self.url)
        length = response.headers.get('Content-Length')
        data = []
        read = 0
        while True:
            if not self.alive:
                return
            chunk = response.read(65536)
            read += len(chunk)
            if chunk:
                data.append(chunk)
                self.progress_callback(read, int(length))
            else:
                break

        data = ''.join(data)

        if not self.alive:
            return

        self.result_callback(self.audio_id, data)


class Player(Thread):
    def __init__(self):
        super(Player, self).__init__()

        self.is_downloading = False
        self.queue_thread = None
        self._finished = False
        self.player = None
        self.volume = 1
        self._reset()

    def _reset(self):
        if self.player:
            self.player.pause()
            self.player.delete()
            del self.player
        self._finished = False
        self.player = vlc.MediaPlayer()
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerPlaying, self._on_media_state_changed)
        self.player.event_manager().event_attach(vlc.EventType.MediaPlayerPaused, self._on_media_state_changed)
        # self.player.on_eos = self._on_eos

    # def attach_on_eos(self):
    #     self.player.event_manager().event_attach(vlc.EventType.MediaListEndReached, self._on_eos)

    # def detach_on_eos(self):
    #     self.player.event_manager().event_detach(vlc.EventType.MediaListEndReached)

    def run(self):
        pass
        # pyglet.app.run()

    def _on_eos(self, *args):
        # self.detach_on_eos()
        self._finished = True

    def _on_media_state_changed(self, e):
        self.on_media_state_changed()

    def set_volume(self, value):
        if self.player:
            self.volume = value
            self.player.audio_set_volume(int(value * 100))

    @property
    def is_finished(self):
        return self.player.get_position() >= 0.999

    def play(self, audio_id=None, url=None):
        print 'Playing', url
        if url:
            self.player.set_media(vlc.Media(url))
            self.player.play()
            # self.attach_on_eos()
            # self.on_download_started_cb()
            # if self.queue_thread:
            #     self.queue_thread.stop()
            # self._reset()
            # if not os.path.exists(os.path.join(Settings.get_cache_dir(), '{}.mp3'.format(audio_id))):
            #     self.is_downloading = True
            #     self.queue_thread = Downloader(audio_id, url, self.on_progress_update_cb, self._on_downloaded)
            #     self.queue_thread.start()
            # else:
            #     self._on_downloaded(audio_id, None, False)
        else:
            self.player.play()
            self.player.volume = self.volume

    def _on_downloaded(self, audio_id, data, save=True):
        raise AssertionError()
        fname = os.path.join(Settings.get_cache_dir(), '{}.mp3'.format(audio_id))

        if save:
            file = open(fname, 'w')
            file.write(data)
            file.close()

        # source = pyglet.media.load(fname)
        source = vlc.Media(fname)

        self.player.queue(source)
        self.player.play()
        self.player.volume = self.volume

        self.is_downloading = False
        self.on_download_finished_cb()

    def stop(self):
        pass
        # raise AssertionError()
        # pyglet.app.exit()

    def pause(self):
        self.player.pause()

    def get_play_progress(self):
        return self.player.get_position()

    def get_play_progress_seconds(self):
        return int(self.player.get_position() * self.player.get_length() / 1000)

    def on_download_started_cb(self):
        raise NotImplementedError()

    def on_progress_update_cb(self, read, length):
        raise NotImplementedError()

    def on_download_finished_cb(self):
        raise NotImplementedError()

    def on_media_state_changed(self):
        raise NotImplementedError()

    def seek(self, pos):
        self.player.set_position(pos)

    @property
    def is_playing(self):
        return self.player.get_state() == vlc.State.Playing
