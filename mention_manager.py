import re
import html


class mentionManager:
    def isStudentNumber(self, msg):
        search = self.student_no_matcher.search(msg)
        return search if search is None else search.group()

    def __init__(self, db, cow_bot):
        self.student_no_matcher = re.compile("e?\d{6,7}")
        self.db = db
        self.cow_bot = cow_bot
        self.mention_text = "Your alias <b>{}</b> has been mentioned in " + \
                "newsgroup: <b>{}</b> with header: <b>{}</b> at line: {}."

    def sendMention(self, cid, alias, newsgroup, header, line_no):
        return self.cow_bot.sendMsg(cid,
                                    self.mention_text.format(
                                        html.escape(alias),
                                        html.escape(newsgroup),
                                        html.escape(header), line_no))

    def getMinimalStudentNo(self, student_no):
        base = student_no
        if base[0] == 'e':
            base = base[1:]
        base = base[:6]
        return base

    def parseMentions(self, content, newsgroup):
        current_header = ""
        line_no = 0
        for raw_line in content.split('\n'):
            line = raw_line.strip()
            if line.startswith('&gt'):
                continue
            student_no = self.isStudentNumber(line)
            if student_no is not None:
                cids = self.db.checkForAlias(
                    self.getMinimalStudentNo(student_no))
                if cids is None:
                    continue
                header = current_header
                if len(line) > len(student_no):
                    header = line
                for cid in cids:
                    self.sendMention(cid, student_no, newsgroup, header,
                                     line_no)
            else:
                current_header = line
                line_no = 0
            line_no += 1
