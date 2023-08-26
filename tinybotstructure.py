# -*- coding: utf-8 -*-
""" Tinybot by Nortxort (https://github.com/nortxort/tinybot-rtc) """
import logging
import threading
import random
import json
import pinylib
import webbrowser
import urllib, json
import requests
import time
import re
from time import sleep
from random import randint
from apis import tinychat
from util import tracklist
from page import privacy
from apis import youtube, lastfm, other, locals_
import check_user
import time

__version__ = '2.0.3'
log = logging.getLogger(__name__)

class TinychatBot(pinylib.TinychatRTCClient):
    privacy_ = None
    timer_thread = None
    playlist = tracklist.PlayList()
    search_list = []
    is_search_list_yt_playlist = False
    bl_search_list = []

    def message_handler(self, msg):
        prefix = "!"

        if msg.startswith(prefix):
            
            parts = msg.split(' ')
            cmd = parts[0].lower().strip()
            cmd_arg = ' '.join(parts[1:]).strip()

                elif cmd == prefix + 'ai':
                    threading.Thread(target=self.do_ai, args=(cmd_arg,)).start()

    # Class-level variable to track the last time do_ai method was called
    last_do_ai_called = 0

    def do_ai(self, cmd_arg, max_tokens=150, max_parts=2, delay_between_parts=2, min_response_length=3):
        # Define your OpenAI API key
        api_key = 'zk-D1DRCYWEYcSETYWERTYCWtyCETYRPxVxd3po0DCz'

        # Define the chat-based API endpoint
        endpoint = 'https://api.openai.com/v1/chat/completions'

        # Define additional parameters
        params = {
            'max_tokens': max_tokens,
        }

        # Create the request headers with your API key
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(api_key),
        }

        # Specify the model parameter as 'gpt-3.5-turbo'
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'system', 'content': 'You are a helpful assistant.'},
                         {'role': 'user', 'content': cmd_arg}],
            'max_tokens': params['max_tokens'],
        }

        # Send the POST request to the API
        response = requests.post(endpoint, headers=headers, data=json.dumps(data))

        # Check for a successful response
        if response.status_code == 200:
            result = json.loads(response.text)
            if 'choices' in result and result['choices'] and 'message' in result['choices'][0] and 'content' in result['choices'][0]['message']:
                response_text = result['choices'][0]['message']['content']

                # Check if the response_text is not empty and meets the minimum length
                if response_text.strip() and len(response_text) >= min_response_length:
                    # Use regular expression to replace various line break characters
                    response_text = re.sub(r'[\r\n\t\f\v]+', ' ', response_text)

                    # Split the response into parts based on sentence-like breaks
                    parts = []
                    current_part = ''
                    for sentence in response_text.split('. '):
                        if len(current_part + sentence) <= 200:
                            current_part += sentence + '. '
                        else:
                            parts.append(current_part)
                            current_part = sentence + '. '
                    if current_part:
                        parts.append(current_part)

                    num_parts = min(max_parts, len(parts))

                    # Calculate the time interval for rate limiting (15 seconds / 3 messages)
                    rate_limit_interval = 15.0 / 3

                    # Send each part with a delay using self.send_chat_msg method
                    for part in parts[:num_parts]:
                        self.send_chat_msg(part)  # Use self.send_chat_msg to send the response
                        time.sleep(delay_between_parts)
                        # Apply rate limiting
                        time.sleep(rate_limit_interval)
                else:
                    self.send_chat_msg("AI response was blank or too short.")
            else:
                self.send_chat_msg("AI response format unexpected: {}".format(result))
        else:
            error_message = 'Request failed with status code {}: {}'.format(response.status_code, response.text)
            self.send_chat_msg(error_message)
            
