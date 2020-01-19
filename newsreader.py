import traceback
import threading
import time
import datetime
import html
import json
import requests
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

        # Read last stored post id
        try:
            with open(self.lfile) as f:
                self.last_post = int(f.read().strip())
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()

        # Update the last stored post id
        resp = requests.get(self.conparams[0]+"posts.json", cookies=self.token)
        posts = json.loads(resp.text)['latest_posts']
        with open(self.lfile, 'w') as f:
            f.write(str(posts[0]['id']))
        self.initialized = True

    def updateAuthToken(self):
        self.token = None
        data={"username":self.conparams[3], "password":self.conparams[4]}
        backoff = 1
        while True:
            resp = requests.post(self.conparams[1], data=data, allow_redirects=False)
            if resp.ok:
                for cookie in resp.headers['Set-Cookie'].split(";"):
                    cookie = cookie.strip()
                    if cookie.startswith("_t="):
                        self.token = {"_t":cookie[3:]}
                        self.time =  time.time()
                        print(f'[*] New Auth Token: {self.token} acquired at {self.time}')
                        break
                break
            else:
                print(f'[X] Failed AUTH: {resp.status_code}, Retrying in {backoff} seconds')
                time.sleep(backoff)
                backoff = min(60, backoff * 2)

    def getIdForTopic(self, topic):
        for cat_id, name in self.categories.items():
            if name == topic:
                return cat_id
        return -1

    def validTopic(self, topic):
        return topic in self.categories.values()

    def closest(self, topic, topics=None):
        if topics is None:
            topics = self.categories
        for t in topics:
            if t.endswith(topic):
                return t
        return None

    def updatePosts(self, mention_manager):
        if not self.initialized:
            return []
        # TODO: Find token expiration, 60 secs is a bit low
        if time.time() - self.time > 60.:
            self.updateAuthToken()
        
        # Get latest posts
        resp = requests.get(self.conparams[0]+'posts.json', cookies=self.token)
        posts = json.loads(resp.text)['latest_posts']
        start = max(self.last_post, posts[-1]['id'])
        last = start
        res = {}
        for post in posts[::-1]:
            if post['id'] > start:
                last = max(post['id'], last)
                if post['category_id'] not in res:
                    res[post['category_id']] = []
                res[post['category_id']].append(newsArticle((post['username'], post['name']),
                                                            self.categories[post['category_id']],
                                                            post['topic_title'],
                                                            post['created_at'],
                                                            post['raw'],
                                                            post['cooked'],
                                                            mention_manager))
        self.last_post = last
        with open(self.lfile, 'w') as f:
            f.write(str(self.last_post))
        return res
