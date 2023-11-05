import discord
from discord.ext import commands
from config import DISCORD_TOKEN as TOKEN, OPENAI_TOKEN as TOKEN2  # Import the TOKEN variables from config.py

import openai
from contexts import DEFAULT_CONTEXT

# Replace with your actual Discord user ID
MY_USER_ID = '249591687280721920'

openai.api_key = TOKEN2

# Define the intents
intents = discord.Intents.default()
intents.messages = True  # If you need to handle messages
intents.message_content = True  # Add this line

bot = commands.Bot(command_prefix='!', intents=intents)

#Called when the bot has booted up to report in the console whats happening
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

# Reads discord messages
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself or by any other user that is not you
    if message.author == bot.user or str(message.author.id) != MY_USER_ID:
        return

    # Print message content to console for debugging
    print(f"{message.channel}: {message.author}: {message.content}")

    #Send to chatGPT
    await send_to_GPT(message)

    # Important: Without this line, commands won't work.
    await bot.process_commands(message)

#Discord Bot command for when !hello is used
@bot.command()
async def hello(ctx):
    await ctx.send('Hello World!')

#discord Bot command for when !pin is used
@bot.command()
async def ping(ctx):
    await ctx.send('Pong')

async def send_to_GPT(message):
  response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {
        "role": "system",
        "content": DEFAULT_CONTEXT
        },
        {
        "role": "user",
        "content": f"{message.author}: {message.content}"
        }
    ],
    temperature=1,
    max_tokens=256,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )
  
  # Extract the 'content' from the response
  gpt_response_content = response['choices'][0]['message']['content']
  await message.channel.send(gpt_response_content)

#Run the bot.
bot.run(TOKEN)  # Use the TOKEN from config.py
