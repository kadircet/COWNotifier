import traceback
import threading
import time
import datetime
import html
import json
from newsparser import newsArticle


class newsReader:
    def __init__(self, host, auth, port, uname, pw, lfile):
        self.conparams = [host, auth, port, uname, pw]
        self.lfile = lfile
        self.initialized = False
        self.initConnection()

    def initConnection(self):
        self.updateAuthToken()
        self.time = time.time()

        # Grab category ids and names
        self.categories = {}
        resp = requests.get(self.conparams[0]+"site.json", cookies=self.token)
        resp_categories = json.loads(resp.text)['categories']
        for item in resp_categories:
            self.categories[item['id']] = item['name']

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

    def getIdForTopic(self, topic):
        for cat_id, name in self.categories.items():
            if name == topic:
                return cat_id
        return -1

    def validTopic(self, topic):
        return topic in self.groups

    def closest(self, topic, topics=None):
        if topics is None:
            topics = self.groups
        for t in topics:
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
