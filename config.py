# Configuration variables
#Import toeksn that are ignored by git
from tokens import DISCORD_TOKEN as DT
from tokens import OPENAI_TOKEN as OT

# The token for Discord
DISCORD_TOKEN =  DT
MY_USER_ID = '249591687280721920' # User ID of BigmonD
MY_GUILD_ID = 1156585341411655710 # Guild ID of Derby computing Discord
BOT_USER_ID = 1170451102022504553 # ChatGPT's user ID

# The token for ChatGPT
OPENAI_TOKEN = OT

#Timing calculations to check the bots response time
# Initial response delay in seconds (e.g., 0.5 to 5 minutes)
MIN_RESPONSE_DELAY = 5 * 60  # X
MAX_RESPONSE_DELAY = 15 * 60  # Y

# Maximum delay cap (e.g., 30 min to 6 hours)
MAX_MIN_RESPONSE_DELAY = 1 * 60 * 60
MAX_MAX_RESPONSE_DELAY = 8 * 60 * 60

