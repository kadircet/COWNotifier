import html
from html.parser import HTMLParser
import os
import datetime
import traceback
import re
from emoji_codepoints import emoji


def isPlusOne(msg):
  return msg.startswith("+1") and len(msg) < 10


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
      "%Y-%m-%dT%H:%M:%S") + datetime.timedelta(hours=localTimezone)
  # return the human readable from, refer to datetime.strftime for format
  # options.
  # an example of current format: 03 Feb 2020, 18:30:00
  return machineDate.strftime("%d %b %Y, %H:%M:%S")


class articleParser(HTMLParser):
  # articleParser parses the raw html from Discourse and generates html that
  # Telegram likes. During the process it performs the following.
  #
  # Convert Tags: Telegram supports a very small subset of html tags. In order
  #               to provide (some) formatting in the telegram message, parser
  #               converts tags that telegram doesn't like into ones it does
  #               or removes them (not the contents) if no conversion exists.
  # Handle Image: Images are wrapped in <a> tags with href same as img's src.
  #               (<a><img></a>) In this case parser removes the <img> tag
  #               completely since Telegram handles <a> tags pretty well with
  #               previews. (Also telegram doesn't support <img> tags). In
  #               the future, we may want to ditch the telegram's preview to
  #               handle multiple images (preview only shows the first image)
  #               TODO: Handle images as attachements, preferably as albums.
  # Handle Emoji: Emojis are represented as <img> tags but they are not wrapped
  #               in <a> tags, unlike the previous case. Parser replaces <img>
  #               tags with 'class="emoji"' with their unicode codepoint.

  # Tags supported by Telegram
  # https://core.telegram.org/bots/api#html-style
  supported_tags = [
      'strike', 'i', 'strong', 'b', 'pre', 'ins', 'a', 'code', 'del', 's', 'em',
      'u'
  ]
  # html_tag -> telegram_tag mapping for formatting purposes
  tag_mapping = {'h1': 'b', 'h2': 'b', 'h3': 'b', 'blockquote': 'i'}

  def __init__(self):
    super().__init__(convert_charrefs=False)
    self.reset()
    self.open_tags = []
    self.fed = []

  def handle_entityref(self, name):
    # This is done so that html entities like '&gt;' remain escaped.
    self.fed.append(f'&{name};')

  def handle_starttag(self, tag, attrs):
    tag_attrs = {at[0]: at[1] for at in attrs}
    if tag == 'a':
      href = tag_attrs.get('href', '#')
      if href == '#':
        print(f"<a> with no href: {tag} -> {tag_attrs}")
      self.fed.append(f'<a href="{href}">')
      self.open_tags.append('a')
      return
    if tag == 'img':
      if tag_attrs.get('class', '') == 'emoji':
        self.fed.append(emoji.get(tag_attrs.get('title', ':cow:'), ''))
        return
      if len(self.open_tags) == 0 or self.open_tags[-1] != 'a':
        self.fed.append(f"<a href=\"{tag_attrs.get('src', '#')}\">Image</a>")
        print("Image not wrapped in <a> tags: {tag} -> {tag_attrs}")
      return
    if tag not in self.supported_tags:
      tag = self.tag_mapping.get(tag, None)
    if not tag:
      return
    self.fed.append(f'<{tag}>')
    self.open_tags.append(tag)

  def handle_data(self, data):
    self.fed.append(data)

  def handle_endtag(self, tag):
    # If tag is not supported, it is never added to open_tags so we do nothing
    # otherwise, we pop the open_tags and close the tag in the message.
    if tag not in self.supported_tags:
      tag = self.tag_mapping.get(tag, None)
    if not tag or tag != self.open_tags[-1]:
      return
    self.open_tags.pop()
    self.fed.append(f'</{tag}>')

  def get_data(self):
    return "".join(self.fed)


class legacyParser(HTMLParser):

  def __init__(self):
    super().__init__(convert_charrefs=False)
    self.reset()
    self.fed = []

  def handle_entityref(self, name):
    # This is done so that html entities like '&gt;' remain escaped.
    self.fed.append(f'&{name};')

  def handle_starttag(self, tag, attrs):
    if tag != "img":
      return
    tag_attrs = {at[0]: at[1] for at in attrs}
    if tag_attrs.get('class', '') == 'emoji':
      self.fed.append(emoji.get(tag_attrs.get('title', ':cow:'), ''))
      return
    self.fed.append(f"<a href=\"{tag_attrs.get('src', '#')}\">Image</a>")

  def handle_data(self, d):
    self.fed.append(d)

  def get_data(self):
    return "".join(self.fed)


class newsArticle:

  def __init__(self, author, topic, subject, date, raw_msg, raw_html,
               mention_manager):
    self.author_username = author[0]
    self.author_displayname = author[1]
    self.topic = topic
    self.subject = subject
    self.date = getHumanReadableDate(date)
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
    hdr = f"From: {self.author_username}({self.author_displayname})\r\n"\
        f"Newsgroup: {self.topic}\r\n"\
        f"Subject: {self.subject}\r\n"\
        f"Date: {self.date}\r\n"\
        f"is_plus_one: {self.isPlusOne()}"
    return "<code>" + html.escape(hdr) + "</code>\n\n"

  def parseMessage(self):
    if self.broken:
      return

    try:
      hdr = self.makeHeader()
      p = articleParser()
      p.feed(self.raw_html)
      content = p.get_data()
      if (len(content) > 4095):
        p = legacyParser()
        p.feed(self.raw_html)
        content = p.get_data()
      self.mention_manager.parseMentions(content, self.topic)
      self.content = hdr + content
    except Exception as e:
      print(e, datetime.datetime.now())
      traceback.print_exc()
      self.broken = True
