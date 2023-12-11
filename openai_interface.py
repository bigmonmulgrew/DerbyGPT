import openai
from config import OPENAI_TOKEN as TOKEN, BOT_USER_ID as DISCORD_ID
from contexts import DEFAULT_CONTEXT, MODEL, MODEL_IMAGE, MAX_TOKENS
from datetime import datetime
from utils import debug

# Set up OpenAI key
openai.api_key = TOKEN

def common_contexts():
  # Get the current time
  current_time = datetime.now()
  # Format the time to HH:MM
  formatted_time = current_time.strftime('%H:%M')
  formatted_date = current_time.strftime('%A %d %b %Y')

  common = f"\ncurrent date: " +  formatted_date
  common += f"\ncurrent time: " +  formatted_time
  common += f"\nmessages starting with ! or \ should be ignored"
  return common

def ask_openai(message,temperature=1, max_tokens=256, top_p=1, frequency_penalty=0, presence_penalty=0, context=DEFAULT_CONTEXT):
  
  response = openai.chat.completions.create(
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
  gpt_response_content = response.choices[0].message.content
  return gpt_response_content

def add_system_context(ai_messages, context):
  """Appends the default system message and context to the given list of ai messages"""
  ai_messages.append(
        {
            "role": "system",
            "content": context + common_contexts()
        }
    )

def format_user_message(user_message_block, images):
    # Initialize the message content with the user's text
    message_content = [{"type": "text", "text": user_message_block}]

    # If there are images, add them to the message content
    if images:
        for image_url in images:
            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                },
            })

    # Return the formatted message object
    return {"role": "user", "content": message_content}

def get_images_from_message(m,images):
  found_image = False
  for attachment in m.attachments:
    # Check if the attachment is an image (by content type or file extension)
    if any(attachment.filename.lower().endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
      # Get the image URL and append to the provided list
      images.append(attachment.url)
      found_image = True
  return found_image

def add_message_block(ai_messages, messages):
  """
  Takes in a list of one or more messages from discord and appends them to the ai_messages list
  Includes extraction and formatting of images to the context
  All discord messages passed here will be converted to a single ai message which containt usernames and message content.
  """
  # Initialize variables to keep track of the concatenated user messages
  user_message_block = ""
  last_author = None
  include_images = []
  found_image = False

  for m in messages:
    

    if m.author.display_name != last_author:
      # If the author has changed, start a new block
      ai_messages.append(format_user_message(user_message_block, include_images))
      user_message_block = f"{m.author.display_name}:\n"  # Create a new user message block starting with this users name
      include_images = [] # Reset the image list to empty
    else:
      # Add a newline before adding the next message in the same block
      user_message_block += f"\n"

    #Check if this message contains images
    found_image = get_images_from_message(m, include_images) or found_image

    # Concatenate the current message
    user_message_block += m.content

    # Update the last author
    last_author = m.author.display_name
  
  ai_messages.append(format_user_message(user_message_block, include_images))

  return found_image

def convert_discord_to_context(messages, context):
    ai_messages = []
    image_api = False
    add_system_context(ai_messages, context)

    # Create a list to hold each block of user messages, blocks are broken up by ai messages
    user_message_block = []

    # Group messages into a block of user messages
    for m in messages:
      if DISCORD_ID != m.author.id:   # Message is from a user and not the bot
        user_message_block.append(m)  # Create a list of consecutive user messages

      else:                           # Message is from the bot (assistant)
        if len(user_message_block) > 0:  # If there's a pending user message block, add it first
          image_api = add_message_block(ai_messages, user_message_block) or image_api  # Convert the messages into a single ai user message
          user_message_block = []         # Reset the list to empty once it has been appended
        
        # Add the bot's (assistant's) message
        ai_messages.append({"role": "assistant", "content": f"{m.content}"})

    if len(user_message_block) > 0: # Check if theres still a user message to add after the loop
      image_api = add_message_block(ai_messages, user_message_block) or image_api

    debug("Converted Discord messages to OpenAI context:\n" + str(ai_messages))
    return (ai_messages, image_api)


def ask_openai_with_history(messages,temperature=1, max_tokens=MAX_TOKENS, top_p=1, frequency_penalty=0, presence_penalty=0, context=DEFAULT_CONTEXT):
  debug("Attempting to read full message history \n")

  # Convert messages to the format expected by the OpenAI API
  ai_messages, image_api = convert_discord_to_context(messages, context)


  # Print the messages to the console
  for message in ai_messages:
    print(message)

  response = openai.chat.completions.create(
    model=MODEL_IMAGE if image_api else MODEL,
    messages=ai_messages,
    temperature=temperature,
    max_tokens=max_tokens,
    top_p=top_p,
    frequency_penalty=frequency_penalty,
    presence_penalty=presence_penalty
    )
  
  # Extract the 'content' from the response
  gpt_response_content = response.choices[0].message.content
  return gpt_response_content
