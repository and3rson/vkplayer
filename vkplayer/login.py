from gi.repository import Gtk, WebKit
from urlparse import urlparse, parse_qs
from settings import Settings


def _start_login_process(window, callback):
    sw = Gtk.ScrolledWindow()

    wk = WebKit.WebView()
    sw.add(wk)

    win = Gtk.Window()
    win.resize(400, 400)
    win.add(sw)
    win.set_modal(True)
    win.set_transient_for(window)
    win.show_all()

    wk.open('https://oauth.vk.com/authorize?client_id=3682744&response_type=token&scope=friends,audio,offline,a&display=mobile')

    def login_succeeded(webview, frame):
        if frame.get_uri().startswith('https://oauth.vk.com/blank.html'):
            info = urlparse(frame.get_uri())
            access_token = parse_qs(info.fragment).get('access_token')[0]
            callback(access_token)
            win.hide()

    wk.connect('load-finished', login_succeeded)


def get_token(window, callback, force=False):
    settings = Settings()
    settings.acquire()
    has_token = settings.cp.has_option('vk', 'access_token')
    settings.release()

    if force or not has_token:
        def _callback(access_token):
            settings.acquire()
            settings.cp.set('vk', 'access_token', access_token)
            settings.release()
            callback(access_token)
        _start_login_process(window, _callback)
    else:
        callback(settings.cp.get('vk', 'access_token'))
