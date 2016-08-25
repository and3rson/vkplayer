from urlparse import urlparse, parse_qs
from gi.repository import Gtk, WebKit


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

    wk.open('https://oauth.vk.com/authorize?client_id=5604598&response_type=token&scope=friends,audio&display=mobile')

    def login_succeeded(webview, frame):
        if frame.get_uri().startswith('https://oauth.vk.com/blank.html'):
            info = urlparse(frame.get_uri())
            access_token = parse_qs(info.fragment).get('access_token')[0]
            callback(access_token)
            win.hide()

    wk.connect('load-finished', login_succeeded)


def get_token(window, callback):
    try:
        f = open('/tmp/vk_access_token', 'r')
    except:
        def _callback(access_token):
            f = open('/tmp/vk_access_token', 'w')
            f.write(access_token)
            f.close()
            callback(access_token)
        _start_login_process(window, _callback)
    else:
        access_token = f.read().strip()
        f.close()
        callback(access_token)
