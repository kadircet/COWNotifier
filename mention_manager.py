import re
import html


class mentionManager:
    def isStudentNumber(self, msg):
        return self.student_no_matcher.match(msg) != None

    def __init__(self, db, cow_bot):
        self.student_no_matcher = re.compile("^e?\d{6,7}$")
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

    def parseMentions(self, content, newsgroup):
        current_header = ""
        line_no = 0
        for raw_line in content.split('\n'):
            line = raw_line.strip()
            if self.isStudentNumber(line):
                cids = self.db.checkForAlias(line)
                if cids != None:
                    for cid in cids:
                        self.sendMention(cid, line, newsgroup, current_header,
                                         line_no)
            else:
                current_header = line
                line_no = 0
            line_no += 1
