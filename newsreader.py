from nntplib import NNTP_SSL, NNTP
import email
from email.policy import EmailPolicy
from email.headerregistry import HeaderRegistry, UnstructuredHeader


class newsReader:
    def __init__(self, host, port, uname, pw):
        self.conn = NNTP_SSL(host, port, uname, pw)
        self.groups = {}
        res = self.conn.list()[1]
        for g in res:
            self.groups[g.group] = int(g.last)

    def close(self):
        self.conn.quit()

    def validTopic(self, topic):
        return topic in self.groups

    def closest(self, topic):
        tmp = "metu.ceng."+topic
        if tmp in self.groups:
            return tmp
        tmp = "metu.ceng.course."+topic
        if tmp in self.groups:
            return tmp
        return None

    def updateTopic(self, topic):
        (_, _, first, last, _) = self.conn.group(topic)
        start = max(self.groups[topic]+1, first)
        res = []
        headers = ("From", "Newsgroups", "Subject", "Date")
        registry = HeaderRegistry()
        registry.map_to_type('From', UnstructuredHeader)
        policy = EmailPolicy(header_factory=registry)
        while start<=last:
            artic = self.conn.article(start)[1]
            raw_msg = b'\r\n'.join(artic.lines)
            mime_msg = email.message_from_bytes(raw_msg, policy=policy)
            msg = ""
            for h in headers:
                msg += "%s: %s\r\n" % (h, mime_msg[h])
            for part in mime_msg.walk():
                if part.get_content_type() == 'text/plain':
                    msg += part.get_content()
                    break
            res.append(msg)
            start+=1
        self.groups[topic] = last
        return res

