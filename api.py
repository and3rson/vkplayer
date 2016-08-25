from urllib import urlencode
import urllib2
import json


class VKApi(object):
    BASE_URL = 'https://api.vk.com/method/{method}?{query}'

    def _request(self, method, **kwargs):
        response = urllib2.urlopen(VKApi.BASE_URL.format(
            method=method,
            query=urlencode(kwargs)
        ))
        return json.loads(response.read())

    def __init__(self, access_token):
        self.access_token = access_token

    def api_method(fn):
        def wrapper(self, **kwargs):
            kwargs.update(dict(access_token=self.access_token))
            return self._request(fn.__name__.replace('_', '.'), **kwargs)
        return wrapper

    @api_method
    def audio_get(self, **kwargs):
        pass

    @api_method
    def audio_search(self, **kwargs):
        pass
