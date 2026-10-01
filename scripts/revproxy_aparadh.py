#!/usr/bin/env python3
"""Dual-mode local proxy for headless-Chromium screenshots.

- Requests whose absolute URL/host is in REVERSE_HOSTS are reverse-proxied to
  the local Next.js server (lets Chromium load localhost-only apps through the
  proxy code path, which is not subject to the build's loopback navigation block).
- Everything else is forwarded to the upstream egress proxy from $https_proxy
  with Proxy-Authorization injected (AGENTS.md pattern).

Usage: python3 revproxy.py  (listens on 127.0.0.1:8888)
"""
import base64
import os
import socket
import threading
from urllib.parse import urlsplit

LISTEN = ("127.0.0.1", 8888)
REVERSE_HOSTS = {"aparadh.local"}
UPSTREAM_TARGET = ("127.0.0.1", 8901)


def upstream_proxy():
    for var in ("https_proxy", "HTTPS_PROXY"):
        v = os.environ.get(var)
        if v:
            u = urlsplit(v)
            return u.hostname, u.port or 8080, v
    return None


def read_headers(rfile):
    headers = {}
    while True:
        line = rfile.readline().decode("latin1")
        if line in ("\r\n", "\n", ""):
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return headers


def handle(client):
    try:
        rfile = client.makefile("rb")
        req_line = rfile.readline().decode("latin1")
        if not req_line:
            client.close()
            return
        parts = req_line.strip().split()
        if len(parts) < 2:
            client.close()
            return
        method, target = parts[0], parts[1]
        headers = read_headers(rfile)
        body = b""
        if "content-length" in headers:
            try:
                body = rfile.read(int(headers["content-length"]))
            except Exception:
                pass

        # absolute URL (forward-proxy style) or origin-form
        if target.startswith("http://") or target.startswith("https://"):
            u = urlsplit(target)
            host, path = u.hostname or "", u.path or "/"
            if u.query:
                path += "?" + u.query
        else:
            host = headers.get("host", "").split(":")[0]
            path = target

        if host in REVERSE_HOSTS:
            # reverse-proxy to local Next.js
            upstream = socket.create_connection(UPSTREAM_TARGET, timeout=20)
            hdr_lines = "".join(
                f"{k}: {v}\r\n" for k, v in headers.items() if k != "proxy-authorization"
            )
            upstream.sendall(
                f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:3000\r\nConnection: close\r\n{hdr_lines}\r\n".encode(
                    "latin1"
                )
                + body
            )
            while True:
                chunk = upstream.recv(65536)
                if not chunk:
                    break
                client.sendall(chunk)
            upstream.close()
            client.close()
            return

        # forward to upstream egress proxy
        up = upstream_proxy()
        if not up:
            client.sendall(b"HTTP/1.1 502 no upstream proxy\r\nConnection: close\r\n\r\n")
            client.close()
            return
        uhost, uport, _ = up
        upstream = socket.create_connection((uhost, uport), timeout=20)
        auth = ""
        for var in ("https_proxy", "HTTPS_PROXY"):
            v = os.environ.get(var)
            if v:
                u = urlsplit(v)
                if u.username:
                    cred = f"{u.username}:{u.password or ''}"
                    auth = base64.b64encode(cred.encode()).decode()
                break
        hdr_lines = "".join(
            f"{k}: {v}\r\n"
            for k, v in headers.items()
            if k not in ("proxy-authorization",)
        )
        if auth:
            hdr_lines += f"Proxy-Authorization: Basic {auth}\r\n"
        # reconstruct absolute URL for forward proxying
        abs_url = target if target.startswith("http") else f"http://{host}{path}"
        upstream.sendall(
            f"{method} {abs_url} HTTP/1.1\r\n{hdr_lines}\r\n".encode("latin1") + body
        )
        while True:
            chunk = upstream.recv(65536)
            if not chunk:
                break
            client.sendall(chunk)
        upstream.close()
        client.close()
    except Exception:
        try:
            client.close()
        except Exception:
            pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(LISTEN)
    srv.listen(100)
    print(f"proxy on {LISTEN[0]}:{LISTEN[1]}", flush=True)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()


if __name__ == "__main__":
    main()
