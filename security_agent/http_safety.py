"""Bounded HTTP workers and strict, deadline-limited JSON framing."""
import json
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class HTTPBodyError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


class _DeadlineHeaders:
    def __init__(self, source, connection, deadline):
        self.source, self.connection, self.deadline = source, connection, deadline

    def readline(self, limit=-1):
        chunks=[]
        while limit<0 or len(chunks)<limit:
            remaining=self.deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Header deadline exceeded')
            self.connection.settimeout(remaining)
            byte=self.source.read1(1)
            if not byte:break
            chunks.append(byte)
            if byte==b'\n':break
        return b''.join(chunks)


def body_length(headers):
    lengths = headers.get_all('Content-Length', [])
    if headers.get_all('Transfer-Encoding', []) or len(lengths) > 1:
        raise HTTPBodyError(400, 'INVALID_BODY_FRAMING')
    value = lengths[0].strip() if lengths else '0'
    if len(value) > 9 or not re.fullmatch(r'[0-9]+', value):
        raise HTTPBodyError(400, 'INVALID_CONTENT_LENGTH')
    return int(value)


def read_json_body(handler, limit):
    length = body_length(handler.headers)
    if length > limit:
        raise HTTPBodyError(413, 'REQUEST_TOO_LARGE')
    deadline = time.monotonic() + getattr(handler.server, 'request_timeout', 3.0)
    chunks, remaining = [], length
    try:
        while remaining:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                raise HTTPBodyError(408, 'REQUEST_TIMEOUT')
            handler.connection.settimeout(timeout)
            chunk = handler.rfile.read1(min(remaining, 8192))
            if not chunk:
                raise HTTPBodyError(400, 'INCOMPLETE_BODY')
            chunks.append(chunk)
            remaining -= len(chunk)
        obj = json.loads(b''.join(chunks) if length else b'{}')
        if not isinstance(obj, dict):
            raise ValueError('object required')
        return obj
    except (TimeoutError, socket.timeout):
        raise HTTPBodyError(408, 'REQUEST_TIMEOUT') from None
    except (ValueError, UnicodeError):
        raise HTTPBodyError(400, 'INVALID_JSON') from None
    finally:
        handler.connection.settimeout(getattr(handler.server, 'request_timeout', 3.0))


class SafeHTTPHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(getattr(self.server, 'request_timeout', 3.0))
        super().setup()

    def body_error(self, error):
        self.close_connection = True
        raw = json.dumps({'error': error.code}).encode()
        self.send_response(error.status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(raw)

    def parse_request(self):
        if not super().parse_request():
            return False
        if isinstance(self.rfile,_DeadlineHeaders):self.rfile=self.rfile.source
        try:
            body_length(self.headers)
        except HTTPBodyError as error:
            self.body_error(error)
            return False
        return True

    def handle_one_request(self):
        original=self.rfile
        self.rfile=_DeadlineHeaders(original,self.connection,time.monotonic()+getattr(self.server,'request_timeout',3.0))
        try:
            super().handle_one_request()
        except HTTPBodyError as error:
            self.body_error(error)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
            self.close_connection = True
        finally:
            self.rfile=original


class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, address, handler, *, max_connections=32, request_timeout=3.0):
        self.request_timeout = request_timeout
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            try:
                request.settimeout(.2)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n')
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()
