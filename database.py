import traceback
import threading
import MySQLdb
import datetime


class dataBase:
    def __init__(self, host, uname, pw, dbname, rdr):
        self.conn = MySQLdb.connect(host, uname, pw, dbname, charset='utf8mb4')
        self.params = [host, uname, pw, dbname]
        self.rdr = rdr
        self.lock = threading.Lock()

    def close(self):
        self.conn.close()

    def ping(self):
        try:
            self.conn.ping()
            return
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
        backoff = 1
        while True:
            try:
                self.conn = MySQLdb.connect(
                    self.params[0],
                    self.params[1],
                    self.params[2],
                    self.params[3],
                    charset='utf8')
            except Exception as e:
                print(e, datetime.datetime.now())
                traceback.print_exc()
                time.sleep(backoff)
                backoff = min(60, backoff * 2)

    def registerUser(self, uid, cid, uname):
        sql = "INSERT INTO `users` (uid, cid, uname) VALUES (%s,%s,%s)"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = 0
        try:
            cur.execute(sql, (
                uid,
                cid,
                uname,
            ))
        except MySQLdb.IntegrityError:
            res = 1
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = 2
        self.conn.commit()
        cur.close()
        self.lock.release()
        return res

    def setUserStatus(self, uid, status):
        sql = "UPDATE `users` SET `is_active`=%s WHERE `uid`=%s"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = 0
        try:
            cur.execute(sql, (
                status,
                uid,
            ))
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = 1
        self.conn.commit()
        cur.close()
        self.lock.release()
        return res

    def updateUser(self, uid, no_plus_one):
        sql = "UPDATE `users` SET `no_plus_one`=%s WHERE `uid`=%s"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = 0
        try:
            cur.execute(sql, (
                no_plus_one,
                uid,
            ))
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = 1
        self.conn.commit()
        cur.close()
        self.lock.release()
        return res

    def addTopic(self, cid, topic):
        if not self.rdr.validTopic(topic):
            topic = self.rdr.closest(topic)
            if topic is None:
                return (2, topic)
        cat_id = self.rdr.getIdForTopic(topic)
        if cat_id == -1:
            return (2, topic)
        sql = "INSERT INTO `topics` (cid, cat_id, topic) VALUES (%s, %s, %s)"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = 0
        try:
            cur.execute(sql, (
                cid,
                cat_id,
                topic,
            ))
        except MySQLdb.IntegrityError:
            res = 1
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = 3
        self.conn.commit()
        cur.close()
        self.lock.release()
        return (res, topic)

    def deleteTopic(self, cid, topic):
        if not self.rdr.validTopic(topic):
            topic = self.rdr.closest(topic, self.getTopicsByCid(cid))
            if topic is None:
                return (2, topic)
        cat_id = self.rdr.getIdForTopic(topic)
        if cat_id == -1:
            return (2, topic)
        sql = "DELETE FROM `topics` WHERE cid=%s AND topic=%s AND cat_id=%s"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = 0
        try:
            cnt = cur.execute(sql, (
                cid,
                topic,
                cat_id,
            ))
            if cnt == 0:
                res = 1
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = 3
        self.conn.commit()
        cur.close()
        self.lock.release()
        return (res, topic)

    def getCids(self):
        sql = "SELECT `cid` FROM `users`"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = []
        try:
            cur.execute(sql)
            for row in cur:
                res.append(row[0])
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = None
        self.conn.commit()
        cur.close()
        self.lock.release()
        return res

    def getTopicsByCid(self, cid):
        sql = "SELECT topic FROM `topics` WHERE cid=%s"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = []
        try:
            cur.execute(sql, (cid, ))
            for row in cur:
                res.append(row[0])
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = None
        self.conn.commit()
        cur.close()
        self.lock.release()
        return res

    def getTopics(self):
        sql = "SELECT topic, cat_id FROM `topics` GROUP BY topic"
        sql2 = "SELECT `users`.`cid`, `users`.`no_plus_one` FROM `topics`, `users` WHERE cat_id=%s and `topics`.`cid`=`users`.`cid` and `users`.`is_active`=1"
        self.lock.acquire()
        cur = self.conn.cursor()
        cur2 = self.conn.cursor()
        res = []
        try:
            cur.execute(sql)
            for row in cur:
                cur2.execute(sql2, (row[1], ))
                users = []
                for user in cur2:
                    _user = (user[0], bool(user[1][0]))
                    users.append(_user)
                res.append([row[1], row[0], users])
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = None
        self.conn.commit()
        cur.close()
        self.lock.release()
        return res

    def checkForAlias(self, alias):
        sql = "SELECT `cid` FROM `aliases` WHERE `alias` = %s"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = []
        try:
            cur.execute(sql, (alias, ))
            for row in cur:
                res.append(row[0])
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = None
        cur.close()
        self.lock.release()
        return res

    def addAlias(self, cid, alias):
        sql = "INSERT INTO `aliases` (`cid`, `alias`) VALUES (%s, %s)"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = 0
        try:
            cur.execute(sql, (cid, alias))
        except MySQLdb.IntegrityError:
            res = 1
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            res = 2
        self.conn.commit()
        cur.close()
        self.lock.release()
        return res

    def getAliases(self, cid):
        sql = "SELECT `alias` FROM `aliases` WHERE `cid` = %s"
        self.lock.acquire()
        cur = self.conn.cursor()
        res = []
        try:
            cur.execute(sql, (cid, ))
            for row in cur:
                res.append(row[0])
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
        cur.close()
        self.lock.release()
        return res
