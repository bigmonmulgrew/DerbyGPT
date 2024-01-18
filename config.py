# Configuration variables
#Import toeksn that are ignored by git
from tokens import DISCORD_TOKEN as DT
from tokens import OPENAI_TOKEN as OT

# The settings for Discord
DISCORD_TOKEN =  DT
MY_USER_ID = '249591687280721920'   # User ID of BigmonD
MY_GUILD_ID = 1156585341411655710   # Guild ID of Derby computing Discord
BOT_USER_ID = 1170451102022504553   # ChatGPT's user ID

# The token for ChatGPT
OPENAI_TOKEN = OT

#Timing calculations to check the bots response time

BOT_CHECK_TIME = 10 # Max interval the bot will check the channels at.
RESPONSE_RATE_RANDOMNESS  = 0.2 # Amount +/- the bots response probability can vary. This is a randomised percentage betweeen +/- the limits
GLOBAL_RESPONSE_MULTIPLIER = 2 # Amount to multiply probability curve of all channels when there has been a recent global response
MIN_GLOBAL_MULTIPLIER = 0.1 # Used to clamp the multiplier so it never reaches 0

CHANNEL_DEFAULTS = {
    "min_response_time": 30,
    "max_response_time": 300,
    "min_response_time_cap": 1800,  #Hard limit for min time when increased by growth factor
    "max_response_time_cap": 6400,   #Hard limit for max time when increased by growth factor
    "idle_growth_factor": 1.1,       #Amount the min and max response times increase by after checkign responses and finding nothing
    "attention_factor": 2           #Amount the probability to respond will increase by per ping
}

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