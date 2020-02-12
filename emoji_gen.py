import requests

URL = "https://gist.githubusercontent.com/hbostann/b95739045411eec0518d282b91c258f2/raw/dc6178933d75b3159c544d4fbb4303b126c5a317/EmojiCheatsheet"


def generateEmojiFile(filename):
  resp = requests.get(URL)
  with open(filename, 'w', encoding='utf-8') as emoji_codepoints:
    emoji_codepoints.write("# Generated\n\nemoji = {\n")
    for line in resp.text.splitlines():
      name, code = line.split(",")
      name = name.strip()
      code = code.strip()
      emoji_codepoints.write(f" u'{name}': u'{code}',\n")
    emoji_codepoints.write("}\n")
