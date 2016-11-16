import os
import pyglet
from threading import Thread
import urllib2
from settings import Settings

# from pyglet.media.drivers import pulse
from pyglet.media.drivers.pulse import PulseAudioDriver

PulseAudioDriver.get_app_name = lambda self: 'VKPlayer'


# class PAProxy(object):
#     def __getattr__(self, name):
#         return getattr(pulse.pa, name)


# pulse.pa = PAProxy()

# pa.pa_stream_new = lambda *args: pa.pa_signal_new(args[0], 'Playback', args[2], args[3])
# print pa.pa_context_get_name()


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
        self.player = pyglet.media.Player()
        self.player.on_eos = self._on_eos

    def run(self):
        pyglet.app.run()

    def _on_eos(self, *args):
        self._finished = True

    def set_volume(self, value):
        if self.player:
            self.volume = value
            self.player.volume = value

    @property
    def is_finished(self):
        return self._finished

    def play(self, audio_id=None, url=None):
        if url:
            self.on_download_started_cb()
            if self.queue_thread:
                self.queue_thread.stop()
            self._reset()
            if not os.path.exists(os.path.join(Settings.get_cache_dir(), '{}.mp3'.format(audio_id))):
                self.is_downloading = True
                self.queue_thread = Downloader(audio_id, url, self.on_progress_update_cb, self._on_downloaded)
                self.queue_thread.start()
            else:
                self._on_downloaded(audio_id, None, False)
        else:
            self.player.play()
            self.player.volume = self.volume

    def _on_downloaded(self, audio_id, data, save=True):
        fname = os.path.join(Settings.get_cache_dir(), '{}.mp3'.format(audio_id))

        if save:
            file = open(fname, 'w')
            file.write(data)
            file.close()

        source = pyglet.media.load(fname)

        self.player.queue(source)
        self.player.play()
        self.player.volume = self.volume

        self.is_downloading = False
        self.on_download_finished_cb()

    def stop(self):
        pyglet.app.exit()

    def pause(self):
        self.player.pause()

    def get_play_progress(self):
        return self.player.time

    def on_download_started_cb(self):
        raise NotImplementedError()

    def on_progress_update_cb(self, read, length):
        raise NotImplementedError()

    def on_download_finished_cb(self):
        raise NotImplementedError()

    def seek(self, pos):
        self.player.seek(pos)

    @property
    def is_playing(self):
        return self.player.playing
