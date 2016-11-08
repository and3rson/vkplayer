from urllib import urlencode
import urllib2
import json
from threading import Thread


class BaseApi(object):
    def _request(self, method, cb, **kwargs):
        kwargs = {
            k: v.encode('utf-8') if isinstance(v, unicode) else v for k, v in kwargs.items()
        }
        response = urllib2.urlopen(self.BASE_URL.format(
            method=method,
            query=urlencode(kwargs)
        ))
        cb(json.loads(response.read()))


class VKApi(BaseApi):
    BASE_URL = 'https://api.vk.com/method/{method}?{query}'

    def __init__(self, access_token):
        self.access_token = access_token
        self.data = None

    def api_method(method):
        def wrapper(self, cb, **kwargs):
            kwargs.update(dict(access_token=self.access_token))

            Thread(target=self._request, args=(method, cb), kwargs=kwargs).start()
        return wrapper

    def _set_my_data(self, data):
        self.data = data
        print 'My data:', data

    audio_get = api_method('audio.get')
    audio_search = api_method('audio.search')
    users_get = api_method('users.get')
    audio_add = api_method('audio.add')

    def load_my_info(self, cb):
        def inner_cb(data):
            if 'error' in data.keys():
                cb(False)
            else:
                self._set_my_data(data['response'][0])
                cb(True)
            pass
        self.users_get(inner_cb)

    def audio_add_to_my_page(self, cb, audio_id):
        self.audio_add(cb, owner_id=self.data['uid'], audio_id=audio_id)


class ITunesApi(BaseApi):
    BASE_URL = 'https://itunes.apple.com/{method}?{query}'

    def search(self, cb, term):
        return self._request('search', cb, term=term)
