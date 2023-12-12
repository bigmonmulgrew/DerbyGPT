import asyncio
import random
import discord
import os

from discord.ext import commands
#splitting imports from config into groups for for readability
from config import DISCORD_TOKEN as TOKEN, MY_USER_ID, MY_GUILD_ID, BOT_USER_ID
from config import CHAT_CHANNEL, SOS_CHANNEL, DEBUG_CHANNEL
from config import MIN_RESPONSE_DELAY, MAX_MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY, MAX_MAX_RESPONSE_DELAY, ATENTTION_FACTOR
from config import STATUS_LIST, STATUS_UPDATE_CHANCE
from contexts import HISTORY_COUNT, DEFAULT_CONTEXT, HISTORY_COUNT_SOS, SOS_CONTEXT
from openai_interface import ask_openai, ask_openai_with_history
from utils import debug
from datetime import datetime, timedelta

# Last message time
last_general_message_time = datetime.utcnow()# - timedelta(minutes=30)
last_sos_message_time = datetime.utcnow()# - timedelta(minutes=30)

# Delay times
gen_chat_delay = (300, 4) # define a default but we will set this befor efirst use anyway
sos_chat_delay = (300, 3) # define a sos channel delay, we set this later, this is just a reasonable default/

#List of channels to check for messages
#These are checked on the delayed loop rather than real time.
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
    bot.loop.create_task(respond_to_general_chat())     #Creat the loop that monitors general chat.
    bot.loop.create_task(respond_to_sos_chat())         #Creat the loop that monitors sos chat.
    await set_status(bot)
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

    # Check if the message is sent in the debug channel
    if message.channel.id == DEBUG_CHANNEL:
        await debug_test()

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
    ##Currently all this really does is return time since last message, planning to see if the ai spots this in a future code review.
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

def update_delay(change, chat_delay):
    part_delay = chat_delay[0]
    iterations = chat_delay[1]

    if change <= part_delay:
        iterations -= 1
    else:
        iterations -= change // part_delay

    new_chat_delay = (part_delay, iterations)
    debug("Updating delay:" + str(new_chat_delay))
    return new_chat_delay

async def respond_to_channel(c, history_count=HISTORY_COUNT, context_string=DEFAULT_CONTEXT):
    global last_general_message_time

    # Ensure the channel is a text channel where message history is available
    channel = bot.get_channel(c)
    if isinstance(channel, discord.TextChannel):
        messages = [message async for message in channel.history(limit=history_count)]
        if messages and (messages[0].author.id != BOT_USER_ID):
            last_general_message_time = datetime.utcnow()
            messages.reverse()

            # Set typing indicator
            async with channel.typing():
                openai_response = ask_openai_with_history(messages, context=context_string)

            # Check if the response is too long and split if necessary
            if len(openai_response) > 2000:
                # Split the response at newline characters near the 2000 character mark
                responses = split_response(openai_response)
                for response_part in responses:
                    async with channel.typing():
                        await asyncio.sleep(10)
                    await channel.send(response_part)
                    # Wait and show typing indicator between messages
                    
                    
                    
            else:
                await channel.send(openai_response)

            # % chance to update the status
            if random.random() < STATUS_UPDATE_CHANCE:
                await set_status(bot)

def split_response(response, limit=2000, delimiter='\n'):
    """
    Splits a long string into parts, each with a maximum length of 'limit'.
    Tries to split at 'delimiter' to avoid breaking words.
    """
    parts = []
    while response:
        if len(response) <= limit:
            parts.append(response)
            break
        else:
            # Find nearest delimiter to the limit
            split_index = response.rfind(delimiter, 0, limit)
            if split_index == -1:  # No delimiter found, hard split at the limit
                split_index = limit

            parts.append(response[:split_index])
            response = response[split_index:].lstrip(delimiter)  # Remove leading delimiter from next part

    return parts

async def process_channels():
    for channel,context_data in channel_list.items():
        await respond_to_channel(channel, context_string=context_data)

async def respond_to_general_chat():
    global last_general_message_time
    global gen_chat_delay
    while True:
        # Calculate time since last message
        time_since_last_message = (datetime.utcnow() - last_general_message_time).total_seconds()

        # Determine the current delay based on the time since the last message
        current_min_delay = weighted_delay(MIN_RESPONSE_DELAY, MAX_MIN_RESPONSE_DELAY, time_since_last_message)
        current_max_delay = weighted_delay(MAX_RESPONSE_DELAY, MAX_MAX_RESPONSE_DELAY, time_since_last_message)

        # Wait for a random amount of time within the current delay window
        total_delay = random.uniform(current_min_delay, current_max_delay)
        
        gen_chat_delay = generate_delay_steps(total_delay)
        debug("OpenAI loop delay:" + str(gen_chat_delay))
        
        # delay[1] iterations, #delay[0] delay per iteration.
        while gen_chat_delay[1] > 0:
            await asyncio.sleep(gen_chat_delay[0])
            gen_chat_delay = update_delay(gen_chat_delay[0], gen_chat_delay)

        while 0 <= datetime.utcnow().hour < 6:
            await asyncio.sleep(3600)
            await set_status(bot)

        await process_channels()

async def respond_to_sos_chat():
    global last_sos_message_time
    global sos_chat_delay
    while True:
        # Calculate time since last message
        time_since_last_message = (datetime.utcnow() - last_general_message_time).total_seconds()

        #Use the standard response delay for this because it shouldnt get slower when idle 
        # Wait for a random amount of time within the current delay window
        total_delay = random.uniform(MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY)
        
        sos_chat_delay = generate_delay_steps(total_delay)
        debug("OpenAI loop delay:" + str(sos_chat_delay))
        
        # delay[1] iterations, #delay[0] delay per iteration.
        while sos_chat_delay[1] > 0:
            await asyncio.sleep(sos_chat_delay[0])
            sos_chat_delay = update_delay(sos_chat_delay[0], sos_chat_delay)

        await respond_to_channel(SOS_CHANNEL, history_count = HISTORY_COUNT_SOS, context_string = SOS_CONTEXT)


async def tagged_me(message):
    # Reduces the chat delay when theb bot is tagged
    # For example, modifying delay or sending a response
    # Example: print(f"I was tagged in a message by {message.author.display_name}")
    global gen_chat_delay
    gen_chat_delay = update_delay(gen_chat_delay[0], gen_chat_delay)

async def get_attention(message):
    # When users chat it should reduce the delay time of the bot.
    global gen_chat_delay
    t = gen_chat_delay[0]    #time
    i = gen_chat_delay[1]    #iterations

    t -= ATENTTION_FACTOR
    if t <=0:
        t = 1
    
    gen_chat_delay = (t, i)
    debug("Getting attenion:" + str(gen_chat_delay))

async def set_status(bot):
    # List of potential statuses
    statuses = STATUS_LIST

    # Randomly choose a status
    activity_type, name = random.choice(statuses)

    # Map the string to the actual Discord activity type
    if activity_type == "Playing":
        activity = discord.Game(name=name)
    elif activity_type == "Listening to":
        activity = discord.Activity(type=discord.ActivityType.listening, name=name)
    elif activity_type == "Watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=name)

    # Set the bot's status
    await bot.change_presence(activity=activity)

async def debug_test():
    await respond_to_channel(DEBUG_CHANNEL, history_count = 4, context_string = DEFAULT_CONTEXT)
    