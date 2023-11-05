import openai
from config import OPENAI_TOKEN as TOKEN
from contexts import DEFAULT_CONTEXT
# from utils import debug

# Set up OpenAI key
openai.api_key = TOKEN

def ask_openai(message,temperature=1, max_tokens=256, top_p=1, frequency_penalty=0, presence_penalty=0):
  
  response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {
        "role": "system",
        "content": DEFAULT_CONTEXT
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