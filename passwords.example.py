# Sensitive and Important Data

class Bot:
    def __init__(
        self,
        client_id,
        client_secret,
        user_agent,
        username,
        password,
        admin,
        mPassword,
        subreddit="PoliticalCompassMemes",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self.admin = admin
        self.mPassword = mPassword
        self.subreddit = subreddit


# include bot login data here
bot = Bot()

# Save locations
savePath = '/Desktop/basedcount_bot/'
backupSavePath = '/Desktop/Backup/'

bannedWords = []