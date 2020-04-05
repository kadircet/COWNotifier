import logging


class Message:

  def __init__(self, fmt, args):
    self.fmt = fmt
    self.args = args

  def __str__(self):
    return self.fmt.format(*self.args)


class StyleAdapter(logging.LoggerAdapter):

  def __init__(self, logger, extra=None):
    super(StyleAdapter, self).__init__(logger, extra or {})

  def log(self, level, msg, *args, **kwargs):
    if self.isEnabledFor(level):
      msg, kwargs = self.process(msg, kwargs)
      self.logger._log(level, Message(msg, args), (), **kwargs)


def getLogger(name):
  return StyleAdapter(logging.getLogger(name))
