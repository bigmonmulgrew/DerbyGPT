import openai
from config import OPENAI_TOKEN as TOKEN, BOT_USER_ID as DISCORD_ID
from contexts import DEFAULT_CONTEXT
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
    model="gpt-4",
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

def conver_discord_to_context(messages,context):
  ai_messages = []
  ai_messages.append(
      {
          "role": "system",
          "content": context + common_contexts()
      }
  )
  for m in messages:
      message_dict = {
          "role": "assistant" if DISCORD_ID == m.author.id else "user",
          "content": f"{m.content}" if DISCORD_ID == m.author.id else f"{m.author.display_name}: {m.content}",
          
      }
      ai_messages.append(message_dict)  # You need to append the message_dict to the list
  return ai_messages

def ask_openai_with_history(messages,temperature=1, max_tokens=256, top_p=1, frequency_penalty=0, presence_penalty=0, context=DEFAULT_CONTEXT):
  debug("Attempting to read full message history \n")

  # Convert messages to the format expected by the OpenAI API
  ai_messages = conver_discord_to_context(messages, context)

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
