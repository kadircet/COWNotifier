import mistune
import string
import re

from emoji_codepoints import emoji
from logger import getLogger
"""Converts discourse markdown into a telegram compatible version."""

logger = getLogger(__name__)


def pluginEmoji(md):
  """Parses markdown emojis in the form of :smiley:

  Generates an `emoji` token with text inside colons.
  """

  def parseEmoji(self, m, state):
    return 'emoji', self.render(m.group(1), state)

  EMOJI_REGEX = r""":(\w+):"""
  md.inline.register_rule('emoji', EMOJI_REGEX, parseEmoji)
  md.inline.rules.append('emoji')


def pluginQuote(md):
  """Parser for discourse quote style.

  These are in the form of:
  [quote="$USER_NAME$, post:$POST_ID$, topic:$TOPIC_ID$(, full:true)"]
  QUOTED_TEXT
  [/quote]

  Generates a `quote` token with children set to $QUOTED_TEXT$ and params set to
  ($USER_NAME$, $POST_ID$, $TOPIC_ID$).
  """

  def parseQuote(self, m, state):
    params = m.group(1).split(',')
    username = params[0].strip()
    post_id = int(params[1].split(':')[1])
    topic_id = int(params[2].split(':')[1])
    return {
        'type': 'quote',
        'children': self.parse(m.group(2), state),
        'params': (username, post_id, topic_id, params[3:])
    }

  QUOTE_REGEX = re.compile(r'\[quote="(.*?)"\]\s*((.*?\n?)*?)\s*\[/quote\]\s*')
  md.block.register_rule('quote', QUOTE_REGEX, parseQuote)
  md.block.rules.append('quote')


def unescape(text):
  """Unescapes punctuation and drops markdown markers in text."""
  toEscape = {
      False: [
          '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|',
          '{', '}', '.', '!'
      ],
      True: ['`', '\\']
  }

  res = ''
  i = 0
  insideCodeBlock = False
  while i < len(text):
    # strip markdown markers.
    if text[i] in toEscape[insideCodeBlock]:
      if text[i] == '`':
        insideCodeBlock = not insideCodeBlock
      i += 1
      continue
    # if this is a backslash and the next char is punctuation, print that one
    # instead.
    if text[i] == '\\':
      if i + 1 < len(text) and text[i + 1] in toEscape[insideCodeBlock]:
        i += 1
    res += text[i]
    i += 1
  return res


def escape(text, inCodeBlock=False):
  """Escapes characters specified in toEscape by prepending bachslashes.

  By default toEscape is the list mentioned in telegram bot api.
  """
  if not inCodeBlock:
    toEscape = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|',
        '{', '}', '.', '!'
    ]
  else:
    toEscape = ['`', '\\']

  res = ''
  for t in text:
    if t in toEscape:
      res += '\\'
    res += t
  return res


class telegramRenderer(mistune.renderers.BaseRenderer):
  """Renderer to convert discourse markdown into telegram supported dialect."""
  NAME = 'telegram'
  IS_TREE = True
  UPLOAD_SCHEME = 'upload://'

  def __init__(self):
    super(telegramRenderer, self).__init__()

  def createDefaultHandler(self, name):
    logger.error('Creating default method for unhandled rule: {}', name)

    def __unknown(*args):
      logger.error('Unhandled rule {} with data: {}', name, args)
      return ''

    return __unknown

  def _get_method(self, name):
    try:
      return super(telegramRenderer, self).__getattribute__(name)
    except:
      return self.createDefaultHandler(name)

  def paragraph(self, children):
    logger.debug('paragraph: {}', children)
    return ''.join(children)

  def text(self, text):
    logger.debug('text: {}', text)
    return escape(text)

  def emoji(self, children):
    logger.debug('emoji: {}', children)
    text = f':{"".join(children)}:'
    return emoji.get(text, f'{text}')

  def list(self, children_and_levels, ordered, depth, start=None):
    logger.debug('list: {} {} {} {}', children_and_levels, ordered, depth,
                 start)
    if start is None:
      start = 1
    res = []
    base_padding = '  ' * (depth - 1)
    for children, level in children_and_levels:
      padding = '  ' * level + base_padding
      cur = []
      for child in children:
        bullet = (str(start) + '\\.') if ordered else '\\-'
        start += 1
        cur.append(f'{padding}{bullet} {child}')
      res.append('\n'.join(cur))
    return '\n'.join(res)

  def list_item(self, children, level):
    logger.debug('list_item: {}', children, level)
    return children, level - 1

  def block_text(self, children):
    logger.debug('block_text: {}', children)
    return ''.join(children)

  def heading(self, children, level):
    logger.debug('heading: {}', children)
    return ''.join(children)

  def strong(self, children):
    logger.debug('strong: {}', children)
    return f'*{"".join(children)}*'

  def emphasis(self, children):
    logger.debug('emphasis: {}', children)
    return f'_{"".join(children)}_'

  def block_code(self, children, info=None):
    logger.debug('code: {} {}', children, info)
    text = '```'
    if info is not None:
      text += escape(info.split()[0], True)
    text += '\n'
    text += escape(''.join(children), True)
    text += '\n```'
    return text

  def link(self, link, text=None, title=None):
    logger.debug('link: {} {} {}', link, text, title)
    if link.startswith(self.UPLOAD_SCHEME):
      link = 'https://cow.ceng.metu.edu.tr/uploads/short-url/' + link[
          len(self.UPLOAD_SCHEME):]
    if text is None:
      if title is None:
        text = link
      else:
        text = title
    text = escape(text)
    return f'[{text}]({link})'

  def image(self, src, alt='', title=None):
    logger.debug('image: {} {} {}', src, alt, title)
    if title is None:
      title = alt
    if not title:
      title = 'Image'
    if src.startswith(self.UPLOAD_SCHEME):
      src = 'https://cow.ceng.metu.edu.tr/uploads/short-url/' + src[
          len(self.UPLOAD_SCHEME):]
    #TODO(kadircet): Also send photos as attachments
    return f'[{escape(title)}]({src})'

  def quote(self, children, user, post_id, topic_id, *args):
    logger.debug('quote: {} {} {} {}', user, post_id, topic_id, children,
                 ''.join(*args))
    text = '\n\n'.join(children).replace('\n', '\n\\> ')
    return (f'\\> [@{user}](https://cow.ceng.metu.edu.tr/u/{user}) in '
            f'[post](https://cow.ceng.metu.edu.tr/t/{topic_id}/{post_id}):\n'
            f'\\> _{text}_')

  def codespan(self, text):
    logger.debug('codespan: {}', text)
    return f'`{text}`'

  def thematic_break(self):
    logger.debug('thematic_break')
    return escape('---')

  def block_quote(self, children):
    logger.debug('block_quote: {}', children)
    text = '\n\n'.join(children).replace('\n', '\n\\> ')
    return f'\\> _{text}_'

  def linebreak(self):
    logger.debug('linebreak')
    return '\n'

  def newline(self):
    logger.debug('newline')
    return '\n'

  def inline_html(self, text):
    logger.debug('inline_html {}', text)
    return escape(text)


def convertDiscourseToTelegram(content):
  logger.debug(f'Got discourse markdown: {content}')
  renderer = telegramRenderer()
  paragraphs = mistune.markdown(
      content, renderer=renderer, plugins=[pluginEmoji, pluginQuote])
  return paragraphs
