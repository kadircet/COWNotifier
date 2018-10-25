import email
import os
import hashlib
import datetime
import traceback
import html
from email.policy import EmailPolicy
from email.headerregistry import HeaderRegistry, UnstructuredHeader


class telegramAttachment:
    def __init__(self, file_name, file_content, file_type):
        ext = os.path.splitext(file_name)[1].replace('"', '')
        self.name = hashlib.sha1(file_name.encode('utf-8')).hexdigest() + ext
        self.content = file_content
        self.type = file_type
        self.file_id = None


def isPlusOne(msg):
    return msg.startswith("+1") and len(msg) < 10


def tryParseAttachment(part):
    content_disp = part.get("Content-Disposition", None)
    if content_disp is None:
        return None
    disps = content_disp.strip().split(';')
    if disps[0].lower() != "attachment":
        return None
    file_data = part.get_payload(decode=True)
    content_type = part.get_content_type()
    file_name = "whoknows"
    for config in disps[1:]:
        param, value = (x.strip() for x in config.split('='))
        if param == "filename":
            file_name = value
            break
    return telegramAttachment(file_name, file_data, content_type)


class newsArticle:
    headers = ("From", "Newsgroups", "Subject", "Date")
    registry = HeaderRegistry()
    registry.map_to_type('From', UnstructuredHeader)
    policy = EmailPolicy(header_factory=registry)

    def __init__(self, raw_msg, mention_manager, topic):
        self.raw_msg = raw_msg
        self.mention_manager = mention_manager
        self.topic = topic
        self.broken = False
        self.content = None
        self.is_plus_one = None
        self.attachments = None

    def isPlusOne(self):
        if self.is_plus_one is None:
            self.parseMessage()
        return self.is_plus_one

    def getAsHtml(self):
        if self.content is None:
            self.parseMessage()
        return self.content

    def getAttachments(self):
        if self.attachments is None:
            self.parseMessage()
        return self.attachments

    def parseMessage(self):
        if self.broken:
            return
        self.attachments = []
        try:
            mime_msg = email.message_from_bytes(
                self.raw_msg, policy=newsArticle.policy)
            hdr = "<code>"
            for h in newsArticle.headers:
                hdr += "%s: %s\r\n" % (h, html.escape(mime_msg[h]))
            content = ""
            for part in mime_msg.walk():
                attachment = tryParseAttachment(part)
                if attachment:
                    self.attachments.append(attachment)
                elif part.get_content_type() == 'text/plain':
                    content += str(
                        part.get_payload(decode=True),
                        part.get_content_charset(), 'replace')
            content = html.escape(content)
            self.is_plus_one = isPlusOne(content)
            self.mention_manager.parseMentions(content, self.topic)
            hdr += "%s: %s\r\n" % ("is_plus_one", self.is_plus_one)
            hdr += "</code>\r\n"
            self.content = hdr + content
        except Exception as e:
            print(e, datetime.datetime.now())
            traceback.print_exc()
            self.broken = True
