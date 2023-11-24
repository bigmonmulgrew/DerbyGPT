import openai
from config import OPENAI_TOKEN as TOKEN, BOT_USER_ID as DISCORD_ID
from contexts import DEFAULT_CONTEXT, MODEL
from datetime import datetime
from utils import debug

# Set up OpenAI key
openai.api_key = TOKEN

def common_contexts():
  # Get the current time
  current_time = datetime.now()
  # Format the time to HH:MM
  formatted_time = current_time.strftime('%H:%M')

  common = "\ncurrent time: " +  formatted_time
  common += "\nmessages starting with ! or \ should be ignored"
  return common

def ask_openai(message,temperature=1, max_tokens=256, top_p=1, frequency_penalty=0, presence_penalty=0, context=DEFAULT_CONTEXT):
  
  response = openai.ChatCompletion.create(
    model=MODEL,
    messages=[
        {
        "role": "system",
        "content": context + common_contexts()
        },
        {
        "role": "user",
        "content": f"{message.author.display_name}: {message.content}"
        }
    ],
    temperature=temperature,
    max_tokens=max_tokens,
    top_p=top_p,
    frequency_penalty=frequency_penalty,
    presence_penalty=presence_penalty
    )
  
  # Extract the 'content' from the response
  gpt_response_content = response['choices'][0]['message']['content']
  return gpt_response_content

def convert_discord_to_context(messages, context):
    ai_messages = []
    ai_messages.append(
        {
            "role": "system",
            "content": context + common_contexts()
        }
    )

    # Initialize variables to keep track of the concatenated user messages
    user_message_block = ""
    last_author = None

    for m in messages:
        if DISCORD_ID == m.author.id:  # Message from the bot (assistant)
            if user_message_block:  # If there's a pending user message block, add it first
                ai_messages.append({"role": "user", "content": user_message_block})
                user_message_block = ""  # Reset the user message block

            # Add the bot's (assistant's) message
            ai_messages.append({"role": "assistant", "content": f"{m.content}"})

        else:  # Message from a user
            if m.author.display_name != last_author:
                # If the author has changed, start a new block
                if user_message_block:  # Add a newline if not the first message in the block
                    user_message_block += "\n\n"
                user_message_block += f"{m.author.display_name}:\n"
            else:
                # Add a newline before adding the next message in the same block
                user_message_block += "\n"

            # Concatenate the current message
            user_message_block += m.content

            # Update the last author
            last_author = m.author.display_name

    # Add any remaining user message block after the loop
    if user_message_block:
        ai_messages.append({"role": "user", "content": user_message_block})

    debug("Converted Discord messages to OpenAI context:\n" + str(ai_messages))
    return ai_messages


def ask_openai_with_history(messages,temperature=1, max_tokens=256, top_p=1, frequency_penalty=0, presence_penalty=0, context=DEFAULT_CONTEXT):
  debug("Attempting to read full message history \n")

  # Convert messages to the format expected by the OpenAI API
  ai_messages = convert_discord_to_context(messages, context)

   # Print the messages to the console
  for message in ai_messages:
    print(message)

  response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=ai_messages,
    temperature=temperature,
    max_tokens=max_tokens,
    top_p=top_p,
    frequency_penalty=frequency_penalty,
    presence_penalty=presence_penalty
    )
  
  # Extract the 'content' from the response
  gpt_response_content = response['choices'][0]['message']['content']
  return gpt_response_content
