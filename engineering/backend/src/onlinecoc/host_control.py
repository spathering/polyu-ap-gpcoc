"""Host-local control, explicitly separate from room and browser authentication."""
import base64
import ctypes
import json
import os
from pathlib import Path
import secrets
from .errors import require


def protect(raw, decrypt=False):
    # Windows DPAPI CurrentUser: no portable bearer secret in the discovery file.
    require(os.name == 'nt', 'HOST_CONTROL_WINDOWS_REQUIRED')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buf = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise OSError('HOST_CONTROL_PROTECTION_FAILED: '+str(ctypes.windll.kernel32.GetLastError()))
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free(ctypes.cast(target.data, ctypes.c_void_p))


class HostControl:
    def __init__(self, host, port, directory=None):
        self.active = False
        self.host = host
        self.url = f'http://127.0.0.1:{port}'
        self.key = secrets.token_urlsafe(48)
        self.instance = secrets.token_hex(16)
        self.directory = Path(directory) if directory else Path(os.environ['LOCALAPPDATA'])/'OnlineCOC/HostControl'
        self.file = self.directory/(self.instance+'.json')

    def publish(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        record = {'version': 1, 'instanceId': self.instance, 'pid': os.getpid(),
                  'url': self.url, 'dataDirectory': str(self.host.path.resolve()),
                  'protectedKey': base64.b64encode(protect(self.key.encode())).decode()}
        # Create a fresh name; interrupted writes are ignored by the tool.
        with self.file.open('x', encoding='utf-8') as out:
            json.dump(record, out, ensure_ascii=False)
        self.active = True

    def close(self):
        self.active = False
        self.file.unlink(missing_ok=True)

    def authorize(self, request):
        require(self.active, 'PERMISSION_DENIED')
        require(request.client and request.client.host in ('127.0.0.1', '::1'), 'PERMISSION_DENIED')
        require('origin' not in request.headers and 'referer' not in request.headers, 'PERMISSION_DENIED')
        require(request.headers.get('x-onlinecoc-instance') == self.instance, 'PERMISSION_DENIED')
        require(secrets.compare_digest(request.headers.get('x-onlinecoc-host-key', ''), self.key), 'PERMISSION_DENIED')

    def accounts(self):
        with self.host.lock:
            members = self.host.state()['members']
            accounts = self.host.identity.store.snapshot()[1]['accounts']
            return {'instanceId': self.instance, 'pid': os.getpid(), 'dataDirectory': str(self.host.path.resolve()),
                    'items': [{**{k:a[k] for k in ('accountId','loginName','nickname','disabled')},
                               'roomRole': members.get(a['accountId'], {}).get('role')}
                              for a in sorted(accounts.values(), key=lambda a:a['loginName'])]}
