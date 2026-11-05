"""Public HTTP protocol client, used by pack tools and black-box tests."""
import http.cookiejar
import json
import urllib.error
import urllib.request
import uuid


class HostError(RuntimeError):
    def __init__(self, response):
        self.response = response
        super().__init__(str(response))


class Client:
    def __init__(self, base, name, password):
        self.base, self.csrf = base.rstrip('/'), None
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = self.request('/login', {'loginName': name, 'password': password})['csrf']

    def request(self, path, body=None):
        headers = {'Origin': self.base, 'Content-Type': 'application/json'}
        if self.csrf:
            headers['X-CSRF-Token'] = self.csrf
        req = urllib.request.Request(self.base + '/api/v1' + path,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers=headers)
        try:
            with self.opener.open(req, timeout=25) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise HostError({'httpStatus': e.code, **json.loads(e.read())}) from e

    def envelope(self, op, args):
        view = self.request('/view')
        return {'protocolVersion': 1, 'type': 'command', 'requestId': str(uuid.uuid4()),
                'roomId': view['roomId'], 'payload': {
                    'commandId': str(uuid.uuid4()), 'authorityEpoch': view['authorityEpoch'],
                    'runId': view['runId'], 'catalogRevision': view['catalog']['revision'],
                    'rulesetRevision': view['catalog']['rulesetRevision'],
                    'expectedViews': {}, 'op': op, 'args': args}}

    def send(self, envelope):
        receipt = self.request('/commands', envelope)
        if receipt['status'] != 'committed':
            raise HostError(receipt)
        return receipt

    def command(self, op, args):
        return self.send(self.envelope(op, args))['result']

    def invoke(self, action, **inputs):
        return self.command('action.invoke', {'actionId': action, 'input': inputs})
