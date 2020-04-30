import traceback
import datetime
import requests
import sys
import time
import threading
from database import dataBase
from newsreader import newsReader
from mention_manager import mentionManager
from markdownrenderer import escape, unescape
from logger import getLogger

logger = getLogger(__name__)


class cowBot(threading.Thread):
  MAX_RETRIES = 3

  def __init__(self, conf, q):
    threading.Thread.__init__(self)
    self.token = conf['bot']['token']
    self.conf = conf
    self.q = q
    self.rdr = newsReader(conf['news']['host'], conf['news']['port'],
                          conf['news']['user'], conf['news']['pass'],
                          conf['news']['last'], conf['news']['auth'],
                          conf['news']['timezone'])
    self.db = dataBase(conf['db']['host'], conf['db']['user'],
                       conf['db']['pass'], conf['db']['name'], self.rdr)
    self.mention_manager = mentionManager(self.db, self)

    self.url = 'https://api.telegram.org/bot%s/' % self.token
    self.setWebhook(conf['bot']['url'] + '%s' % self.token,
                    conf['web']['pubkey'])
    self.registerHandlers()
    self.registerTexts()

  def updateTopics(self):
    while True:
      try:
        self.db.ping()
        entries = self.db.getTopics()
        posts = self.rdr.updatePosts(self.mention_manager)
        for entry in entries:
          cat_id = entry[0]
          relevant_posts = posts.get(cat_id, [])
          for user in entry[1]:
            for msg in relevant_posts:
              if not user[1] or not msg.isPlusOne():
                self.sendArticle(user[0], msg)
      except Exception as e:
        logger.error('{} {}', e, datetime.datetime.now())
        traceback.print_exc()
      time.sleep(10)

  def startHandler(self, data, reply=True):
    self.db.ping()
    res = self.db.registerUser(data['uid'], data['cid'], data['uname'])
    msg = self.texts['error'].format(data['uname'])
    if res == 0:
      msg = self.texts['welcome'].format(data['uname'])
    elif res == 1:
      msg = self.texts['registered'].format(data['uname'])
      self.db.setUserStatus(data['cid'], 1)

    if reply:
      self.sendMsg(data['cid'], msg)

  def handlePlusOne(self, data, no_plus_one, reply=True):
    self.db.ping()
    res = self.db.updateUser(data['uid'], no_plus_one)
    msg = self.texts['error'].format(data['uname'])
    if res == 0:
      msg = self.texts['updated'].format(data['uname'])
    if reply:
      self.sendMsg(data['cid'], msg)

  def noPlusOne(self, data, reply=True):
    self.handlePlusOne(data, True, reply)

  def yesPlusOne(self, data, reply=True):
    self.handlePlusOne(data, False, reply)

  def helpHandler(self, data):
    self.sendMsg(data['cid'], self.texts['help'])

  def addHandler(self, data):
    text = data['txt'].split(' ')
    if len(text) < 2:
      self.sendMsg(data['cid'], self.texts['invalid'])
      return

    topic = ' '.join(text[1:])
    self.db.ping()
    res, added_topic = self.db.addTopic(data['cid'], topic)

    msg = self.texts['error'].format(data['uname'])
    if res == 0:
      msg = self.texts['added'].format(added_topic)
    elif res == 1:
      msg = self.texts['exists'].format(added_topic)
    elif res == 2:
      msg = self.texts['notfound'].format(topic)
    elif res == 4:
      msg = self.texts['ambiguous'].format(added_topic)

    self.sendMsg(data['cid'], msg)

  def announcementHandler(self, data):
    if data['uid'] != 147926496:
      return

    text = data['txt'].split(' ')
    if len(text) < 2:
      self.sendMsg(data['cid'], self.texts['invalid'])
      return
    text = text[1]

    for cid in self.db.getCids():
      self.sendMsg(cid, text)

  def deleteHandler(self, data):
    text = data['txt'].split(' ')
    if len(text) < 2:
      self.sendMsg(data['cid'], self.texts['invalid'])
      return

    topic = ' '.join(text[1:])
    self.db.ping()
    res, deleted_topic = self.db.deleteTopic(data['cid'], topic)

    msg = self.texts['error'].format(data['uname'])
    if res == 0:
      msg = self.texts['deleted'].format(deleted_topic)
    elif res == 1:
      msg = self.texts['notexists'].format(deleted_topic)
    elif res == 2:
      msg = self.texts['notfound'].format(topic)
    elif res == 4:
      msg = self.texts['ambiguous'].format(deleted_topic)

    self.sendMsg(data['cid'], msg)

  def listHandler(self, data):
    self.db.ping()
    res = self.db.getTopicsByCid(data['cid'])
    if res is None:
      msg = self.texts['error'].format(data['uname'])
    elif len(res) > 0:
      msg = '\r\n'.join(res)
    else:
      msg = "You haven't added any topics yet"

    self.sendMsg(data['cid'], msg)

  def listAll(self, data):
    msg = '\n'.join(self.rdr.categories.values())
    self.sendMsg(data['cid'], msg)

  def addAliasHandler(self, data):
    cid = data['cid']
    text = data['txt'].split(' ')
    if len(text) < 2:
      self.sendMsg(cid, self.texts['noalias'])
      return

    alias = text[1]
    if self.mention_manager.isStudentNumber(alias) is None:
      msg = self.texts['aliasnotvalid'].format(alias)
    else:
      self.db.ping()
      alias = self.mention_manager.getMinimalStudentNo(alias)
      res = self.db.addAlias(cid, alias)
      msg = self.texts['error'].format(data['uname'])
      if res == 0:
        msg = self.texts['aliasadded'].format(alias)
      elif res == 1:
        msg = self.texts['aliasexists'].format(alias)

    self.sendMsg(cid, msg)

  def showAliasesHandler(self, data):
    cid = data['cid']

    self.db.ping()
    aliases = self.db.getAliases(cid)
    msg = '\r\n'.join(aliases)
    if len(aliases) == 0:
      msg = "You haven't added any aliases yet."
    self.sendMsg(cid, msg)

  def makeRequest(self, data, depth=1):
    try:
      r = requests.post(self.url, json=data)
      logger.debug('Request: {}', data)
      res = r.json()
      if res['ok']:
        return True, res
      if res['error_code'] == 403 and res['description'] in (
          'Forbidden: bot was blocked by the user',
          'Forbidden: user is deactivated'):
        logger.info('Disabling user: {}', data['chat_id'])
        self.db.ping()
        self.db.setUserStatus(data['chat_id'], 0)
        return False, res
      if res['error_code'] == 429 and depth < self.MAX_RETRIES:
        params = res.get('parameters', {})
        wait = params.get('retry_after')
        if wait:
          logger.info('Hit flood control, retrying in {} secs', wait)
          time.sleep(wait)
          return self.makeRequest(data, depth + 1)
      logger.error('Req {} failed with {}', data, res)
      return False, res
    except Exception as e:
      logger.error('{} {}', e, datetime.datetime.now())
      traceback.print_exc()
    return False, res

  def makeMultiPartRequest(self, files, data):
    try:
      r = requests.post(self.url, files=files, data=data)
      res = r.json()
      if res['ok'] != True:
        logger.error('Multi part req {} failed with {}', data, res)
      return res
    except Exception as e:
      logger.error('{} {}', e, datetime.datetime.now())
      traceback.print_exc()
    return False

  def setWebhook(self, url, pubkey):
    data = {}

    data['method'] = 'deleteWebhook'
    self.makeRequest(data)

    data['method'] = 'setWebhook'
    data['url'] = url
    files = {'certificate': open(pubkey, 'rb')}
    resp = requests.post(self.url, data=data, files=files).json()
    if resp['ok'] == False:
      logger.error('Failed to set webhook {} - {}', data, resp)
      sys.exit(1)

  def registerTexts(self):
    self.texts = {}
    self.texts[
        'welcome'] = """Hello {}, you can use /help to get a look at commands"""
    self.texts['invalid'] = """You forgot to mention the topic name"""
    self.texts[
        'registered'] = """Welcome back {}, type /help to take a look at commands"""
    self.texts['exists'] = """{} is already in your list"""
    self.texts['notexists'] = """{} does not seem to be in your list"""
    self.texts['notfound'] = """{} does not seem to be a valid topic"""
    self.texts['added'] = """{} has been successfully added to your list"""
    self.texts[
        'deleted'] = """{} has been successfully deleted from your list"""
    self.texts['error'] = """Sorry {}, something went wrong, please try again"""
    self.texts[
        'updated'] = """Well played! Your profile successfully updated, {}."""
    self.texts[
        'help'] = """/add NEWSGROUP_SUFFIX - Adds first group matching the suffix to watchlist.

/list - Lists groups in the watchlist.

/delete NEWSGROUP - Deletes given group from watchlist.

/help - Shows that list.

/listall - Lists all possible groups to watch.

/noplus1 - Enables +1 filtering.*Experimental*.

/yesplus1 - Disables +1 filtering.

/addalias STUDENT\_NO - Adds given student number to aliases to receive mention notifications. STUDENT\_NO must be in the form e?\d{6,7}.*Experimental*.

/showaliases - Lists all registered aliases.

For any bugs and hugs reach out to @kadircet or @hbostann
Source is available at https://github.com/kadircet/COWNotifier
"""
    self.texts[
        'aliasadded'] = """Alias {}, has been succesfully added to your mention list."""
    self.texts[
        'aliasnotvalid'] = """Alias must be METU student number, complying with regex e?\d{{6,7}}, {} doesn't comply with it."""
    self.texts[
        'aliasexists'] = """You already have {} as one of your aliases."""
    self.texts['noalias'] = """You forgot to provide an alias."""
    self.texts['ambiguous'] = """Ambiguous selection: {}."""

  def registerHandlers(self):
    self.handlers = {
        'add': self.addHandler,
        'list': self.listHandler,
        'start': self.startHandler,
        'delete': self.deleteHandler,
        'help': self.helpHandler,
        'listall': self.listAll,
        'no+1': self.noPlusOne,
        'yes+1': self.yesPlusOne,
        'noplus1': self.noPlusOne,
        'yesplus1': self.yesPlusOne,
        'announcement': self.announcementHandler,
        'addalias': self.addAliasHandler,
        'showaliases': self.showAliasesHandler
    }

  def sendArticle(self, cid, article):
    self.sendMsg(cid, article.parse(), escaped=True)
    # TODO: Send attachments

  def sendMsg(self, cid, text, escaped=False):
    if text is None:
      return
    if not escaped:
      text = escape(text)
    data = {}
    data['method'] = 'sendMessage'
    data['chat_id'] = cid
    data['parse_mode'] = 'MarkdownV2'
    while len(text):
      data['text'] = text[:4096]
      text = text[4096:]
      status, res = self.makeRequest(data)
      # Failed to send message, try to recover.
      if res.get('error_code') == 400 and res.get(
          'description', '').startswith('Bad Request: can\'t parse entities:'):
        data['text'] = unescape(data['text'])
        # In case of a bad markdown syntax, try with plaintext.
        del data['parse_mode']
        status, _ = self.makeRequest(data)
        # Restore parse_mode for remaining blocks.
        data['parse_mode'] = 'MarkdownV2'

      if not status:
        break
    return

  def sendAttachment(self, cid, attachment):
    data = {}
    data['method'] = 'sendDocument'
    data['chat_id'] = cid
    if attachment.file_id:
      data['document'] = attachment.file_id
      self.makeRequest(data)
    else:
      files = {
          'document': (attachment.name, attachment.content, attachment.type)
      }

      res = self.makeMultiPartRequest(files, data)
      if res:
        attachment.file_id = res['result']['document']['file_id']
        attachment.content = None

  def parse(self, data):
    res = {}
    if 'message' in data:
      msg = data['message']
    elif 'edited_message' in data:
      msg = data['edited_message']
    if 'text' not in msg:
      msg['text'] = 'n n'
    cht = msg['chat']
    frm = msg['from']
    cid = cht['id']
    uid = frm['id']
    cmd = msg['text'].split(' ')[0]
    txt = msg['text']
    uname = ''
    fname = ''
    lname = ''
    if 'username' in frm:
      uname = frm['username']
    if 'first_name' in frm:
      fname = frm['first_name']
    if 'last_name' in frm:
      lname = frm['last_name']
    if len(uname) == 0:
      uname = fname + ' ' + lname

    res['msg'] = msg
    res['cht'] = cht
    res['frm'] = frm
    res['cid'] = cid
    res['uid'] = uid
    res['cmd'] = cmd
    res['txt'] = txt
    res['uname'] = uname
    return res

  def process(self, data):
    data = self.parse(data)
    cid = data['cid']
    cmd = data['cmd']

    if cmd[0] != '/':
      self.sendMsg(cid, "Master didn't make me a chatty bot!")
      return
    cmd = cmd[1:].lower()

    if cmd not in self.handlers:
      self.sendMsg(cid, "Master didn't implement it yet!")
      return

    if cmd != 'start':
      self.handlers['start'](data, False)
    self.handlers[cmd](data)

  def run(self):
    threading.Thread(target=self.updateTopics).start()
    while True:
      try:
        data = self.q.get()
        self.process(data)
      except Exception as e:
        logger.error('{}', e)
        traceback.print_exc()
      sys.stdout.flush()
      sys.stderr.flush()
