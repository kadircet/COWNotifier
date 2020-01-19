import os
import datetime
import traceback
import re

class newsArticle:
    def __init__(self, user, topic, subject, date, raw_msg, raw_html, mention_manager):
        self.user = user
        self.topic = topic
        self.subject = subject
        self.date = date
        self.raw_msg = raw_msg
        self.raw_html = raw_html
        self.mention_manager = mention_manager
        self.broken = False
        self.content = None
        self.is_plus_one = None
        self.attachments = None

    def isPlusOne(self):
        if self.is_plus_one is None:
            self.is_plus_one = self.raw_msg.startswith("+1") and len(self.raw_msg) < 10
        return self.is_plus_one

    def getAsHtml(self):
        if self.content is None:
            self.parseMessage()
        return self.content

    def getAttachments(self):
        if self.attachments is None:
            self.parseMessage()
        return self.attachments

    def makeHeader(self):
        hdr = f"```\r\n"\
            f"From: {self.user[0]}({self.user[1]})\r\n"\
            f"Newsgroup: {self.topic}\r\n"\
            f"Subject: {self.subject}\r\n"\
            f"Date: {self.date}\r\n"\
            f"is_plus_one: {self.isPlusOne()}```\n\n"
        return hdr

    def parseMarkup(self, msg):
        parsed = msg.split("\n")
        for i in range(len(parsed)):
                line = parsed[i]
                if line.startswith("#"):
                    line = line.lstrip("# ")
                    line = "*"+line+"*"
                elif line.startswith("*"):
                    line = '\\'+line
                elif line.startswith(">"):
                    line = " >_"+line[1:]+"_"
                parsed[i] = line
        parsed = "\n".join(parsed)
        return parsed

    def parseLinks(self, msg):
        regex = r"!\[([^\]]*)\]\(([^\)]*)\)"
        img_tag = '<img src=\"'
        pattern = re.compile(regex)
        parsed = ""
        link_counter = 1
        last_pos = 0
        for m in pattern.finditer(msg):
            # Find link name
            name_start, name_end = m.span(1)
            link_name = msg[name_start:name_end]
            if link_name == "":
                link_name = f"Link {link_counter}"

            # Find first img link in html
            html_link_start = self.raw_html.find(img_tag)+len(img_tag)
            html_link_len = self.raw_html[html_link_start:].find('"')
            html_link = self.raw_html[html_link_start:html_link_start+html_link_len]
            # Discard used html
            self.raw_html = self.raw_html[html_link_start+html_link_len:]

            # Replace link in markdown
            match_start, match_end = m.span()
            parsed += msg[last_pos:match_start] + f"[{link_name}]({html_link})"

            last_pos = match_end
            link_counter+=1

        parsed += msg[last_pos:]
        return parsed

    def parseMessage(self):
        if self.broken:
            return
        self.attachments = []
        try:
            hdr = self.makeHeader()
            content = self.parseMarkup(self.raw_msg)
            content = self.parseLinks(content)
            self.mention_manager.parseMentions(content, self.topic)
            self.content = hdr + content
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            self.broken = True
