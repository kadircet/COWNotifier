from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
import traceback
import threading
import json

class webHook(threading.Thread):
    class ReqHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            if self.path == '/'+self.token:
                data = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')
                data = json.loads(data) 
                self.q.put(data)

        def do_POST(self):
            self.do_GET()

        def log_message(self, fmt, *args):
            return

    def __init__(self, conf, q):
        threading.Thread.__init__(self)
        self.ReqHandler.token = conf['bot']['token']
        self.ReqHandler.q = q
        httpd = HTTPServer(('0.0.0.0', 8443), self.ReqHandler)
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=conf['web']['cert'], server_side=True)
        self.httpd = httpd

    def run(self):
        self.httpd.serve_forever()

