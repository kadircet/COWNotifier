import traceback
import threading
import time
import datetime
import html
import json
import requests
import sys
from newsparser import newsArticle
from logger import getLogger

logger = getLogger(__name__)


class newsReader:

  def __init__(self, host, port, uname, pw, lfile, auth, timezone):
    self.conparams = [host, port, uname, pw, auth]
    self.lfile = lfile
    self.timezone = timezone
    self.initialized = False
    self.initConnection()

  # TODO: Make this function higher level
  def makeAPICall(self, endpoint, params={}, **kwargs):
    post = kwargs.get('post', False)
    timeout = kwargs.get('timeout', 30)
    retry = kwargs.get('retry', False)
    redirect = kwargs.get('redirect', True)
    backoff = 1
    if not endpoint.endswith('/'):
      endpoint += '/'
    req_url = self.conparams[0] + endpoint
    while True:
      try:
        # do POST request
        if post:
          resp = requests.post(
              req_url,
              data=params,
              cookies=self.token,
              timeout=timeout,
              allow_redirects=redirect)
        else:  # do GET request
          resp = requests.get(
              req_url,
              params=params,
              cookies=self.token,
              timeout=timeout,
              allow_redirects=redirect)
        resp.raise_for_status()
        return resp, resp.status_code
      except requests.exceptions.RequestException as e:
        logger.error('Request Failed: {} -- Endpoint: {}, Data: {}', e,
                     endpoint, params)
        resp = None
        if not retry:
          return resp, e.response.status_code
        logger.error('Retrying in {} seconds', backoff)
        time.sleep(backoff)
        backoff = max(60, backoff * 2)
      except Exception as e:
        # Something outside "requests" library failed
        logger.error('{} {}', e, datetime.datetime.now())
        traceback.print_exc()
        sys.exit(1)

  def populateCategories(self):
    # Grab category ids and names
    categories = {}
    resp, _ = self.makeAPICall('site.json', retry=True)
    resp_categories = resp.json()['categories']
    parent = {}
    for item in resp_categories:
      categories[item['id']] = item['name']
      parent[item['id']] = item.get('parent_category_id', None)

    self.categories = {}
    for id, name in categories.items():
      parents = [name]
      cur_id = id
      while parent[id] is not None:
        parents.append(categories[parent[id]])
        id = parent[id]
      cat_name = '.'.join(parents[::-1])
      logger.debug('Got category: {} - {}', cur_id, cat_name)
      self.categories[cur_id] = cat_name

  def initConnection(self):
    self.updateAuthToken()
    self.time = time.time()
    self.populateCategories()

    # Read last stored post id
    try:
      with open(self.lfile) as f:
        self.last_post = int(f.read().strip())
    except Exception as e:
      self.last_post = None
      logger.error('{} {}', e, datetime.datetime.now())
      traceback.print_exc()

    # Update the last stored post id
    if self.last_post == None:
      resp, _ = self.makeAPICall('posts.json', params={'before': 0}, retry=True)
      posts = resp.json()['latest_posts']
      remote_post_id = max([p['id'] for p in posts])
      with open(self.lfile, 'w') as f:
        f.write(str(remote_post_id))
      self.last_post = remote_post_id
    self.initialized = True

  def updateAuthToken(self):
    self.token = None
    data = {'username': self.conparams[2], 'password': self.conparams[3]}
    resp, _ = self.makeAPICall(
        self.conparams[4], params=data, post=True, retry=True, redirect=False)
    for cookie in resp.headers['Set-Cookie'].split(';'):
      cookie = cookie.strip()
      if cookie.startswith('_t='):
        self.token = {'_t': cookie[3:]}
        self.time = time.time()
        logger.info('New Auth Token: {} acquired at {}', self.token, self.time)
        break

  def getIdForTopic(self, topic):
    for cat_id, name in self.categories.items():
      if name == topic:
        return cat_id
    return -1

  def validTopic(self, topic):
    return topic in self.categories.values()

  def closest(self, topic, topics=None):
    if topics == None:
      topics = self.categories.values()
    pos = []
    topic = topic.lower()
    for t in topics:
      t_lower = t.lower()
      if t_lower == topic.lower():
        return [t]
      if topic in t_lower:
        pos.append(t)
    return pos

  def updatePosts(self, mention_manager):
    if not self.initialized:
      return {}
    # TODO: Find token expiration. Currently a day.
    if time.time() - self.time > 60. * 60 * 24:
      self.updateAuthToken()

    # Get latest posts
    resp, _ = self.makeAPICall('posts.json', params={'before': 0})
    if resp == None:
      return {}
    posts = json.loads(resp.text)['latest_posts']
    last = max([p['id'] for p in posts])
    start = self.last_post
    res = {}
    while start < last:
      start += 1
      # Get post
      post, code = self.makeAPICall(f'posts/{start}.json')
      if post == None:
        if code == 403 or code == 404:
          continue
        start -= 1
        break
      post = post.json()
      # post information we get through 'posts/{id}.json'
      # doesn't contain category_id and topic_title so
      # we need to make another request for that info.
      # TODO: Cache topic_id -> category_id and
      #       topic_id -> topic_title mappings

      # Get post's topic for category and title
      topic, code = self.makeAPICall(f"t/{post['topic_id']}.json")
      if topic == None:
        if code == 403 or code == 404:
          continue
        start -= 1
        break
      topic = topic.json()
      if topic['category_id'] not in self.categories:
        logger.error('Unknown category_id: {}', topic['category_id'])
        continue
      if topic['category_id'] not in res:
        res[topic['category_id']] = []
      # TODO(kadircet): Also include link to the post via topic_id and post_count.
      res[topic['category_id']].append(
          newsArticle(
              (post['username'], post['name']),
              self.categories[topic['category_id']],
              topic['title'],
              (post['created_at'], self.timezone),
              post['raw'],  # raw msg (markdown)
              mention_manager))
    self.last_post = start
    with open(self.lfile, 'w') as f:
      f.write(str(self.last_post))
    return res
