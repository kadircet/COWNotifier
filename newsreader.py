from nntplib import NNTP_SSL
import traceback
import threading
import time
import datetime
import html
import json
from newsparser import newsArticle


class newsReader:
    def __init__(self, host, port, uname, pw, lfile):
        self.conparams = [host, port, uname, pw]
        self.lfile = lfile
        self.initialized = False
        self.initConnection()

    def initConnection(self):
        self.conn = NNTP_SSL(self.conparams[0], self.conparams[1],
                             self.conparams[2], self.conparams[3])
        self.time = time.time()
        last = {}
        try:
            with open(self.lfile) as f:
                last = json.load(f)
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
        self.groups = {}
        res = self.conn.list()[1]
        for g in res:
            if g.group in last:
                self.groups[g.group] = last[g.group]
            else:
                self.groups[g.group] = int(g.last)
        with open(self.lfile, 'w') as f:
            json.dump(self.groups, f)
        self.initialized = True

    def connect(self):
        try:
            self.conn.quit()
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
        backoff = 1
        while True:
            try:
                self.conn = NNTP_SSL(self.conparams[0], self.conparams[1],
                                     self.conparams[2], self.conparams[3])
                self.time = time.time()
                break
            except Exception as e:
                time.sleep(backoff)
                backoff = min(60, backoff * 2)
                print(e, datetime.datetime.now())
                traceback.print_exc()

    def close(self):
        self.conn.quit()

    def validTopic(self, topic):
        return topic in self.groups

    def closest(self, topic):
        for t in self.groups:
            if t.endswith(topic):
                return t
        return None

    def updateTopic(self, topic, mention_manager):
        if not self.initialized:
            return []
        if time.time() - self.time > 60.:
            self.connect()
        try:
            (_, _, first, last, _) = self.conn.group(topic)
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            self.connect()
            return
        start = max(self.groups[topic] + 1, first)
        res = []
        while start <= last:
            try:
                artic = self.conn.article(start)[1]
                raw_msg = b'\r\n'.join(artic.lines)
                res.append(newsArticle(raw_msg, mention_manager, topic))
            except Exception as e:
                print(e, datetime.datetime.now())
                traceback.print_exc()
            start += 1
        self.groups[topic] = last
        with open(self.lfile, 'w') as f:
            json.dump(self.groups, f)
        return res
