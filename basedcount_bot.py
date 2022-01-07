# basedcount_bot ⣿
# FAQ: https://reddit.com/r/basedcount_bot/comments/iwhkcg/basedcount_bot_info_and_faq/

# Python Libraries
from typing import List, Optional
from datetime import datetime
import signal
import random
import re
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from asyncpraw.reddit import Comment, Reddit, Redditor, Subreddit
from asyncpraw.exceptions import APIException
from retrie.trie import Trie
from retrie.retrie import Replacer
import asyncio
from flairs import checkFlair
from backupDrive import backupDataBased
import logging
import os 
import ranks

# I'm going to use an environment PRODUCTION to differentiate between production and development
if os.getenv("PRODUCTION", "0") == "1":
    log_level = logging.INFO
    bot = object()
    bannedWords = []
    modPasswords = []
else:
    log_level = logging.DEBUG
    from passwords import bot, bannedWords, modPasswords # I know this is bad but I don't have passwords to work with

logging.basicConfig(level=log_level)

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

noUserReplies = {
    "myBased": [
        "Hmm... I don't see you in my records, as it appears you aren't very based. I guess nobody's perfect.",
        "[mybasedcount_clever_response_1](https://www.youtube.com/watch?v=YzKM5g_FwYU&ab_channel=TheMar%C3%ADas)",
        "[mybasedcount_clever_response_2](https://www.youtube.com/watch?v=PNbBDrceCy8&ab_channel=TheWhoVEVO)",
        "[mybasedcount_clever_response_3](https://i.kym-cdn.com/photos/images/original/001/535/068/29d.jpg)",
        "[mybasedcount_clever_response_4](https://qph.fs.quoracdn.net/main-qimg-3999c004b514b9bfc6ba09527bfcd724)",
        "[mybasedcount_clever_response_5](https://media1.giphy.com/media/Q7LP0tm86sBWIqjFCL/giphy.gif)",
        "[mybasedcount_clever_response_6](https://www.youtube.com/watch?v=KeLtNnHEipA&ab_channel=AlltheAnime)",
        "[mybasedcount_clever_response_7](https://www.youtube.com/watch?v=pmGNo8RL5kM&ab_channel=YeahYeahYeahsVEVO)",
        "[mybasedcount_clever_response_8](https://www.youtube.com/watch?v=M5QGkOGZubQ&ab_channel=Fayroe)",
    ],
    "basedCount": [
        "Yeah... I got nothing.",
        "[basedcount_clever_response_1](https://www.youtube.com/watch?v=XXJ99MJ67gw&ab_channel=pepperjackcheese1)",
        "[basedcount_clever_response_2](https://pics.me.me/never-met-him-trump-be-like-18509974.png)",
        "[basedcount_clever_response_3](https://www.youtube.com/watch?v=ZTFfdEeB6j8&ab_channel=EnglishSingsing)",
        "[basedcount_clever_response_4](https://media1.giphy.com/media/Q7LP0tm86sBWIqjFCL/giphy.gif)",
        "[basedcount_clever_response_5](https://i.pinimg.com/originals/cd/c5/ff/cdc5ffaf883b13e7bcd834e464ab971a.png)",
        "[basedcount_clever_response_6](https://www.youtube.com/watch?v=Cs57e-viIKw&ab_channel=ButtonsTheDragon)",
        "[basedcount_clever_response_7](https://www.youtube.com/watch?v=tOlh-g2dxrI&ab_channel=e7magic)",
    ],
}

based_list = [
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

based_Variations = make_re(
    based_list
)
based_Varations_blacklist = make_re(["based on", "based for"])

pillExcludedStrings_start = Replacer(
    {
        k: ""
        for k in 
    [
        'and ', 'but ', 'and-', 'but-', ' ', '-', 'r/', '/r/', *based_list
    ]},
    match_substrings=False,  # TODO: discuss whether I should be removing substrings for pill replacer
)

pillExcludedStrings_end = Replacer(
    {
        k: ""
        for k in 
    [" and", " but", " ", "-"]
    },
)

myBasedCount_Variations = ["/mybasedcount"]
basedCountUser_Variations = ["/basedcount"]
mostBased_Variations = ["/mostbased"]

backupDataBased()


class BasedBot(Reddit):
    def __init__(self, config, loop = None):
        self.loop = loop or asyncio.get_event_loop()

        self.config = config

        super().__init__(
            client_id=config.client_id,
            client_secret=config.client_secret,
            user_agent=config.user_agent,
            username=config.username,
            password=config.password,
        )

        self.active: bool = True
        self._admin : Optional[Redditor] = None 
        self.backup()
        self.log = logging.getLogger("BasedBot")
        asyncio.create_task(self.setup())

    async def setup(self):
        self.sub : Subreddit = await self.subreddit(self.config.subreddit, fetch=True) # we're doing it once so might as well get a bit more info   
        self.log.info("Subreddit: %s", self.sub.name)
        self.mongo_client : AsyncIOMotorClient = AsyncIOMotorClient(self.config.mongo_uri)
        self.db : AsyncIOMotorDatabase = self.mongo_client.dataBased
        self.log.debug("Connected to MongoDB")

    async def get_admin(self) -> Redditor:
        if self._admin is None:
            self._admin = await self.redditor(self.config.admin, fetch = True)
            
        return self._admin 
        
    def backup(self):
        backupDataBased()  # TODO: Implement backup functionality into bot/cron job

    def process_command(self, *data):
        ...  # TODO

    async def checkMail(self):
        async for message in self.inbox.unread():
            if not self.active:
                break
            message.mark_read()
            currentTime = datetime.now().timestamp()

            if isinstance(message, Comment):
                continue
            if message.created_utc > (currentTime - 180):
                content = str(message.body)
                author = str(message.author)
                subject = str(message.subject).lower()
                # --------- Check Questions and Suggestions and then reply
                if any([x in subject for x in ["question", "suggestion"]]):
                    admin = await self.get_admin()
                    await admin.message(  # message admin first to not send a false positive
                        str(message.subject) + " from " + author, content
                    )

                    if "suggestion" in subject:
                        await message.reply(
                            "Thank you for your suggestion. I have forwarded it to a human operator."
                        )
                    else:
                        await message.reply(
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
                                replyMessage = await self.removePill(
                                    user_pill_split[0], user_pill_split[1]
                                )
                            break  # useless iteration

                # --------- Check for user commands
                if "/info" in content.lower():
                    await message.reply(infoMessage)

                for v in myBasedCount_Variations:
                    if v in content.lower():
                        replyMessage = await self.myBasedCount(author)
                        await message.reply(replyMessage)
                        break

                for v in basedCountUser_Variations:
                    if v in content.lower():
                        replyMessage = await self.basedCountUser(content)
                        await message.reply(replyMessage)
                        break

                for v in mostBased_Variations:
                    if v in content.lower():
                        replyMessage = await self.mostBased()
                        await message.reply(replyMessage)
                        break

                if content.lower().startswith("/removepill"):
                    replyMessage = await self.removePill(author, content)
                    await message.reply(replyMessage)

    async def readComments(self):
        try:
            async for comment in self.sub.stream.comments(skip_existing=True):
                if not self.active:
                    break

                # Get data from comment
                author = str(comment.author)
                if author in excludedAccounts:
                    return

                # Remove bot mentions from comment text
                commenttext = str(botName_Variations.replace(comment.body)).lower()

                # ------------- Based Check

                if ( based_Variations.match(commenttext) is not None) and (
                    based_Varations_blacklist.match(commenttext) is None
                ):
                    #_ = match.group(0) # used in the future if I need what the user said
                    # Get data from parent comment
                    parent = str(comment.parent())
                    parentComment = await self.comment(id=parent)

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
                        cheating = based_Variations.match(parentText.lower()) is not None and len(parentText) < 50

                        # Check for pills
                        pill = "None"
                        if "pilled" in commenttext.lower():
                            pill = commenttext.lower().partition("pilled")[0]
                            if (len(pill) < 70) and ("." not in pill):

                                # Clean pill string beginning
                                pill = pillExcludedStrings_start.replace(pill)

                                # Clean pill string ending
                                pill = pillExcludedStrings_end.replace(pill)
                            else:
                                pill = "None"

                            # Make sure pill is acceptable
                            for w in bannedWords:
                                if w in pill:
                                    pill = "None"

                        # Calculate Based Count and build reply message
                        if not cheating:
                            if flair != "Unflaired":
                                replyMessage = await self.based(parentAuthor, pill)

                                # Build list of users and send Cheat Report to admin
                                await self.checkForCheating(author, parentAuthor)

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
                        replyMessage = await self.myBasedCount(author)
                        comment.reply(replyMessage)
                        break

                for v in basedCountUser_Variations:
                    if commenttext.lower().startswith(v):
                        replyMessage = await self.basedCountUser(commenttext)
                        comment.reply(replyMessage)
                        break

                for v in mostBased_Variations:
                    if v in commenttext.lower():
                        replyMessage = await self.mostBased()
                        comment.reply(replyMessage)
                        break

                if commenttext.lower().startswith("/removepill"):
                    replyMessage = await self.removePill(author, commenttext)
                    comment.reply(replyMessage)
                    break

        # - Exception Handler
        except APIException as e:
            if e.error_type == "RATELIMIT": # this is a bad implementation but I don't know the responses so I'm just going to keep it
                delay = re.search(r"(\d+) minutes?", e.message)
                if delay:
                    delay_seconds = float(int(delay.group(1)) * 60)
                    await asyncio.sleep(delay_seconds)
                else:
                    if delay := re.search(r"(\d+) seconds", e.message):
                        delay_seconds = float(delay.group(1))
                        await asyncio.sleep(delay_seconds)
            else:
                print(e.message)

    async def run(self):
        mail_task = asyncio.create_task(self.checkMail())
        read_task = asyncio.create_task(self.readComments())
        return await asyncio.gather(*[mail_task, read_task])

    async def closeBot(self):
        self.active = False
        await self.sendCheatReport()
        print("Shutdown complete.")

    async def stop_signal(self, _signum, _frame):
        return await self.closeBot()

    # cheating detection 
    async def checkForCheating(self, user: str, parentAuthor: str) -> None:
        # Add users to database
        userProfile = await self.db.basedHistory.find_one({"name": user})
        if userProfile is None:
            await self.db.basedHistory.update_one(
                {"name": user}, {"$set": {parentAuthor: 1}}, upsert=True
            )
        else:
            if parentAuthor not in userProfile:
                await self.db.basedHistory.update_one({"name": user}, {"$set": {parentAuthor: 1}})
            else:
                await self.db.basedHistory.update_one(
                    {"name": user}, {"$set": {parentAuthor: userProfile[parentAuthor] + 1}}
                )


    async def sendCheatReport(self):
        # Add Suspicious Users
        content = "" # TODO: figiure out wtf is this nonsense
        async for user in self.db.basedHistory.find({}):
            for key in user.keys():
                if key != "_id" and key != "name":
                    if user[key] > 5:
                        content = (
                            content
                            + user["name"]
                            + " based "
                            + str(key)
                            + " "
                            + str(user[key])
                            + " times.\n"
                        )

        # Send Cheat Report to Admin
        if content != "":
            admin = await self.get_admin()
            await admin.message("Cheat Report", content)

        await self.db.basedHistory.delete_many({})


    # User Commands 
    async def based(self, user, pill):

        # Retrieve User Data
        count = await self.addBasedCount(user)
        pills = await self.addPill(user, pill)
        rank = ranks.rankName(int(count), user)
        rankUp = ranks.rankMessage(int(count))

        # Build Reply Message
        replyMessage = ""
        if (int(count) % 5) == 0:
            replyMessage = (
                "u/"
                + user
                + "'s Based Count has increased by 1. Their Based Count is now "
                + str(count)
                + ". \n\n Rank: "
                + rank
                + "\n\n Pills: "
                + pills
                + "\n\n I am a bot. Reply /info for more info."
            )
            if rankUp:
                replyMessage = (
                    "u/"
                    + user
                    + "'s Based Count has increased by 1. Their Based Count is now "
                    + str(count)
                    + ". \n\n Congratulations, u/"
                    + user
                    + "! You have ranked up to "
                    + rank
                    + "! "
                    + rankUp
                    + "\n\n Pills: "
                    + pills
                )
        elif int(count) == 1:
            replyMessage = (
                "u/"
                + user
                + " is officially based! Their Based Count is now 1. \n\n Rank: House of Cards"
                + "\n\n Pills: "
                + pills
                + "\n\n I am a bot. Reply /info for more info."
            )
        return replyMessage


    async def myBasedCount(self, user):

        # Retrieve User Data
        count = await self.checkBasedCount(user)
        pills = await self.getPills(user)

        # Build Reply Message
        if int(count) > 0:
            rank = ranks.rankName(int(count), user)
            replyMessage = (
                "Your Based Count is "
                + str(count)
                + ". \n\n"
                + "Rank: "
                + rank
                + "\n\n"
                + "Pills: "
                + ', '.join(pills)
            )
        else:
            replyMessage = random.choice(noUserReplies["myBased"])
        return replyMessage


    async def basedCountUser(self, string):

        # Take comment text string and remove everything except the username
        excludedStrings = ["/u/", "u/", "basedcount_bot ", "/basedcount "]
        for s in excludedStrings:
            if s in string:
                string = string.replace(s, "")
        user = string

        # Retrieve User Data
        count = str(await self.checkBasedCount(user))
        pills = await self.getPills(user)

        # Build Reply Message
        if int(count) > 0:
            rank = ranks.rankName(int(count), user)
            replyMessage = (
                user
                + "'s Based Count is "
                + count
                + ". \n\n"
                + "Rank: "
                + rank
                + "\n\n"
                + "Pills: "
                + pills
            )
        else:
            replyMessage = random.choice(noUserReplies["basedCount"])
        return replyMessage


    async def mostBased(self):
        mostCountFlair = []
        u = 1
        async for r in self.db.dataBased.find().sort("count", -1).limit(10):
            mostUserName = r["name"]
            mostCount = str(r["count"])
            mostFlair = r["flair"]
            mostCountFlair.append(
                str(
                    str(u)
                    + ". "
                    + mostUserName
                    + "  |  "
                    + mostCount
                    + "  |  "
                    + mostFlair
                )
            )
            u += 1

        # Build Reply Message
        replyMessage = (
            "--The Top 10 Most Based Users--\n\n"
            + "\n\n".join(mostCountFlair)
        )
        return replyMessage


    # === Databased Searching and Updating ===


    async def addBasedCount(self, user) -> int:
        # Check if existing user and calculate based count
        doc = await self.db.databased.find_one_and_update({"name":user}, {"$setOnInsert":{"pills":[]}, "$inc": {"count": 1}}, return_document=ReturnDocument.AFTER)
        return doc['count']

    async def checkBasedCount(self, user) -> int:
        userProfile = await self.db.dataBased.find_one({"name": user})
        if userProfile == None:
            return 0
        else:
            return userProfile['count']

    async def getPills(self, user) -> List[str]:

        # Check if existing user and calculate pill list
        userProfile = await self.db.dataBased.find_one({"name": user})
        return (userProfile or {}).get("pills", [])


    async def addPill(self, user, pill):
        # Check if user exists
        data = await self.db.dataBased.find_one_and_update({"name":user}, {"$addToSet": {"pills": pill}}, return_document=ReturnDocument.AFTER)
        return data['pills']


    async def removePill(self, user, pill):
        # Parse data and get the bare string
        data = await self.db.dataBased.find_one_and_update({"name": user}, {"$pull": {"pills": {"$eq": pill}}}, return_document=ReturnDocument.AFTER)
        # Build Reply Message
        return "Pill removed. Your pills: " + ", ".join(data['pills'])

if __name__ == "__main__":
    from signal import signal
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    based_bot = BasedBot(bot, loop=loop)

    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal(sig, lambda *a: asyncio.create_task(based_bot.stop_signal(*a)))

    loop.run_until_complete(based_bot.run())
