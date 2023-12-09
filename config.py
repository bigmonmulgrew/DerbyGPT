# Configuration variables
#Import toeksn that are ignored by git
from tokens import DISCORD_TOKEN as DT
from tokens import OPENAI_TOKEN as OT

# The settings for Discord
DISCORD_TOKEN =  DT
MY_USER_ID = '249591687280721920'   # User ID of BigmonD
MY_GUILD_ID = 1156585341411655710   # Guild ID of Derby computing Discord
BOT_USER_ID = 1170451102022504553   # ChatGPT's user ID
CHAT_CHANNEL = 1156585342007251042  # Id of the channel the bot will chat in casually.
MEME_CHANNEL = 1156585342007251044  # ID of the memes channel
SOS_CHANNEL = 1169946506023948319   # ID of the channel to respond to SoS messages in.
DEBUG_CHANNEL = 1170789197393703003 # Same as chat channel but we use a hidden chgannel when debuggin things that might be spammy

# The token for ChatGPT
OPENAI_TOKEN = OT

#Timing calculations to check the bots response time
# Initial response delay in seconds (e.g., 0.5 to 5 minutes)
MIN_RESPONSE_DELAY = 1 * 60  # X
MAX_RESPONSE_DELAY = 15 * 60  # Y

# Min and max will trend towards these when discord is inactive
# Maximum delay cap (e.g., 30 min to 6 hours)
MAX_MIN_RESPONSE_DELAY = 2 * 60 * 60
MAX_MAX_RESPONSE_DELAY = 8 * 60 * 60

ATENTTION_FACTOR = 10   # Amount to reduce the current delay by when people chat, in seconds. This is per interval so bear in mind it will in practice be several times this.

STATUS_UPDATE_CHANCE = 0.25  # Probability of updating status on chat messages
STATUS_LIST = [
        ("Watching", "SAO"),
        ("Watching", "Humanity"),
        ("Watching", "Lecture recordings"),
        ("Watching", "Humanity"),
        ("Listening to", "Miku"),
        ("Listening to", "Nier Soundtrack"),
        ("Listening to", "Suspicious neighbours"),
        ("Playing", "Dota"),
        ("Playing", "FF14"),
        ("Playing", "Portal"),
        ("Playing", "Factorio"),
        ("Playing", "my own VR"),
        ("Watching", "youtube")
    ]