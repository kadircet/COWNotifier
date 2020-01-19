import os
import json
import datetime
import traceback
import queue
from bot import cowBot
from server import webHook


def getConf(storage):
    if os.path.exists(storage):
        return json.loads(open(storage, 'r').read())
    conf = {}
    conf['bot'] = {'token': 'BOTTOKEN', 'url': 'https://example.com:8443/'}
    conf['web'] = {'cert': 'CERTFILE', 'pubkey': 'PUBKEYFILE'}
    conf['news'] = {
        'host': 'HOST',
        'auth': 'HOST',
        'port': 443,
        'user': 'UNAME',
        'pass': 'PASS',
        'last': 'lpost_id'
    }
    conf['db'] = {
        'host': 'HOST',
        'user': 'USER',
        'pass': 'PASS',
        'name': 'DBNAME'
    }
    with open(storage, 'w') as f:
        json.dump(conf, f)
    return conf


def main():
    try:
        conf = getConf('conf.ini')
        q = queue.Queue()
        bot = cowBot(conf, q)
        wh = webHook(conf, q)
        bot.start()
        wh.start()
        bot.join()
    except Exception as e:
        print(e, datetime.datetime.now())
        traceback.print_exc()


if __name__ == '__main__':
    main()
