from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime
import ssl
import traceback
import threading
import json
import socket

class webHook(threading.Thread):
    class ReqHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                self.send_response(200)
                self.end_headers()
                if self.path == '/'+self.token:
                    data = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')
                    data = json.loads(data) 
                    print(data)
                    self.q.put(data)
            except Exception as e:
                print(e, datetime.datetime.now())
                traceback.print_exc()

        def do_POST(self):
            self.do_GET()

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        """MixIn for HTTPServer for threading."""

    def __init__(self, conf, q):
        threading.Thread.__init__(self)
        self.ReqHandler.token = conf['bot']['token']
        self.ReqHandler.q = q
        httpd = self.ThreadedHTTPServer(('0.0.0.0', 8443), self.ReqHandler)
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=conf['web']['cert'], server_side=True)
        self.httpd = httpd

    def run(self):
        self.httpd.serve_forever()

