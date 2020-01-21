import traceback
import threading
import time
import datetime
import html
import json
import requests
import sys
from newsparser import newsArticle


class newsReader:
    def __init__(self, host, port, uname, pw, lfile, auth):
        self.conparams = [host, port, uname, pw, auth]
        self.lfile = lfile
        self.initialized = False
        self.initConnection()
    
    def makeAPICall(self,endpoint, params={}, post=False, timeout=30):
        if not endpoint.endswith('/'):
            endpoint += '/'
        try:
            req_url = self.conparams[0]+endpoint
            # do POST request
            if post:
                resp = requests.post(req_url, data=params, cookies=self.token, timeout=timeout)
            else: # do GET request
                resp = requests.get(req_url, params=params, cookies=self.token, timeout=timeout)
            return resp
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            sys.exit(1)

        

    def initConnection(self):
        self.updateAuthToken()
        self.time = time.time()

        # Grab category ids and names
        self.categories = {}
        resp = self.makeAPICall("site.json")
        if not resp.ok:
            # TODO: recover
            sys.exit(2)
        resp_categories = resp.json()['categories']
        for item in resp_categories:
            self.categories[item['id']] = item['name']

        # Read last stored post id
        try:
            with open(self.lfile) as f:
                self.last_post = int(f.read().strip())
        except Exception as e:
            self.last_post = None
            print(e, datetime.datetime.datetime.now())
            traceback.print_exc()

        # Update the last stored post id
        resp = self.makeAPICall('posts.json', params={'before':0})
        if not resp.ok:
            # TODO: recover
            sys.exit(2)
        posts = resp.json()['latest_posts']
        remote_post_id = max([p['id'] for p in posts])
        if self.last_post == None:
            with open(self.lfile, 'w') as f:
                f.write(str(remote_post_id))
            self.last_post = remote_post_id
        self.initialized = True

    def updateAuthToken(self):
        self.token = None
        data={"username":self.conparams[2], "password":self.conparams[3]}
        backoff = 1
        while True:
            try:
                resp = requests.post(self.conparams[4], data=data, allow_redirects=False, timeout=30)
                resp.raise_for_status()
                for cookie in resp.headers['Set-Cookie'].split(";"):
                    cookie = cookie.strip()
                    if cookie.startswith("_t="):
                        self.token = {"_t":cookie[3:]}
                        self.time =  time.time()
                        print(f'[*] New Auth Token: {self.token} acquired at {self.time}')
                        break
                break
            except requests.exceptions.RequestException as e:
                print(f'[X] Failed AUTH: {e.response.status_code}, Retrying in {backoff} seconds')
                time.sleep(backoff)
                backoff = min(60, backoff * 2)
            except Exception as e:
                print('[X] Failed AUTH!')
                print(e, datetime.datetime.now())
                sys.exit(1)

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
        resp = self.makeAPICall('posts.json', params={'before':0})
        if not resp.ok:
            # TODO: recover
            sys.exit(2)
        posts = json.loads(resp.text)['latest_posts']
        last = max([p['id'] for p in posts])
        start = self.last_post
        res = {}
        while start <= last:
            start += 1
            # Get post
            post = self.makeAPICall(f'posts/{start}.json')
            if not post.ok:
                # TODO: recover
                continue
            print(f"Post[{start}]: {post.ok}, {post.status_code}", end=" - ")
            post = post.json()
            # Get post's topic for category and title
            topic = self.makeAPICall(f"t/{post['topic_id']}.json")
            if not topic.ok:
                # TODO: recover
                continue
            print(f"Topic[{start}]: {topic.ok}, {topic.status_code}")
            topic = topic.json()
            if topic['category_id'] not in res:
                res[topic['category_id']] = []
            res[topic['category_id']].append(newsArticle((post['username'], post['name']),
                                                         self.categories[topic['category_id']],
                                                         topic['title'],
                                                         post['created_at'],
                                                         post['raw'],
                                                         post['cooked'],
                                                         mention_manager))
        self.last_post = start
        with open(self.lfile, 'w') as f:
            f.write(str(self.last_post))
        return res
