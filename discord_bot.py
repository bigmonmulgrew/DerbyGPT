import asyncio
import random
import discord

from discord.ext import commands
from config import DISCORD_TOKEN as TOKEN, MY_USER_ID, MY_GUILD_ID, BOT_USER_ID
#from config import CHAT_CHANNEL
from config import DEBUG_CHANNEL as CHAT_CHANNEL    #Comment out the above line and uncomment here to swithc to debugging channel
from config import MIN_RESPONSE_DELAY, MAX_MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY, MAX_MAX_RESPONSE_DELAY, ATENTTION_FACTOR
from contexts import HISTORY_COUNT, DEFAULT_CONTEXT
from openai_interface import ask_openai, ask_openai_with_history
from utils import debug
from datetime import datetime, timedelta

# Last message time
last_message_time = datetime.utcnow()# - timedelta(minutes=30)

# Delay times
delay = (300, 4) # define a default but we will set this befor efirst use anyway

#List of channels to check for messages
channel_list = {
  CHAT_CHANNEL: DEFAULT_CONTEXT  # General Chat usually
}

# Define the intents
intents = discord.Intents.default()
intents.messages = True  # If you need to handle messages
intents.message_content = True  # Add this line

bot = commands.Bot(command_prefix='!', intents=intents)

#Called when the bot has booted up to report in the console whats happening
@bot.event
async def on_ready():
    debug(f'We have logged in as {bot.user}')
    # Start the response loop
    bot.loop.create_task(respond_to_messages())
    for guild in bot.guilds:
        debug(f"- {guild.name} (ID: {guild.id})")

# Reads discord messages
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Process commands first
    await bot.process_commands(message)

    # Check if the message is a command (starts with the command prefix)
    # If it is, return early to prevent further processing
    ctx = await bot.get_context(message)
    if ctx.valid:
        # It's a command, so don't proceed with custom message handling
        return

    # Check if the bot is mentioned in the message
    if bot.user in message.mentions:
        debug(f'Someone called me {bot.user}')
        await tagged_me(message)
    
    # Check if the message is sent in the designated channel
    if message.channel.id == CHAT_CHANNEL:
        await get_attention(message)

    # Custom processing for non-command messages
    #if str(message.author.id) == MY_USER_ID:
        #debug(f"{message.channel}: {message.author.display_name}: {message.content}")
        #openai_response = ask_openai(message)
        #await message.channel.send(openai_response)

#Discord Bot command for when !hello is used
@bot.command()
async def hello(ctx):
    await ctx.send('Hello World!')

#discord Bot command for when !pin is used
@bot.command()
async def ping(ctx):
    await ctx.send('Pong')
    
#discord Bot command for testing new code
@bot.command()
async def testing(ctx):
    
    await process_channels()

def run_bot():    
    #Run the bot
    bot.run(TOKEN)    

def weighted_delay(min_delay, max_delay, time_since_last_message):
    # Calculate delay factor based on time since last message
    delay_factor = time_since_last_message / min_delay
    # Calculate weighted delay
    delay = min_delay * delay_factor
    # Make sure the delay is at least the minimum and at most the maximum
    delay = max(min_delay, min(delay, max_delay))
    return delay

def generate_delay_steps(total_delay):
    debug("Generate delay steps, Total delay:" + str(total_delay))
    total_delay = round(total_delay)
    factors = []
    for i in range(1, int(total_delay**0.5) + 1):
        if total_delay % i == 0:
            factors.append(i)
            if i != total_delay // i:
                factors.append(total_delay // i)

    debug("Generate delay steps, factors:" + str(factors))
    factors.sort()

    # Picking a factor from two-thirds the way along the list
    index = len(factors) * 2 // 3
    part_delay = factors[index]

    # Calculating the second factor
    iterations = total_delay // part_delay

    return part_delay, iterations

def update_delay(change):
    # delay[1] iterations, #delay[0] delay per iteration.
    global delay
    part_delay = delay[0]
    iterations = delay[1]

    if change <= part_delay:
        iterations -= 1
    else:
        iterations -= change // part_delay

    delay = (part_delay, iterations) 
    debug("Updating delay:" + str(delay))

async def respond_to_channel(c):
    global last_message_time

    # Ensure the channel is a text channel where message history is available
    channel = bot.get_channel(c)
    if isinstance(channel, discord.TextChannel):
        # Use the history() method to retrieve messages
        messages = [message async for message in channel.history(limit=HISTORY_COUNT)]
        if (messages[0].author.id != BOT_USER_ID):
            last_message_time = datetime.utcnow()
            messages.reverse()

            # Set typing indicator
            async with channel.typing():
                openai_response = ask_openai_with_history(messages)
            
            #Send the response
            await channel.send(openai_response)
    

async def process_channels():
    for c in channel_list:
        await respond_to_channel(c)

async def respond_to_messages():
    global last_message_time
    global delay
    while True:
        # Calculate time since last message
        time_since_last_message = (datetime.utcnow() - last_message_time).total_seconds()

        # Determine the current delay based on the time since the last message
        current_min_delay = weighted_delay(MIN_RESPONSE_DELAY, MAX_MIN_RESPONSE_DELAY, time_since_last_message)
        current_max_delay = weighted_delay(MAX_RESPONSE_DELAY, MAX_MAX_RESPONSE_DELAY, time_since_last_message)

        # Wait for a random amount of time within the current delay window
        total_delay = random.uniform(current_min_delay, current_max_delay)
        
        delay = generate_delay_steps(total_delay)
        debug("OpenAI loop delay:" + str(delay))
        
        # delay[1] iterations, #delay[0] delay per iteration.
        while delay[1] > 0:
            await asyncio.sleep(delay[0])
            update_delay(delay[0])

        while 0 <= datetime.utcnow().hour < 6:
            await asyncio.sleep(3600)

        await process_channels()

async def tagged_me(message):
    # Your logic when the bot is tagged
    # For example, modifying delay or sending a response
    # Example: print(f"I was tagged in a message by {message.author.display_name}")
    # ... your logic here ...
    
    update_delay(delay[0])

async def get_attention(message):
    # When users chat it should reduce the delay time of the bot.
    global delay
    t = delay[0]    #time
    i = delay[1]    #iterations

    t -= ATENTTION_FACTOR
    if t <=0:
        t = 1
    
    delay = (t, i)
    debug("Getting attenion:" + str(delay))


    