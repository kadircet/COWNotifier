# COWNotifier
Get notifications via a Telegram bot for your favorite news groups.
Generic server allows multiple users to create and manage followlist
within a news server and get notifications whenever a new post has
been made to one of those groups.

## Usage
### Server side
Clone the repo then edit driver.py's `getConfig` function for the first
setup, by giving the Telegram Bot's token, your server's URL etc. Function
is self-explanatory. Then run `driver.py`.

### Bot Side
/start - Create a record within the server for the followlist<br/>
/add TOPICNAME - Adds topic to your followlist, in addition to exact
                 topic name, it also tries to match the name by prepending
                 metu.ceng. or metu.ceng.course. to the given parameter,
                 a spesific help for METU CENG users. Can be tweaked within
                 newsreader.py's closest fuction.<br/>
/delete TOPICNAME - Deletes given topic from your followlist<br/>
/list - Shows your followlist entries.<br/>
/help - Prints out command's and basic info about usage<br/>

---

There's a working bot telegram.me/cownotifbot but it's only available to
metu ceng newsgroup, you can simply create a new bot and give token to
server's config and create a bot for your own server.
