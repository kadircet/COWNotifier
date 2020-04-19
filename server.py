from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime
import ssl
import traceback
import threading
import json
import socket
from logger import getLogger

logger = getLogger(__name__)


class webHook(threading.Thread):

  class ReqHandler(BaseHTTPRequestHandler):

    def do_GET(self):
      try:
        self.send_response(200)
        self.end_headers()
        if self.path == '/' + self.token:
          data = self.rfile.read(int(
              self.headers['Content-Length'])).decode('utf-8')
          data = json.loads(data)
          logger.info('Received {}', data)
          self.q.put(data)
      except Exception as e:
        logger.error('{} {}', e, datetime.datetime.now())
        traceback.print_exc()

    def do_POST(self):
      self.do_GET()

  class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):

    def get_request(self):
      newsock, addr = self.socket.accept()
      newsock = ssl.wrap_socket(
          newsock,
          certfile=self.certfile,
          do_handshake_on_connect=False,
          server_side=True)
      timeout = newsock.gettimeout()
      newsock.settimeout(2.)
      newsock.do_handshake()
      newsock.settimeout(timeout)
      return newsock, addr

  def __init__(self, conf, q):
    threading.Thread.__init__(self)
    self.ReqHandler.token = conf['bot']['token']
    self.ReqHandler.q = q
    httpd = self.ThreadedHTTPServer(('0.0.0.0', 8443), self.ReqHandler)
    httpd.certfile = conf['web']['cert']
    self.httpd = httpd

  def run(self):
    self.httpd.serve_forever()
