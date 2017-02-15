from nntplib import NNTP_SSL, NNTP

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
        headers = ["from:", "newsgroups:", "subject:", "date:"]
        while start<=last:
            artic = self.conn.article(start)[1]
            coding = 'iso-8859-9'
            for x in artic.lines:
                if x.decode('utf-8').lower().startswith('subject:'):
                    if 'utf-8' in x.decode('utf-8').lower():
                        coding = 'utf-8'
                    break
            artic = [x.decode(coding).strip() for x in artic.lines]
            msg = ""
            data = False
            for line in artic:
                if data:
                    msg+=line+"\r\n"
                    continue
                for h in headers:
                    if line.lower().startswith(h):
                        msg+=line+"\r\n"
                else:
                    if line=="":
                        data=True
            res.append(msg)
            start+=1
        self.groups[topic] = last
        return res

