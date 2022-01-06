# basedcount_bot ⣿
# FAQ: https://reddit.com/r/basedcount_bot/comments/iwhkcg/basedcount_bot_info_and_faq/

# Python Libraries
import json
from typing import List
import praw
from datetime import timedelta, datetime
import traceback
from subprocess import call
from os import path
import signal
import time
import re
from pymongo import MongoClient
from praw.reddit import Reddit
from praw.exceptions import APIException
from retrie.trie import Trie
from retrie.retrie import Replacer

# basedcount_bot Libraries
from commands import based, myBasedCount, basedCountUser, mostBased, removePill
from flairs import checkFlair
from passwords import bot, bannedWords, modPasswords
from cheating import checkForCheating, sendCheatReport
from backupDrive import backupDataBased


# Connect to Reddit

version = "Bot v2.11.0"
infoMessage = (
    "I am a bot created to keep track of how based users are. "
    "Check out the [FAQ](https://reddit.com/r/basedcount_bot/comments/iwhkcg/basedcount_bot_info_and_faq/). "
    "I also track user [pills](https://reddit.com/r/basedcount_bot/comments/l23lwe/basedcount_bot_now_tracks_user_pills/).\n\n"
    "If you have any suggestions or questions, please message them to me with the subject "
    'of "Suggestion" or "Question" to automatically forward them to a human operator.\n\n'
    "> based - adj. - to be in possession of viewpoints acquired through logic or observation "
    "rather than simply following what your political alignment dictates, "
    "often used as a sign of respect but not necessarily agreement\n\n"
    + version
    + "\n\n"
    "**Commands: /info | /mybasedcount | /basedcount username | /mostbased | /removepill pill**"
)

# Vocabulary
excludedAccounts = ["basedcount_bot", "VredditDownloader"]
excludedParents = ["basedcount_bot"]


def make_re(words: List[str], starts=False) -> re.Pattern:
    trie = Trie()
    for word in words:
        trie.add(word)
    return re.compile(("^" if starts else "") + trie.pattern())


botName_Variations = Replacer(
    {
        k: ""
        for k in [
            "/u/basedcount_bot ",
            "u/basedcount_bot ",
            "basedcount_bot ",
            "/u/basedcount_bot",  # /u/is the bot's username
            "u/basedcount_bot",
            "basedcount_bot",
        ]
    },
    match_substrings=False,  # TODO: discuss whether I should be removing substrings
)  # I can't tell if removing substrings is a bug or a features

based_Variations = make_re(
    [
        "based",
        "baste",
        "basado",
        "basiert",
        "basato",
        "fundiert",
        "fondatum",
        "bazita",
        "מבוסס",
        "oparte",
        "bazowane",
        "basé",
        "baseado",
        "gebaseerd",
        "bazirano",
        "perustuvaa",
        "perustunut",
        "основано",
        "基于",
        "baseret",
        "بايسد, ",
        "na základě",
        "basert",
        "bazirano",
        "baserad",
        "basat",
        "ベース",
        "bazat",
        "berdasar",
        "Базирано",
        "gebasseerd",
        "Oj +1 byczq +1",
        "Oj+1byczq+1",
    ]
)
based_Varations_blacklist = make_re(["based on", "based for"])

pillExcludedStrings_start = make_re(
    [
        "based",
        "baste",
        "and ",
        "but ",
        "and-",
        "but-",
        " ",
        "-",
        "r/",
        "/r/",
        "basado",
        "basiert",
        "basato",
        "fundiert",
        "fondatum",
        "bazita",
        "מבוסס",
        "oparte",
        "bazowane",
        "basé",
        "baseado",
        "gebaseerd",
        "bazirano",
        "perustuvaa",
        "perustunut",
        "основано",
        "基于",
        "baseret",
        "بايسد, ",
        "na základě",
        "basert",
        "bazirano",
        "baserad",
        "basat",
        "ベース",
        "bazat",
        "berdasar",
        "Базирано",
        "gebasseerd",
        "Oj +1 byczq +1",
        "Oj+1byczq+1",
    ],
    starts=True,
)

pillExcludedStrings_end = [" and", " but", " ", "-"]

myBasedCount_Variations = ["/mybasedcount"]
basedCountUser_Variations = ["/basedcount"]
mostBased_Variations = ["/mostbased"]

backupDataBased()


class BasedBot(Reddit):
    def __init__(self, config):
        self.config = config

        super().__init__(
            client_id=config.client_id,
            client_secret=config.client_secret,
            user_agent=config.user_agent,
            username=config.username,
            password=config.password,
        )

        self.active: bool = True

        self.mongo_client = MongoClient(config.mongo_url)
        self.db = self.mongo_client.dataBased
        self.sub = self.subreddit(config.subreddit)
        self.backup()

    def backup(self):
        backupDataBased()  # TODO: Implement backup functionality into bot/cron job

    def process_command(self, *data):
        ...  # TODO

    def checkMail(self):
        inbox = self.inbox.unread(limit=30)
        for message in inbox:
            message.mark_read()
            currentTime = datetime.now().timestamp()
            if (message.created_utc > (currentTime - 180)) and (
                message.was_comment is False
            ):
                content = str(message.body)
                author = str(message.author)
                subject = str(message.subject).lower()
                # --------- Check Questions and Suggestions and then reply
                if any([x in subject for x in ["question", "suggestion"]]):

                    self.redditor(
                        bot.admin
                    ).message(  # message admin first to not send a false positive
                        str(message.subject) + " from " + author, content
                    )

                    if "suggestion" in subject:
                        message.reply(
                            "Thank you for your suggestion. I have forwarded it to a human operator."
                        )
                    else:
                        message.reply(
                            "Thank you for your question. I have forwarded it to a human operator, and I should reply shortly with an answer."
                        )

                # --------- Check for mod commands
                for mpass in modPasswords:
                    if content.startswith(mpass.password):
                        if author == mpass.user:
                            cleanContent = content.replace(mpass.password + " ", "")
                            if cleanContent.startswith("/removepill "):
                                cleanContent = cleanContent.replace("/removepill ", "")
                                user_pill_split = cleanContent.split(" ", 1)
                                replyMessage = removePill(
                                    user_pill_split[0], user_pill_split[1]
                                )
                            break  # useless iteration

                # --------- Check for user commands
                if "/info" in content.lower():
                    message.reply(infoMessage)

                for v in myBasedCount_Variations:
                    if v in content.lower():
                        replyMessage = myBasedCount(author)
                        message.reply(replyMessage)
                        break

                for v in basedCountUser_Variations:
                    if v in content.lower():
                        replyMessage = basedCountUser(content)
                        message.reply(replyMessage)
                        break

                for v in mostBased_Variations:
                    if v in content.lower():
                        replyMessage = mostBased()
                        message.reply(replyMessage)
                        break

                if content.lower().startswith("/removepill"):
                    replyMessage = removePill(author, content)
                    message.reply(replyMessage)

    def readComments(self):
        try:
            for comment in self.sub.stream.comments(skip_existing=True):
                if not self.active:
                    break

                self.checkMail()

                # Get data from comment
                author = str(comment.author)
                if author in excludedAccounts:
                    return

                # Remove bot mentions from comment text
                commenttext = str(botName_Variations.replace(comment.body)).lower()

                # ------------- Based Check

                if (based_Variations.match(commenttext) is not None) and (
                    based_Varations_blacklist.match(commenttext) is None
                ):

                    # Get data from parent comment
                    parent = str(comment.parent())
                    parentComment = self.comment(id=parent)

                    # See if parent is comment (pass) or post (fail)
                    try:
                        parentAuthor = str(parentComment.author)
                        parentTextHandler = parentComment.body
                        parentText = str(parentTextHandler).lower()
                        parentFlair = parentComment.author_flair_text
                    except:
                        parentAuthor = str(comment.submission.author)
                        parentText = "submission is a post"
                        parentFlair = comment.submission.author_flair_text
                    flair = str(checkFlair(parentFlair))

                    # Make sure bot isn't the parent
                    if (
                        (parentAuthor not in excludedParents)
                        and (parentAuthor not in author)
                        and (comment.author_flair_text != "None")
                    ):

                        # Check for cheating
                        cheating = False
                        for v in based_Variations:
                            if parentText.lower().startswith(v) and (
                                len(parentText) < 50
                            ):
                                cheating = True

                        # Check for pills
                        pill = "None"
                        if "pilled" in commenttext.lower():
                            pill = commenttext.lower().partition("pilled")[0]
                            if (len(pill) < 70) and ("." not in pill):

                                # Clean pill string beginning
                                pillClean = 0
                                while pillClean < len(pillExcludedStrings_start):
                                    for pes in pillExcludedStrings_start:
                                        if pill.startswith(pes):
                                            pill = pill.replace(pes, "", 1)
                                            pillClean = 0
                                        else:
                                            pillClean += 1

                                # Clean pill string ending
                                pillClean = 0
                                while pillClean < len(pillExcludedStrings_end):
                                    for pes in pillExcludedStrings_end:
                                        if pill.endswith(pes):
                                            pill = pill[:-1]
                                            pillClean = 0
                                        else:
                                            pillClean += 1
                            else:
                                pill = "None"

                            # Make sure pill is acceptable
                            for w in bannedWords:
                                if w in pill:
                                    pill = "None"

                        # Calculate Based Count and build reply message
                        if not cheating:
                            if flair != "Unflaired":
                                replyMessage = based(parentAuthor, flair, pill)

                                # Build list of users and send Cheat Report to admin
                                checkForCheating(author, parentAuthor)

                            # Reply
                            else:
                                break
                                # replyMessage = "Don't base the Unflaired scum!"
                            if replyMessage:
                                comment.reply(replyMessage)
                            break

                # ------------- Commands
                if commenttext.lower().startswith("/info"):
                    comment.reply(infoMessage)

                for v in myBasedCount_Variations:
                    if v in commenttext.lower():
                        replyMessage = myBasedCount(author)
                        comment.reply(replyMessage)
                        break

                for v in basedCountUser_Variations:
                    if commenttext.lower().startswith(v):
                        replyMessage = basedCountUser(commenttext)
                        comment.reply(replyMessage)
                        break

                for v in mostBased_Variations:
                    if v in commenttext.lower():
                        replyMessage = mostBased()
                        comment.reply(replyMessage)
                        break

                if commenttext.lower().startswith("/removepill"):
                    replyMessage = removePill(author, commenttext)
                    comment.reply(replyMessage)
                    break

        # - Exception Handler
        except APIException as e:
            if e.error_type == "RATELIMIT":
                delay = re.search(r"(\d+) minutes?", e.message)
                if delay:
                    delay_seconds = float(int(delay.group(1)) * 60)
                    time.sleep(delay_seconds)
                    self.readComments()
                else:
                    if delay := re.search(r"(\d+) seconds", e.message):
                        delay_seconds = float(delay.group(1))
                        time.sleep(delay_seconds)
                        self.readComments()
            else:
                print(e.message)

    def run(self):
        while self.active:
            self.checkMail()
            self.readComments()

    def closeBot(self):
        self.active = False
        sendCheatReport()
        print("Shutdown complete.")

    def stop_signal(self, _signum, _frame):
        self.closeBot()

    # /info
    # starts with /
    #  info args[0] arguments = args[1:]

    def command_info(self, message):
        message.reply(infoMessage)


if __name__ == "__main__":
    from signal import signal

    based_bot = BasedBot(bot)

    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal(sig, based_bot.stop_signal)

    based_bot.run()
