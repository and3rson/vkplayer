import os
import pyglet
from threading import Thread
import urllib2


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

        self.queue_thread = None
        self._finished = False
        self.player = None
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

    @property
    def is_finished(self):
        return self._finished

    def play(self, audio_id=None, url=None):
        if url:
            self.on_download_started()
            if self.queue_thread:
                self.queue_thread.stop()
            self._reset()
            if not os.path.exists('./music/{}.mp3'.format(audio_id)):
                self.queue_thread = Downloader(audio_id, url, self.on_progress_update, self._on_downloaded)
                self.queue_thread.start()
            else:
                self._on_downloaded(audio_id, None, False)
        else:
            self.player.play()

    def _on_downloaded(self, audio_id, data, save=True):
        if not os.path.exists('./music'):
            os.mkdir('./music')

        fname = './music/{}.mp3'.format(audio_id)

        if save:
            file = open(fname, 'w')
            file.write(data)
            file.close()

        source = pyglet.media.load(fname)

        self.player.queue(source)
        self.player.play()

        self.on_download_finished()

    def stop(self):
        pyglet.app.exit()

    def pause(self):
        self.player.pause()

    def get_play_progress(self):
        return self.player.time

    def seek(self, pos):
        self.player.seek(pos)

    def on_download_started(self):
        pass

    def on_progress_update(self, read, length):
        pass

    def on_download_finished(self):
        pass
