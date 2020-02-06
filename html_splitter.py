class HTMLSplitter(HTMLParser):
  # Splits a given html into 4095 byte chunks while keeping each chunk as a
  # valid html
  def __init__(self):
    super(MyParser, self).__init__(convert_charrefs=False)
    self.opened_tags = []
    self.parsed_msgs = []
    self.current_msg = []

  def getOpeningTagsLen(self):
    return sum(len(f'<{tag+attrs}>') for tag, attrs in self.opened_tags)

  def getClosingTagsLen(self):
    return sum(len(f'</{tag}>') for tag, attrs in self.opened_tags)

  def getCurrentMsgLen(self):
    return sum(len(item) for item in self.current_msg)

  def getTotalMsgLen(self):
    return self.getClosingTagsLen() + self.getCurrentMsgLen()

  def finishMsg(self):
    for tag, attrs in self.opened_tags[::-1]:
      self.current_msg.append(f'</{tag}>')
    parsed = ''.join(self.current_msg)
    self.parsed_msgs.append(parsed)
    self.current_msg = []
    for tag, attrs in self.opened_tags:
      self.current_msg.append(f'<{tag+attrs}>')

  def handle_entityref(self, name):
    unescaped = f'&{name};'
    cur_len = self.getCurrentMsgLen()
    closing_len = self.getClosingTagsLen()
    if cur_len + closing_len + len(unescaped) > 4095:
      self.finishMsg()
    self.current_msg.append(unescaped)

  def handle_starttag(self, tag, attrs):
    if (self.getOpeningTagsLen() + self.getClosingTagsLen()) > 4095:
      print("Too many opening tags without closing")
      self.reset()
      return
    attr_list = [f'{at[0]}="{at[1]}"' for at in attrs]
    attr_str = ' '.join([''] + attr_list)
    tag_len = len(f'<{ptag+attr_str}>')
    tag_close_len = len(f'</{ptag}>')
    cur_len = self.getCurrentMsgLen()
    closing_len = self.getClosingTagsLen()
    if cur_len + closing_len + tag_len + tag_close_len > 4095:
      self.finishMsg()
      self.opened_tags.append((ptag, attr_str))
      self.current_msg.append(f'<{ptag+attr_str}>')

  def handle_data(self, data):
    while len(data):
      cur_len = self.getCurrentMsgLen() + self.getClosingTagsLen()
      remaining = 4095 - cur_len
      if remaining <= 0:
        self.finishMsg()
      remaining = max(remaining, 0)
      self.current_msg.append(data[:remaining])
      data = data[remaining:]

  def handle_endtag(self, tag):
    popped = self.opened_tags.pop()[0]
    assert tag == popped, "Tag mismatch"
    self.current_msg.append(f'</{tag}>')

  def get_messages(self):
    self.close()
    self.finishMsg()
    return self.parsed_msgs

  def reset(self):
    self.opened_tags = []
    self.parsed_msgs = []
    self.current_msg = []
    self.dup_newline = False
    super(MyParser, self).reset()