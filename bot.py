import traceback
import requests
import sys
import time
import json
import queue
import threading
from database import dataBase
from newsreader import newsReader

class cowBot(threading.Thread):
    def __init__(self, conf, q):
        threading.Thread.__init__(self)
        self.token = conf['bot']['token']
        self.q = q
        self.rdr = newsReader(conf['news']['host'], conf['news']['port'], conf['news']['user'], conf['news']['pass'])
        self.db = dataBase(conf['db']['host'], conf['db']['user'], conf['db']['pass'], conf['db']['name'], self.rdr)

        self.url = 'https://api.telegram.org/bot%s/' % self.token
        self.setWebhook(conf['bot']['url']+'%s' % self.token, conf['web']['pubkey'])
        self.registerHandlers()
        self.registerTexts()

    def updateTopics(self):
        while True:
            try:
                entries = self.db.getTopics()
                for entry in entries:
                    topic = entry[0]
                    res = self.rdr.updateTopic(topic)
                    for cid in entry[1]:
                        for msg in res:
                            self.sendMsg(cid, msg)
            except Exception as e:
                print(e)
                traceback.print_exc()
            time.sleep(1)

    def startHandler(self, data, reply=True):
        res = self.db.registerUser(data['uid'], data['cid'], data['uname'])
        msg = self.texts['error'].format(data['uname'])
        if res==0:
            msg = self.texts['welcome'].format(data['uname'])
        elif res==1:
            msg = self.texts['registered'].format(data['uname'])

        if reply:
            self.sendMsg(data['cid'], msg)

    def helpHandler(self, data):
        self.sendMsg(data['cid'], self.texts['help'])

    def addHandler(self, data):
        text = data['txt'].split(' ')
        if len(text)<2:
            self.sendMsg(data['cid'], self.texts['invalid'])
            return

        topic = text[1]
        res = self.db.addTopic(data['cid'], topic)

        msg = self.texts['error'].format(data['uname'])
        if res == 0:
            msg = self.texts['added'].format(topic)
        elif res==1:
            msg = self.texts['exists'].format(topic)
        elif res==2:
            msg = self.texts['notfound'].format(topic)

        self.sendMsg(data['cid'], msg)

    def deleteHandler(self, data):
        text = data['txt'].split(' ')
        if len(text)<2:
            self.sendMsg(data['cid'], self.texts['invalid'])
            return

        topic = text[1]
        res = self.db.deleteTopic(data['cid'], topic)

        msg = self.texts['error'].format(data['uname'])
        if res == 0:
            msg = self.texts['deleted'].format(topic)
        elif res==1:
            msg = self.texts['notexists'].format(topic)
        elif res==2:
            msg = self.texts['notfound'].format(topic)

        self.sendMsg(data['cid'], msg)

    def listHandler(self, data):
        res = self.db.getTopicsByCid(data['cid'])
        if res == None:
            msg = self.texts['error'].format(data['uname'])
        else:
            msg = ""
            for topic in res:
                msg += topic+"\r\n"
            if msg=="":
                msg = "You haven't added any topics yet"

        self.sendMsg(data['cid'], msg)

    def makeRequest(self, data):
        r = requests.post(self.url, json=data)
        res = r.json()
        if res["ok"]!=True:
            print(data, res)
        return res["ok"] == True

    def setWebhook(self, url, pubkey):
        data = {}

        data['method'] = 'deleteWebhook'
        self.makeRequest(data)

        data['method'] = 'setWebhook'
        data['url'] = url
        files = {'certificate': open(pubkey, 'rb')}
        resp = requests.post(self.url, data=data, files=files)
        if resp == False:
            print("Failed to set webhook!")
            sys.exit(1)

    def registerTexts(self):
        self.texts = {}
        self.texts['welcome'] = """Hello {}, you can use /help to get a look at commands"""
        self.texts['invalid'] = """You forgot to mention the topic name"""
        self.texts['registered'] = """Welcome back {}, type /help to take a look at commands"""
        self.texts['exists'] = """{} is already in your list"""
        self.texts['notexists'] = """{} does not seem to be in your list"""
        self.texts['notfound'] = """{} does not seem to be a valid topic"""
        self.texts['added'] = """{} has been successfully added to your list"""
        self.texts['deleted'] = """{} has been successfully deleted from your list"""
        self.texts['error'] = """Sorry {}, something went wrong, please try again"""
        self.texts['help'] = """You can add courses by "/add metu.ceng.course.100"
or any other topic, by its exact name. Then you can use "/list" to list the added topics
or use "/delete metu.ceng.course.100" to delete any course from your list"""

    def registerHandlers(self):
        self.handlers = {
                'add': self.addHandler,
                'list': self.listHandler,
                'start': self.startHandler,
                'delete': self.deleteHandler,
                'help': self.helpHandler
                }

    def sendMsg(self, cid, text):
        data = {}
        data['method'] = 'sendMessage'
        data['chat_id'] = cid
        data['text'] = text
        res=self.makeRequest(data)
        return res
        #if self.makeRequest(data)==False:
        #    print("Msg sent failed")
        #else:
        #    print("Sent:",text,cid)

    def parse(self, data):
        res = {}
        msg = data['message']
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
        if len(uname)==0:
            uname = fname+' '+lname

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

        if cmd[0]!='/':
            self.sendMsg(cid, "Master didn't make me a chatty bot!")
            return
        cmd = cmd[1:]

        if cmd not in self.handlers:
            self.sendMsg(cid, "Master didn't implement it yet!")
            return
        
        if cmd!='start':
            self.handlers['start'](data,False)
        self.handlers[cmd](data)

    def run(self):
        threading.Thread(target=self.updateTopics).start()
        while True:
            try:
                data = self.q.get()
                self.process(data)
            except Exception as e:
                print(e)
                traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()

