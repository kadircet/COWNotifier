import datetime
import traceback
from logger import getLogger
from markdownrenderer import convertDiscourseToTelegram, escape

logger = getLogger(__name__)


def isPlusOne(msg):
  return msg.startswith('+1') and len(msg) < 10


def getHumanReadableDate(date):
  # Date is expected to be a tuple of two elements, from newsreader.
  # date[0] -> message's date in raw form: %Y:%m:%dT%H:%M:%S.xxZ
  # where 'xx's and Z represent nanosecs(?) and the UTC +0 respectively.
  # date[1] -> list of timezone difference to localzone, Turkey's is UTC 3.00,
  #            so it is [3, 0] representing hours and minutes by default.
  rawDate, localTimezone = date
  # Parse the raw format and add localTimezone's hour difference.

  machineDate = datetime.datetime.strptime(
      rawDate.split('.')[0],
      '%Y-%m-%dT%H:%M:%S') + datetime.timedelta(hours=localTimezone)
  # return the human readable from, refer to datetime.strftime for format
  # options.
  # an example of current format: 03 Feb 2020, 18:30:00
  return machineDate.strftime('%d %b %Y, %H:%M:%S')


class newsArticle:

  def __init__(self, author, topic, subject, date, dc_markdown,
               mention_manager):
    self.author_username = author[0]
    self.author_displayname = author[1]
    self.topic = topic
    self.subject = subject
    self.date = getHumanReadableDate(date)
    self.dc_markdown = dc_markdown
    self.mention_manager = mention_manager
    self.broken = False
    self.tg_markdown = None
    self.is_plus_one = None

  def isPlusOne(self):
    if self.is_plus_one is None:
      self.is_plus_one = isPlusOne(self.dc_markdown)
    return self.is_plus_one

  def parse(self):
    # TODO(kadircet): Improve handling of 4K text limit.
    if self.tg_markdown is None:
      self.parseMessage()
    return self.tg_markdown

  # TODO: getAttachemnts:
  #  Extract the images and files in the message

  def makeHeader(self):
    hdr = f"From: {self.author_username}({self.author_displayname})\n"\
        f"Newsgroup: {self.topic}\n"\
        f"Subject: {self.subject}\n"\
        f"Date: {self.date}\n"\
        f"is_plus_one: {self.isPlusOne()}"
    return '```\n' + escape(hdr, True) + '\n```\n'

  def parseMessage(self):
    if self.broken:
      return

    try:
      self.mention_manager.parseMentions(self.dc_markdown, self.topic)
      paragraphs = convertDiscourseToTelegram(self.dc_markdown)
      self.tg_markdown = self.makeHeader() + '\n\n'.join(paragraphs)
    except Exception as e:
      logger.error('{} {}', e, datetime.datetime.now())
      traceback.print_exc()
      # Record failure so we don't retry.
      self.broken = True
