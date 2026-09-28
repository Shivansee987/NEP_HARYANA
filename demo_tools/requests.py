"""Minimal stand-in for the `requests` API used by seed_demo.py (stdlib only, so no extra install)."""
import json as _json
import urllib.error
import urllib.request
import uuid


class Response:
    def __init__(self, code, data):
        self.status_code, self.content = code, data
        self.text = data.decode("utf-8", "replace")

    def json(self):
        return _json.loads(self.text)


class Session:
    def __init__(self):
        self.headers = {}

    def request(self, method, url, json=None, data=None, files=None):
        headers = dict(self.headers)
        body = None
        if files:
            b = uuid.uuid4().hex
            parts = []
            for k, v in (data or {}).items():
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            for k, (name, content, ctype) in files.items():
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + content + b"\r\n")
            body = b"".join(parts) + f"--{b}--\r\n".encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={b}"
        elif json is not None or method in ("POST", "PUT", "PATCH"):
            body = _json.dumps(json if json is not None else {}).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as r:
                return Response(r.status, r.read())
        except urllib.error.HTTPError as e:
            return Response(e.code, e.read())
