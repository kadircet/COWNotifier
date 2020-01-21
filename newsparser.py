import os
import datetime
import traceback
import re

def isPlusOne(msg):
    return msg.startswith("+1") and len(msg) < 10

class newsArticle:
    def __init__(self, author, topic, subject, date, raw_msg, raw_html, mention_manager):
        self.author_username = author[0]
        self.author_displayname = author[1]
        self.topic = topic
        self.subject = subject
        self.date = date
        self.raw_msg = raw_msg
        self.raw_html = raw_html
        self.mention_manager = mention_manager
        self.broken = False
        self.content = None
        self.is_plus_one = None


    def isPlusOne(self):
        if self.is_plus_one is None:
            self.is_plus_one = isPlusOne(self.raw_msg)
        return self.is_plus_one

    def getAsHtml(self):
        if self.content is None:
            self.parseMessage()
        return self.content

    # TODO: getAttachemnts:
    #  Extract the images and files in the message

    def makeHeader(self):
        hdr = f"```\r\n"\
            f"From: {self.author_username}({self.author_displayname})\r\n"\
            f"Newsgroup: {self.topic}\r\n"\
            f"Subject: {self.subject}\r\n"\
            f"Date: {self.date}\r\n"\
            f"is_plus_one: {self.isPlusOne()}```\n\n"
        return hdr

    def parseLinks(self, msg):
        # In markdown, discourse uses the following format for images and image links
        #     ![image_name](upload://<file_name_hash>)
        # However, in the html version of the message image links are regular http(s)
        # links. This part of the code removes the upload:// urls from the markdown and
        # replaces them with the image links from the html version.
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

        try:
            hdr = self.makeHeader()
            content = self.raw_msg
            # TODO: Parse Markup
            content = self.parseLinks(content)
            content = ''.join(['\\'+c for c in content if ord(c) > 0 and ord(c) < 128])
            self.mention_manager.parseMentions(content, self.topic)
            self.content = hdr + content
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            self.broken = True
