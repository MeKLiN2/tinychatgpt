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

    @property
    def config_path(self):
        """ Returns the path to the rooms configuration directory. """
        return pinylib.CONFIG.CONFIG_PATH + self.room_name + '/'

    def user_check(self, user, account=False, guest=False, nick=False, lurker=False):
        """
        A wrapper for the CheckUser class.

        :return: True, if the user was banned.
        :rtype: bool
        """
        if not self.is_client_mod:
            return False

        judge = check_user.CheckUser(self, user, pinylib.CONFIG)

        if account and user.account != '':
            log.debug('checking account: %s' % user.account)
            if not user.is_mod and judge.check_account():
                return True

            api = pinylib.apis.tinychat.user_info(user.account)
            if api is not None:
                user.tinychat_id = api['tinychat_id']
                user.last_login = api['last_active']

        if guest:
            log.debug('checking guest entrance: %s' % user.nick)
            if judge.guest_entry():
                return True

        if nick and user.nick:
            log.debug('checking nick: %s' % user.nick)
            if not user.is_mod and judge.check_nick():
                return True

        if lurker and user.is_lurker:
            log.debug('check lurker: %s' % user.nick)
            if judge.check_lurker():
                return True

        return False
#### 1l1l1l1l1l1l1l1l1l1l1l1l1l1l1l1l
    def on_joined(self, client_info):
        """
        Received when the client have joined the room successfully.

        :param client_info: This contains info about the client, such as user role and so on.
        :type client_info: dict
        """
        log.info('client info: %s' % client_info)
        self.client_id = client_info['handle']
        self.is_client_mod = client_info['mod']
        self.is_client_owner = client_info['owner']
        client = self.users.add(client_info)
        client.user_level = 0
        self.console_write(pinylib.COLOR['bright_green'], 'Client joined the room: %s:%s' % (client.nick, client.id))
        
        # do special operations.
        threading.Thread(target=self.options).start()
        #threading.Thread(target=self.clock).start()
        self.send_chat_msg('SpamFairy is Online!\nVIP Status: %s' % pinylib.CONFIG.B_vip)

    test = None

    def on_join(self, join_info):
        log.info('user join info: %s' % join_info)
        _user = self.users.add(join_info)
        adminlist = open(self.config_path + pinylib.CONFIG.B_Admins).read().splitlines()
        knownlist = open(self.config_path + pinylib.CONFIG.B_known).read().splitlines()
        people = open(self.config_path + pinylib.CONFIG.B_peep).read().splitlines() 
        if not _user.account in knownlist:
            print(' %s is arriving' % _user.account)
        if _user.account:
            if _user.is_owner or _user.account in adminlist:
                _user.user_level = 1
                self.console_write(pinylib.COLOR['red'], '%s:%s' % (_user.nick, _user.account))
                if not _user.account in knownlist:
                    pinylib.file_handler.file_writer(self.config_path, pinylib.CONFIG.B_known, _user.account)
                    sleep(randint(2,10))
                    self.send_chat_msg('I know who %s is' % (_user.account))
            if _user.account not in adminlist:
                if _user.account:
                    #sleep(randint(2,10))
                    #self.send_chat_msg('!acc add %s verified' % (_user.account))

                    pinylib.file_handler.file_writer(self.config_path, pinylib.CONFIG.B_peep, _user.account)



        self.console_write(pinylib.COLOR['cyan'], '%s arrived.' % (_user.nick))

    def on_nick(self, uid, nick):
        _user = self.users.search(uid)
        old_nick = _user.nick
        _user.nick = nick

        if uid != self.client_id:
            if not self.user_check(_user, nick=True):
                if pinylib.CONFIG.B_GREET and self.is_client_mod:
                    if old_nick.startswith('guest-'):
                        if _user.account:
                            self.send_chat_msg('Welcome to the room %s:%s:%s' %
                                               (_user.nick, _user.id, _user.account))
                        else:
                            self.send_chat_msg('Welcome to the room %s:%s' % (_user.nick, _user.id))

            self.console_write(pinylib.COLOR['bright_cyan'], '%s:%s Changed nick to: %s' % (old_nick, uid, nick))

    def on_yut_play(self, yt_data):
        """
        Received when a youtube gets started or time searched.

        This also gets received when the client starts a youtube, the information is
        however ignored in that case.

        :param yt_data: The event information contains info such as the ID (handle) of the user
        starting/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        if self.playlist.has_active_track:
            self.cancel_timer()

        track = youtube.video_details(yt_data['item']['id'], False)

        if 'handle' in yt_data:
            if yt_data['handle'] != self.client_id:
                _user = self.users.search(yt_data['handle'])

                if yt_data['item']['offset'] == 0:
                    self.playlist.start(_user.nick, track)
                    self.timer(track.time)
                    self.console_write(pinylib.COLOR['bright_magenta'], '%s started youtube video (%s)' %
                                       (_user.nick, track.title))
                    
                elif yt_data['item']['offset'] > 0:
                    offset = self.playlist.play(yt_data['item']['offset'])
                    self.timer(offset)
                    self.console_write(pinylib.COLOR['bright_magenta'], '%s searched the youtube video to: %s' %
                                       (_user.nick, int(round(yt_data['item']['offset']))))
        else:
            if yt_data['item']['offset'] > 0:
                self.playlist.start('started before joining.', track)
                offset = self.playlist.play(yt_data['item']['offset'])
                self.timer(offset)

    def on_yut_pause(self, yt_data):
        """
        Received when a youtube gets paused or searched while paused.

        This also gets received when the client pauses or searches while paused, the information is
        however ignored in that case.

        :param yt_data: The event information contains info such as the ID (handle) of the user
        pausing/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        if self.playlist.has_active_track:
            self.cancel_timer()

        self.playlist.pause()

        if 'handle' in yt_data:
            if yt_data['handle'] != self.client_id:
                _user = self.users.search(yt_data['handle'])
                self.console_write(pinylib.COLOR['bright_magenta'], '%s paused the video at %s' %
                                   (_user.nick, int(round(yt_data['item']['offset']))))
        else:
            log.info('no handle for youtube pause: %s' % yt_data)

    story = []
    votes = {}

    def send_full_story_in_parts(self, full_story):
        # Split the full story into parts of a manageable size
        max_chars_per_message = 150  # Adjust this value as needed
        story_parts = [full_story[i:i + max_chars_per_message] for i in range(0, len(full_story), max_chars_per_message)]

        # Send each part as a separate chat message with a 1.5-second delay
        for part in story_parts:
            self.send_chat_msg("Full Story:\n" + part)
            time.sleep(3.0)  # Add a 1.5-second delay


    def add_to_story(self, sentence):
        self.story.append(sentence)
        # Initialize the votes for this sentence.
        self.votes[len(self.story) - 1] = {'likes': 0, 'dislikes': 0}
        
        # Split the message into smaller parts
        max_chars_per_message = 200  # Adjust this value as needed
        message_parts = [sentence[i:i + max_chars_per_message] for i in range(0, len(sentence), max_chars_per_message)]
        
        for part in message_parts:
            self.send_chat_msg("Added to the story: " + part)
            time.sleep(3.0)  # Add a 1.5-second delay

    def get_full_story(self):
        return ' '.join(self.story)

    def load_response_keywords(self):
        # Read keywords from a file and store them in a list.
        keywords = []
        with open("responses.txt", "r") as file:
            keywords = [line.strip() for line in file.readlines()]
        return keywords
        self.message_counter = 0  # Initialize the message counter.



    def check_message_length_and_call_ai(self, msg):
        if len(msg) > 150:
            # Call do_ai and get the response
            ai_response = self.do_ai(msg)

            # Check if ai_response is not None
            if ai_response and 'choices' in ai_response and ai_response['choices']:
                # Extract the response text from ai_response (assuming it's a string)
                response_text = ai_response['choices'][0]['message']['content']

                # Create the final response message using str.format() with the user's nickname
                final_response = "{0}: {1}".format(self.active_user.nick, response_text)

                # Send the final response
                self.send_chat_msg(final_response)





    def message_handler(self, msg):
        prefix = "!"

        # Check message length and call AI if needed
        self.check_message_length_and_call_ai(msg)

        # Load keywords from a file
        keywords = []
        with open("responses.txt", "r") as file:
            keywords = [line.strip() for line in file.readlines()]

        # Check if any keyword from the file is in the received message.
        for keyword in keywords:
            if keyword in msg.lower():  # Convert to lowercase for case-insensitive matching.
                self.send_chat_msg("Bot detected keyword: {} by {}".format(keyword, self.active_user.nick))

        self.message_counter = getattr(self, "message_counter", 0)
        # Increment the message counter for every message received.
        self.message_counter += 1
        if self.message_counter % 10 == 0:
            # If the counter is a multiple of 10, respond to the message.
            # Call do_ai and get the response
            ai_response = self.do_ai(msg)

            # Check if ai_response is not None
            if ai_response and 'choices' in ai_response and ai_response['choices']:
                # Extract the response text from ai_response (assuming it's a string)
                response_text = ai_response['choices'][0]['message']['content']

                # Create the final response message using str.format()
                final_response = "Hey, {0}! {1}".format(self.active_user.nick, response_text)

                # Send the final response
                self.send_chat_msg(final_response)
            #else:
                # Handle the case where ai_response is None or doesn't contain valid data
                #self.send_chat_msg("Slow down, speedy!")

        # Check the length of the message
        if len(msg) > 150:
            # Call do_ai and get the response
            ai_response = self.do_ai(msg)

            # Check if ai_response is not None
            if ai_response and 'choices' in ai_response and ai_response['choices']:
                # Extract the response text from ai_response (assuming it's a string)
                response_text = ai_response['choices'][0]['message']['content']

                # Create the final response message using str.format() with the user's nickname
                final_response = "{0}: {1}".format(self.active_user.nick, response_text)

                # Send the final response
                self.send_chat_msg(final_response)


        if "hello" in msg.lower():
            # Call do_ai and get the response
            ai_response = self.do_ai(msg)

            # Check if ai_response is not None
            if ai_response and 'choices' in ai_response and ai_response['choices']:
                # Extract the response text from ai_response (assuming it's a string)
                response_text = ai_response['choices'][0]['message']['content']

                # Create the final response message using str.format()
                final_response = "{0}, {1}".format(self.active_user.nick, response_text)

                # Send the final response
                self.send_chat_msg(final_response)






        if msg.startswith(prefix + 'story'):
            cmd_arg = ' '.join(msg.split(' ')[1:]).strip()

            if cmd_arg:
                self.add_to_story(cmd_arg)
                self.send_chat_msg("Added to the story: " + cmd_arg)
            else:
                self.send_chat_msg("Please provide a sentence to add to the story.")
        
        elif msg.startswith(prefix + 'fullstory'):
            full_story = self.get_full_story()
            if full_story:
                self.send_full_story_in_parts(full_story)
            else:
                self.send_chat_msg("The story is empty. Start it with '" + prefix + "story <your sentence>'.")
        
        elif msg.startswith(prefix + 'vote'):
            cmd_parts = msg.split(' ')
            if len(cmd_parts) != 3:
                self.send_chat_msg("Invalid vote format. Use '!vote <sentence_number> <like/dislike>'.")
                return
            
            try:
                sentence_num = int(cmd_parts[1])
                vote_type = cmd_parts[2].lower()
                
                if sentence_num < 0 or sentence_num >= len(self.story):
                    self.send_chat_msg("Invalid sentence number. Use '!fullstory' to see the story.")
                    return
                
                if vote_type not in ['like', 'dislike']:
                    self.send_chat_msg("Invalid vote type. Use 'like' or 'dislike'.")
                    return
                
                # Record the vote.
                if vote_type == 'like':
                    self.votes[sentence_num]['likes'] += 1
                elif vote_type == 'dislike':
                    self.votes[sentence_num]['dislikes'] += 1
                
                self.send_chat_msg("Vote recorded for sentence {} - Likes: {} Dislikes: {}".format(
                    sentence_num, self.votes[sentence_num]['likes'], self.votes[sentence_num]['dislikes']))
            
            except ValueError:
                self.send_chat_msg("Invalid sentence number. Use '!fullstory' to see the story.")




        #d3m = unicode('Ḑ̴̛̖͔͚̞̯̝͊͒̊̐̒͂̍͌̊̿̔3̴̡͎̲̣̪͕̰͖͍̻̦̥̝̭͆̐̀͑̈́̐̅́̔̅͜M̴̡̼̗̰͊̈͐̚͠ 🌱 卐 ̶̨̟̦̪̲͌̐̏̑͌́̽̿̍̔͊̕̕͜͜Ḋ̶̡̛̦͉̐͌̊̓̓̈́͂̋̈́̔͘͘͝3̶̧̡͕̮͔̦̀̍̐̑̿͝M̴̞̲͈͙̞̫̀̊̈̄̔̅̅̈́̒͝ͅ🌱 卐 ̴͇̟͖̓̋͑̌̇͑̿͗̕͝͝D̶̼̙̈́̎̇̊̒̚͝͝3̷̨̨̘̬̯̦̥̮̳̞́̐̌̌̋̊̍M̷̨̤̊̔̽͊͐̉̍̓̈́̋̄̓̑̈́͘͜🌱 卐 ̷̛̻͕̼̟͉̭̋̒͗͝D̶͈̟̣̼͔̟̤̏͗̚͠ͅ3̴̛̙̠͖̾̃̈́̏̊̅͠M̶͉͎͕͓̗̂͆̓̊͊͑̏̓͐͋̄͘͝🌱 卐 ̴̢̧̛͎͔͉͚͔̯̿̒D̵̜͉̖͖̹͊͌̈͊̍̂̽̈̿̔̄͂͂͝3̴̧̭̳̤̗̞̺͆͆̒͠M̷̛͖͇̹͙̰̬̟̬͗̑̀̿̄͒̓̕͠ ̵͙́̇̇̍̌̓́͐̃̋͠͠🌱 卐D̴͉̺͋̑͑̄͊͜3̸̨̞͔̻̞͑M̷̛̛̝͗͑̿̈̏̀͆̿̆́͗̋̈́🌱 卐 ̴̡̜̭̦̟̜̗͎̬̞̝̖͎̬̀͗̓͌͌̾̂̈͝Ḑ̶͎̦̖͙̠̩̎̀̓̒͛ͅ3̸̞͍̘̫̮͙͚̘̿̊̀̂͒̓̄̎͝ͅM̵̢̢̟̮͓̹̦̥̗̈́̌͊̑̈́̀̋̈́͗̑̐̓̕̚̚ 🌱 卐', 'utf-8')

        #if self.is_client_mod and self.active_user.user_level > 4:
            #threading.Thread(target=self.check_msg, args=(msg,)).start()

        #if "weed" in msg:
            #self.send_chat_msg("yeah i smoke it, %s" % self.active_user.nick)

        #if "bong" in msg:
            #self.send_chat_msg("i prefer bowls, %s" % self.active_user.nick)

        #if "churs" in msg:
            #self.send_chat_msg("cheers, %s (maori)" % self.active_user.nick)

        #if "tokes" in msg:
            #threading.Thread(target=self.toketimer).start()

        #if "niller" in msg:
            #self.do_niller()

        #if "cheers" in msg:
            #self.send_chat_msg("cheers, %s" % self.active_user.nick)

        if "meklinsleep" in msg:
            threading.Thread(target=self.meksleeptimer).start()

        if "dab" in msg:
            self.send_chat_msg("inhaling anything at high heat forms scar tissue on your lungs, %s" % self.active_user.nick)

        #if "windows" in msg:
            #self.send_chat_msg("%s! https://archive.org/details/7700divine the fastest version of windows ever made for high ranked, serious players, or tournament computers. this is the only windows .iso with zero dpc latency on the cpu. lovingly hand-edited by MeKLiN on 06-27-2022" % self.active_user.nick)

        #if "ignoreadd" in msg:
            #sleep(randint(1,3))
            #self.send_chat_msg("%s's computer is hacked by CTS script! Read more at: https://pastebin.com/1eJZ2hEG" % self.active_user.nick)
            #sleep(randint(1,3))
            #self.send_chat_msg('https://imgur.com/a/GACGIn9 open source script for ublock origins by meklin, blocks ALL javascript for in a chat, but not on the main TC page https://pastebin.com/TiDCRpPH')
            #sleep(randint(5,7))

        #if "orc" in msg:
            msg = unicode("𝗜 𝗔𝗠 𝗔𝗡 𝙊𝙍𝘾 𝗔𝗡𝗗 𝗜'𝗠 𝗗𝗜𝗚𝗚𝗜𝗡𝗚 𝗔 𝗛𝗢𝗟𝗘\n"
                          "𝗗𝗜𝗚𝗚𝗬, 𝗗𝗜𝗚𝗚𝗬 𝗛𝗢𝗟𝗘, 𝗗𝗜𝗚𝗚𝗜𝗡𝗚 𝗔 𝗛𝗢𝗟𝗘", 'utf-8')

        #if "orc" in msg:
            #self.send_chat_msg("𝗜 𝗔𝗠 𝗔𝗡 𝙊𝙍𝘾 𝗔𝗡𝗗 𝗜'𝗠 𝗗𝗜𝗚𝗚𝗜𝗡𝗚 𝗔 𝗛𝗢𝗟𝗘\n𝗗𝗜𝗚𝗚𝗬, 𝗗𝗜𝗚𝗚𝗬 𝗛𝗢𝗟𝗘, 𝗗𝗜𝗚𝗚𝗜𝗡𝗚 𝗔 𝗛𝗢𝗟𝗘", 'utf-8')

        #if "skrypt" in msg:
            #sleep(randint(1,3))
            #self.send_chat_msg("%s! https://pastebin.com/TiDCRpPH addons.mozilla.org/en-US/firefox/addon/ublock-origin chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm?hl=en Add the script into the My Filters tab in the Dashboard settings cog wheel of UBlock Origins." % self.active_user.account)
            #sleep(randint(1,3))
            #self.send_chat_msg('https://imgur.com/a/GACGIn9 AND And remember, the CTS script is compromised. Anything can happen to your computer if malicious javascript is run in your browser. https://pastebin.com/1eJZ2hEG')
            sleep(randint(5,7))

        #if "ZEBBY" in msg:
            #self.send_chat_msg('!acc ban %s' % self.active_user.account)
            #sleep(randint(3,5))

        #if "Z123" in msg:
            #self.send_chat_msg('!allowcam7')
            #sleep(randint(29,31))
            #self.send_chat_msg('!allowcam7')

        if "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n" in msg:
            self.send_chat_msg('!acc ban %s' % self.active_user.account)
            sleep(randint(3,5))

        #if len(msg) > 250:
            #self.send_chat_msg("You have earned ONE spam point! (%s) Type 'ZEBBY' to spend them." % len(msg))

        if msg.startswith(prefix):
            
            parts = msg.split(' ')
            cmd = parts[0].lower().strip()
            cmd_arg = ' '.join(parts[1:]).strip()

            if self.has_level(1):
                if self.is_client_owner:

                    if cmd == prefix + 'mod':
                        threading.Thread(target=self.do_make_mod, args=(cmd_arg,)).start()

                    elif cmd == prefix + 'rmod':
                        threading.Thread(target=self.do_remove_mod, args=(cmd_arg,)).start()

                    elif cmd == prefix + 'dir':
                        threading.Thread(target=self.do_directory).start()

                    elif cmd == prefix + 'p2t':
                        threading.Thread(target=self.do_push2talk).start()

                    elif cmd == prefix + 'crb':
                        threading.Thread(target=self.do_clear_room_bans).start()

                if cmd == prefix + 'kill':
                    self.do_kill()

                elif cmd == prefix + 'reboot':
                    self.do_reboot()
					
            #admin
            if self.has_level(2):
                if cmd == prefix + 'mi':
                    self.do_media_info()
                	

                elif cmd == prefix + 'spam':
                	#self.send_chat_msg(tt)
                	self.do_spam()

               #elif cmd == prefix + "vip":

                   #self.do_vip()

                elif cmd == prefix + 'crb':
                	threading.Thread(target=self.do_clear_room_bans).start()

                elif cmd == prefix + 'noguest':
                    self.do_guests()

                elif cmd == prefix + 'lurkers':
                    self.do_lurkers()

                elif cmd == prefix + 'guestnick':
                    self.do_guest_nicks()

                elif cmd == prefix + 'greet':
                    self.do_greet()

                elif cmd == prefix + 'kab':
                    self.do_kick_as_ban()

                elif cmd == prefix + 'rs':
                    self.do_room_settings()

                elif cmd == prefix + 'v':
                    self.do_version()

                elif cmd == prefix + 't':
                    self.do_uptime()

                elif cmd == prefix + 'nick':
                    self.do_nick(cmd_arg)				
		   
        	#botmods	
            if self.has_level(3):
                
                if cmd == prefix + 'op':
                    self.do_op_user(cmd_arg)


                elif cmd == prefix + 'knownadd':
                    pinylib.file_handler.file_writer(self.config_path, pinylib.CONFIG.B_known, cmd_arg)
                    self.send_chat_msg('Saved to whitelist: %s' % cmd_arg)

                elif cmd == prefix + 'knownremove':

                    pinylib.file_handler.remove_from_file(self.config_path, pinylib.CONFIG.B_known, cmd_arg)
                    self.send_chat_msg('Removed from whitelist: %s' % cmd_arg) 

                #elif cmd == prefix + "vip":
                    #self.do_vip()

                    self.do_vipcheck()   
                #elif cmd == prefix + 'd3m':

                	#self.send_chat_msg(d3m)

                elif cmd == prefix + 'deop':
                    self.do_deop_user(cmd_arg)

                elif cmd == prefix + 'pub':
                    self.do_public_cmds()

                elif cmd == prefix + 'kick12345':
                    threading.Thread(target=self.do_kick, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ban12345':
                    threading.Thread(target=self.do_ban, args=(cmd_arg,)).start()

                elif cmd == prefix + 'bn':
                    self.do_bad_nick(cmd_arg)

                elif cmd == prefix + 'rmbn':
                    self.do_remove_bad_nick(cmd_arg)

                elif cmd == prefix + 'bs':
                    self.do_bad_string(cmd_arg)

                elif cmd == prefix + 'rmbs':
                    self.do_remove_bad_string(cmd_arg)

                elif cmd == prefix + 'ba':
                    self.do_bad_account(cmd_arg)

                elif cmd == prefix + 'rmba':
                    self.do_remove_bad_account(cmd_arg)

                elif cmd == prefix + 't':
                    self.do_uptime()

                elif cmd == prefix + 'list':
                    #self.do_list_info(cmd_arg)
                    self.send_chat_msg('Joke API Disabled.')

                elif cmd == prefix + 'cam':
                    self.do_cam_approve(cmd_arg)

                elif cmd == prefix + 'close12345':
                    self.do_close_broadcast(cmd_arg)

                elif cmd == prefix + 'sbl':
                    self.do_banlist_search(cmd_arg)

                elif cmd == prefix + 'fg':
                    self.do_forgive(cmd_arg)

                elif cmd == prefix + 'unban':
                    self.do_unban(cmd_arg)

                elif cmd == prefix + 'clear':
                    self.do_clear()

            if self.has_level(4):

                if cmd == prefix + 'help':
                    self.do_help()

                elif cmd == prefix + 'top':
                    threading.Thread(target=self.do_lastfm_chart, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ran':
                    threading.Thread(target=self.do_lastfm_random_tunes, args=(cmd_arg,)).start()

                elif cmd == prefix + 'tag':
                    threading.Thread(target=self.do_search_lastfm_by_tag, args=(cmd_arg,)).start()

                elif cmd == prefix + 'pls':
                    threading.Thread(target=self.do_youtube_playlist_search, args=(cmd_arg,)).start()

                elif cmd == prefix + 'plp':
                    threading.Thread(target=self.do_play_youtube_playlist, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ssl':
                    self.do_show_search_list()

                elif cmd == prefix + 'del':
                    self.do_delete_playlist_item(cmd_arg)

                elif cmd == prefix + 'rpl':
                    self.do_media_replay()

                elif cmd == prefix + 'mbpl':
                    self.do_play_media()

                elif cmd == prefix + 'mbpa':
                    self.do_media_pause()

                elif cmd == prefix + 'seek':
                    self.do_seek_media(cmd_arg)

                elif cmd == prefix + 'cm':
                    self.do_close_media()

                elif cmd == prefix + 'cpl':
                    self.do_clear_playlist()

                elif cmd == prefix + 'spl':
                    self.do_playlist_info()

                elif cmd == prefix + 'yts':
                    threading.Thread(target=self.do_youtube_search, args=(cmd_arg,)).start()

                elif cmd == prefix + 'pyts':
                    self.do_play_youtube_search(cmd_arg) 

                elif cmd == prefix + 'ytadd':
                    
                    pinylib.file_handler.file_writer(self.config_path, pinylib.CONFIG.B_Youtube_Play_List, cmd_arg)
                    self.send_chat_msg('Saved to Youtube Log: %s' % cmd_arg)

                elif cmd == prefix + 'ytban' :
                    
                    pinylib.file_handler.file_writer(self.config_path, pinylib.CONFIG.B_Youtube_Ban_List, cmd_arg)
                    self.send_chat_msg('Saved to Youtube Filter: %s' % cmd_arg)

                
                elif cmd == prefix + 'ytunban':

                    pinylib.file_handler.remove_from_file(self.config_path, pinylib.CONFIG.B_Youtube_Ban_List, cmd_arg)
                    self.send_chat_msg('Removed from Youtube Filter: %s' % cmd_arg)

                elif cmd == prefix + 'ytremove':

                    pinylib.file_handler.remove_from_file(self.config_path, pinylib.CONFIG.B_Youtube_Play_List, cmd_arg)
                    self.send_chat_msg('Removed from Youtube Log: %s' % cmd_arg)

                elif cmd == prefix + 'ytlog':
                    lines = open(self.config_path + pinylib.CONFIG.B_Youtube_Play_List).read().splitlines()
                    myline =random.choice(lines)
                    #self.send_chat_msg(myline)

                    results = myline
                    threading.Thread(target=self.do_play_youtube, args=(results,)).start() 
                    self.send_chat_msg("Random Song: %s" % results)

            ytbanlist = open(self.config_path + pinylib.CONFIG.B_Youtube_Ban_List).read().splitlines()

            #if (pinylib.CONFIG.B_PUBLIC_CMD and self.has_level(5)) or self.active_user.user_level < 5:
            if self.has_level(5):

                if cmd == prefix + 'nick':
                    self.do_nick(cmd_arg)

                elif cmd == prefix + "checkuser":

                    if cmd == prefix + 'uinfo':
                        self.do_user_info(cmd_arg)

                elif cmd == prefix + 'movie':
                    #self.do_Movie(cmd_arg)
                    threading.Thread(target=self.do_Movie, args=(cmd_arg,)).start()

                elif cmd == prefix + 'jeopardy':
                    threading.Thread(target=self.jeo).start()

                elif cmd == prefix + 'word':
                    threading.Thread(target=self.GetScramble).start()

                elif cmd == prefix + 'hyde':
                    self.do_Hyde()

                elif cmd == prefix + 'go':
                    threading.Thread(target=self.schedule_random_message).start()

                elif cmd == prefix + 'stop':
                    threading.Thread(target=self.stop_random_message_loop).start()

                elif cmd == prefix + 'commands':
                    threading.Thread(target=self.do_commands).start()   

                elif cmd == prefix + "whiteknight":
                    self.send_chat_msg('White Knight has been awarded to %s' % cmd_arg)

                elif cmd == prefix + "nigold":
                    self.send_chat_msg('Initiating Niller Check for %s' % cmd_arg)
                    sleep(randint(1,2))
                    threading.Thread(target=self.nigtimer, args=(msg,)).start()
                    threading.Thread(target=self.nigtimer).start()
                    threading.Thread(target=self.check_msg, args=(msg,)).start()

                elif cmd == prefix + "niller":
                    self.send_chat_msg('Initiating Niller Check for %s' % cmd_arg)
                    sleep(randint(1,2))
                    threading.Thread(target=self.nigtimer, args=(msg,)).start()
                    threading.Thread(target=self.nigtimer).start()
                    threading.Thread(target=self.check_msg, args=(msg,)).start()


                elif cmd == prefix + "bongskank":
                    self.send_chat_msg('Initiating Bongskank Check for %s' % cmd_arg)
                    sleep(randint(1,2))
                    self.do_banlist_search(cmd_arg)

                if cmd == prefix + 'acspy':
                    threading.Thread(target=self.do_account_spy, args=(cmd_arg,)).start()

                elif cmd == prefix + 'yt':
                    threading.Thread(target=self.do_tube, args=(cmd_arg,)).start()

                elif cmd == prefix + 'yt':
                    webbrowser.open('http://%s' % cmd_arg)

                elif cmd == prefix + 'say':
                    os.system('espeak %s' % cmd_arg)

                elif cmd == prefix + 'wav':
                    os.system('play %s.wav -q' % cmd_arg)

                # Other API commands.
                elif cmd == prefix + 'urb777':
                    threading.Thread(target=self.do_search_urban_dictionary, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ai':
                    threading.Thread(target=self.do_ai, args=(cmd_arg,)).start()

                elif cmd == prefix + 'wea':
                   threading.Thread(target=self.do_weather_search, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ip':
                   threading.Thread(target=self.do_whois_ip, args=(cmd_arg,)).start()

                # Just for fun.
                elif cmd == prefix + 'cn':
                    threading.Thread(target=self.do_chuck_noris).start()

                # Just for fun.
                elif cmd == prefix + 'check':
                    threading.Thread(target=self.do_check).start()

                #elif cmd == prefix + '8ball':
                    #self.do_8ball(cmd_arg)
                
                elif cmd == prefix + 'scope':
                    self.do_scope(cmd_arg)

                elif cmd == prefix + 'fact':
                    self.do_fact()

                elif cmd == prefix + 'joke':
                    #self.do_joke()
                    self.send_chat_msg('Joke API Disabled.')
                   
                elif cmd == prefix + 'mood':
                    self.do_mood()
                     
                elif cmd == prefix + 'roll':
                    self.do_dice()
                    
                elif cmd == prefix + "cookie":
                    self.do_fortune()
                    
                elif cmd == prefix + "ltc":
                    self.do_ltc()
                    
                elif cmd == prefix + "btc":
                    self.do_bitcoin()
                    
                elif cmd == prefix + "xmr":
                    self.do_xmr()
                    
                elif cmd == prefix + "eth":
                    self.do_eth()

                elif cmd == prefix + "sia":
                    self.do_sia()

                elif cmd == prefix + "gank":
                    self.do_gank()

                elif cmd == prefix + "alert":
                    self.do_alert()

                #elif cmd == prefix + "n":
                    #self.do_niller()

                #elif cmd == prefix + "alert":
                    #self.do_alert()

                #elif cmd == prefix + "oof":
                    #self.do_oof()

                #elif cmd == prefix + "train":
                    #self.do_train()

                #elif cmd == prefix + "whistle":
                    #self.do_whistle()

                #elif cmd == prefix + "pedo":
                    #self.do_pedo()

                #elif cmd == prefix + "noob":
                    #self.do_newb()
                    
                elif cmd == prefix + "pot":
                    self.do_pot()

                elif cmd == prefix + "jokes":
                    self.do_joke()

                elif cmd == prefix + "line":
                    self.do_line()    
                    
                elif cmd == prefix + "advice":
                    self.do_Advice()  

                elif cmd == prefix + "mom":
                    self.do_mom()
                  
                elif cmd == prefix + "trump":
                    self.do_Trump()
                    
                elif cmd == prefix + "geek":
                    self.do_Geek()

                elif cmd == prefix + "tokes777":
                    threading.Thread(target=self.toketimer).start()
                    #self.do_whistle()

                elif cmd == prefix + "tokes":
                    threading.Thread(target=self.toketimer).start()
                    #self.do_whistle()

                #elif cmd == prefix + "cracktokes":
                    #threading.Thread(target=self.cracktimer).start()

                #elif cmd == prefix + "methtokes":
                    #threading.Thread(target=self.methtimer).start()

                #elif cmd == prefix + "z123":
                    #threading.Thread(target=self.z123).start()

      		    #Bender · Isolate
                #elif cmd == prefix + 'yt':
                    
                   #threading.Thread(target=self.do_play_youtube, args=(cmd_arg,)).start() 
                 
                elif cmd == prefix + 'tes':

                	self.send_chat_msg("https://greasyfork.org/en/scripts/389657-tinychat-enhancement-suite-tes")
                
                elif cmd == prefix + 'q':
                    self.do_playlist_status()

                elif cmd == prefix + 'n':
                    self.do_next_tune_in_playlist()

                elif cmd == prefix + 'np':
                    self.do_now_playing()

                elif cmd == prefix + 'wp':
                    self.do_who_plays()

                elif cmd == prefix + 'skip':
                    self.do_skip()

            #if cmd == prefix + 'msgme':
             #self.do_pmme()

            # Print command to console.
            self.console_write(pinylib.COLOR['yellow'], self.active_user.nick + ': ' + cmd + ' ' + cmd_arg)
        else:
            #  Print chat message to console.
            self.console_write(pinylib.COLOR['green'], self.active_user.nick + ': ' + msg)
            
        self.active_user.last_msg = msg

    def do_vip(self):
        """ Toggles if public commands are public or not. """
        pinylib.CONFIG.B_vip = not pinylib.CONFIG.B_vip
        self.send_chat_msg('VIP Enabled: %s' % pinylib.CONFIG.B_vip)

    def do_vipcheck(self):
        """ Toggles if public commands are public or not. """
        pinylib.CONFIG.B_CheckUser = not pinylib.CONFIG.B_CheckUser
        self.send_chat_msg('VIP Check Enabled: %s' % pinylib.CONFIG.B_vip)

    def nigtimer(self, msg):
        should_be_banned = False
        chat_words = msg.split(' ')
        for bad in pinylib.CONFIG.B_NIGWORDS:
            if bad.startswith('*'):
                _ = bad.replace('*', '')
                if _ in msg:
                    should_be_banned = True
            elif bad in chat_words:
                should_be_banned = True
        self.send_chat_msg('Are you a niller, %s?' % self.active_user.nick)
        self.active_user.last_msg = msg
        time.sleep(1 * 60)
        if _ in msg:
            should_be_banned = True
        if should_be_banned:
            self.send_chat_msg('Anti-Niller Defense System Activated.')
            self.send_kick_msg(self.active_user.id)
        else:
            self.send_chat_msg('Anti-Niller Defense System Deactivated.')

    running = True  # Initialize the flag here.

    def schedule_random_message(self):
        with open('words.txt', 'r') as words_file:
            words = words_file.read().splitlines()

        while self.running:  # Check the flag to continue or stop the loop.
            # Generate a random sentence from the words in words.txt.
            num_words = random.randint(3, 10)  # Adjust the range as needed.
            random_sentence = ' '.join(random.sample(words, num_words))
            self.send_chat_msg(random_sentence)

            # Sleep for 5 minutes (30 seconds).
            time.sleep(30)

    def stop_random_message_loop(self):
        self.running = False  # Set the flag to False to stop the loop

    def schedule_random_message2(self):
        while True:
            # Generate your random message here.
            random_message = "This is a random message."
            self.send_chat_msg(random_message)

            # Sleep for 5 minutes (30 seconds).
            time.sleep(30)

    def toketimer(self):
        self.send_chat_msg('Tokes in 3 mins.')
        time.sleep(1 * 60)
        self.send_chat_msg('Tokes in 2 mins.')
        time.sleep(1 * 60)
        self.send_chat_msg('Tokes in 1 mins.')
        time.sleep(1 * 60)
        self.send_chat_msg('Tokes started.')

    def cracktimer(self):
        self.send_chat_msg('Crack tokes in 1 mins.')
        time.sleep(1 * 60)
        self.send_chat_msg('Crack tokes started. Fire up those crackpipes, boys!')

    def methtimer(self):
        self.send_chat_msg('Meth tokes in 1 mins.')
        time.sleep(1 * 60)
        self.send_chat_msg("Meth tokes started. Let's get those meth pipes sizzlin'!")

    def z123(self):
        self.send_chat_msg('!allowcam7')
        sleep(randint(29,31))
        self.send_chat_msg('!allowcam7')

    def meksleeptimer(self):
        self.send_chat_msg('Meklin has gone to bed! Waking in 8 hours...')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin wakes in 7 hours')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin wakes in 6 hours')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin wakes in 5 hours')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin wakes in 4 hours')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin wakes in 3 hours')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin wakes in 2 hours')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin wakes in 1 hours')
        time.sleep(60 * 60)
        self.send_chat_msg('Meklin is awake.')

    def toketimer2(self):
        self.send_chat_msg('Tokes in 1 mins.')
        time.sleep(1 * 30)
        self.send_chat_msg('Tokes started.')

    def jeo(self):
        url = "http://jservice.io/api/random"
        out = requests.get(url).text
        resp_dict = json.loads(out)
        question = resp_dict[0]['question']
        answer = resp_dict[0]['answer']


        self.send_chat_msg('Jeopoardy Question: \n"' + question + '."')
        
        time.sleep(20)
        self.send_chat_msg('Jeopardy Answer (what/who is/are):\n "' + answer + '."')
     
    def GetScramble(self):

            words = ["arugola",
            "assenters",
            "atlee",
            "balatas",
            "basophilic",
            "bastinading",
            "begotten",
            "blameful",
            "bloodthirstiest",
            "bribeworthy",
            "burnoose",
            "calcaneonavicular",
            "cautionry",
            "cesure",
            "chimed",
            "classes",
            "commemorating",
            "cuchia",
            "decemviral",
            "decrepitness",
            "deloul",
            "doweled",
            "emeute",
            "excipule",
            "fractionizing",
            "galvanoplastically",
            "ganglionated",
            "gastrothecal",
            "gestalter",
            "gonidiferous",
            "gusle",
            "hairweaver",
            "hajji",
            "handmaid",
            "helminthosporium",
            "homecrofting",
            "immeasurably",
            "impregnant",
            "impunible",
            "infusedly",
            "initialed",
            "kahar",
            "kokum",
            "lactify",
            "lifen",
            "localistic",
            "manchild",
            "marrowed",
            "mennuet",
            "metachromatism",
            "mezuzah",
            "mishmi",
            "mothball",
            "nonaudibility",
            "nonemendation",
            "nonmilitarily",
            "oecist",
            "olfactories",
            "oppugner",
            "outpoll",
            "overfertility",
            "participatively",
            "pastils",
            "petrol",
            "polydomous",
            "polygalaceous",
            "porocephalus",
            "prissiest",
            "prodigy",
            "prussianization",
            "quantitied",
            "rancheros",
            "reargues",
            "reliability",
            "renopulmonary",
            "shakiest",
            "showerier",
            "sinuous",
            "speckled",
            "speedaway",
            "strawflower",
            "subcontraoctave",
            "sula",
            "swims",
            "tenfoldness",
            "tetraketone",
            "thoracoacromial",
            "tidecoach",
            "toxicology",
            "trespassory",
            "trochoids",
            "turkology",
            "unalerted",
            "unbarren",
            "unbutchered",
            "unexpiring",
            "unmangled",
            "unspiritedly",
            "unteeming",
            "vaccinee"]

            word = random.choice(words)


            self.send_chat_msg('Scrambled Word: \n"' + ''.join(random.sample(word, len(word))))
            time.sleep(20)
            self.send_chat_msg('Scrambled Word Answer:\n "' + word + '."')
    # Level 1 Command methods.
    def do_make_mod(self, account):
        """
        Make a tinychat account a room moderator.

        :param account: The account to make a moderator.
        :type account: str
        """
        if self.is_client_owner:
            if len(account) is 0:
                self.send_chat_msg('Missing account name.')
            else:
                tc_user = self.privacy_.make_moderator(account)
                if tc_user is None:
                    self.send_chat_msg('The account is invalid.')
                elif not tc_user:
                    self.send_chat_msg('%s is already a moderator.' % account)
                elif tc_user:
                    self.send_chat_msg('%s was made a room moderator.' % account)

    def do_remove_mod(self, account):
        """
        Removes a tinychat account from the moderator list.

        :param account: The account to remove from the moderator list.
        :type account: str
        """
        if self.is_client_owner:
            if len(account) is 0:
                self.send_chat_msg('Missing account name.')
            else:
                tc_user = self.privacy_.remove_moderator(account)
                if tc_user:
                    self.send_chat_msg('%s is no longer a room moderator.' % account)
                elif not tc_user:
                    self.send_chat_msg('%s is not a room moderator.' % account)

    def do_directory(self):
        """ Toggles if the room should be shown on the directory. """
        if self.is_client_owner:
            if self.privacy_.show_on_directory():
                self.send_chat_msg('Room IS shown on the directory.')
            else:
                self.send_chat_msg('Room is NOT shown on the directory.')

    def do_push2talk(self):
        """ Toggles if the room should be in push2talk mode. """
        if self.is_client_owner:
            if self.privacy_.set_push2talk():
                self.send_chat_msg('Push2Talk is enabled.')
            else:
                self.send_chat_msg('Push2Talk is disabled.')

    def do_green_room(self):
        """ Toggles if the room should be in greenroom mode. """
        if self.is_client_owner:
            if self.privacy_.set_greenroom():
                self.send_chat_msg('Green room is enabled.')
            else:
                self.send_chat_msg('Green room is disabled.')

    def do_clear_room_bans(self):
        """ Clear all room bans. """
        if self.is_client_owner:
            if self.privacy_.clear_bans():
                self.send_chat_msg('All room bans was cleared.')

    def do_kill(self):
        """ Kills the bot. """
        self.disconnect()

    def do_reboot(self):
        """ Reboots the bot. """
        self.reconnect()

    # Level 2 Command Methods.
    def do_media_info(self):
        """ Show information about the currently playing youtube. """
        if self.is_client_mod and self.playlist.has_active_track:
            self.send_chat_msg(
                'Playlist Tracks: ' + str(len(self.playlist.track_list)) + '\n' +
                'Track Title: ' + self.playlist.track.title + '\n' +
                'Track Index: ' + str(self.playlist.track_index) + '\n' +
                'Elapsed Track Time: ' + self.format_time(self.playlist.elapsed) + '\n' +
                'Remaining Track Time: ' + self.format_time(self.playlist.remaining)
            )

    # Level 3 Command Methods.
    def do_op_user(self, user_name):
        """
        Lets the room owner, a mod or a bot controller make another user a bot controller.

        :param user_name: The user to op.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is not None:
                    _user.user_level = 4
                    self.send_chat_msg('%s is now a bot controller (L4)' % user_name)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    def do_deop_user(self, user_name):
        """
        Lets the room owner, a mod or a bot controller remove a user from being a bot controller.

        :param user_name: The user to deop.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is not None:
                    _user.user_level = 5
                    self.send_chat_msg('%s is not a bot controller anymore (L5)' % user_name)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    def do_guests(self):
        """ Toggles if guests are allowed to join the room or not. """
        pinylib.CONFIG.B_ALLOW_GUESTS = not pinylib.CONFIG.B_ALLOW_GUESTS
        self.send_chat_msg('Allow Guests: %s' % pinylib.CONFIG.B_ALLOW_GUESTS)

        
    def do_spam(self):
        """ Toggles if guests are allowed to join the room or not. """
        pinylib.config.B_AllowSpam = not pinylib.config.B_AllowSpam
        self.send_chat_msg('Allow Spam: %s' % pinylib.config.B_AllowSpam)

    def do_lurkers(self):
        """ Toggles if lurkers are allowed or not. """
        pinylib.CONFIG.B_ALLOW_LURKERS = not pinylib.CONFIG.B_ALLOW_LURKERS
        self.send_chat_msg('Allowe Lurkers: %s' % pinylib.CONFIG.B_ALLOW_LURKERS)

    def do_guest_nicks(self):
        """ Toggles if guest nicks are allowed or not. """
        pinylib.CONFIG.B_ALLOW_GUESTS_NICKS = not pinylib.CONFIG.B_ALLOW_GUESTS_NICKS
        self.send_chat_msg('Allow Guest Nicks: %s' % pinylib.CONFIG.B_ALLOW_GUESTS_NICKS)

    def do_greet(self):
        """ Toggles if users should be greeted on entry. """
        pinylib.CONFIG.B_GREET = not pinylib.CONFIG.B_GREET
        self.send_chat_msg('Greet Users: %s' % pinylib.CONFIG.B_GREET)

    def do_public_cmds(self):
        """ Toggles if public commands are public or not. """
        pinylib.CONFIG.B_PUBLIC_CMD = not pinylib.CONFIG.B_PUBLIC_CMD
        self.send_chat_msg('Public Commands Enabled: %s' % pinylib.CONFIG.B_PUBLIC_CMD)

    def do_kick_as_ban(self):
        """ Toggles if kick should be used instead of ban for auto bans . """
        pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN = not pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN
        self.send_chat_msg('Use Kick As Auto Ban: %s' % pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN)

    def do_room_settings(self):
        """ Shows current room settings. """
        if self.is_client_owner:
            settings = self.privacy_.current_settings()
            self.send_chat_msg(
                'Broadcast Password: ' + settings['broadcast_pass'] + '\n' +
                'Room Password: ' + settings['room_pass'] + '\n' +
                'Login Type: ' + settings['allow_guest'] + '\n' +
                'Directory: ' + settings['show_on_directory'] + '\n' +
                'Push2Talk: ' + settings['push2talk'] + '\n' +
                'Greenroom: ' + settings['greenroom']
            )

    def do_lastfm_chart(self, chart_items):
        """
        Create a playlist from the most played tracks on last.fm.

        :param chart_items: The maximum amount of chart items.
        :type chart_items: str | int
        """
        if self.is_client_mod:
            if len(chart_items) == 0 or chart_items is None:
                self.send_chat_msg('Please specify the max amount of tracks you want.')
            else:
                try:
                    chart_items = int(chart_items)
                except ValueError:
                    self.send_chat_msg('Only numbers allowed.')
                else:
                    if 0 < chart_items < 30:
                        self.send_chat_msg('Please wait while creating a playlist...')
                        _items = lastfm.chart(chart_items)
                        if _items is not None:
                            self.playlist.add_list(self.active_user.nick, _items)
                            self.send_chat_msg('Added ' + str(len(_items)) + ' tracks from last.fm chart.')
                            if not self.playlist.has_active_track:
                                track = self.playlist.next_track
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Failed to retrieve a result from last.fm.')
                    else:
                        self.send_chat_msg('No more than 30 tracks.')

    def do_lastfm_random_tunes(self, max_tracks):
        """
        Creates a playlist from what other people are listening to on last.fm

        :param max_tracks: The miximum amount of tracks.
        :type max_tracks: str | int
        """
        if self.is_client_mod:
            if len(max_tracks) == 0 or max_tracks is None:
                self.send_chat_msg('Please specify the max amount of tunes you want.')
            else:
                try:
                    max_tracks = int(max_tracks)
                except ValueError:
                    self.send_chat_msg('Only numbers allowed.')
                else:
                    if 0 < max_tracks < 50:
                        self.send_chat_msg('Please wait while creating playlist...')
                        _items = lastfm.listening_now(max_tracks)
                        if _items is not None:
                            self.playlist.add_list(self.active_user.nick, _items)
                            self.send_chat_msg('Added ' + str(len(_items)) + ' tracks from last.fm')
                            if not self.playlist.has_active_track:
                                track = self.playlist.next_track
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Failed to retrieve a result from last.fm.')
                    else:
                        self.send_chat_msg('No more than 50 tracks.')

    def do_search_lastfm_by_tag(self, search_str):
        """
        Search last.fm for tunes matching a tag.

        :param search_str: The search tag to search for.
        :type search_str: str
        """
        if self.is_client_mod:
            if len(search_str) == 0 or search_str is None:
                self.send_chat_msg('Missing search string.')
            else:
                self.send_chat_msg('Please wait while creating playlist..')
                _items = lastfm.tag_search(search_str)
                if _items is not None:
                    self.playlist.add_list(self.active_user.nick, _items)
                    self.send_chat_msg('Added ' + str(len(_items)) + ' tracks from last.fm')
                    if not self.playlist.has_active_track:
                        track = self.playlist.next_track
                        self.send_yut_play(track.id, track.time, track.title)
                        self.timer(track.time)
                else:
                    self.send_chat_msg('Failed to retrieve a result from last.fm.')

    def do_youtube_playlist_search(self, search_str):
        """
        Search youtube for a playlist.

        :param search_str: The search term to search for.
        :type search_str: str
        """
        if self.is_client_mod:
            if len(search_str) == 0:
                self.send_chat_msg('Missing search string.')
            else:
                self.search_list = youtube.playlist_search(search_str)
                if len(self.search_list) > 0:
                    self.is_search_list_yt_playlist = True
                    _ = '\n'.join('(%s) %s' % (i, d['playlist_title']) for i, d in enumerate(self.search_list))
                    self.send_chat_msg(_)
                else:
                    self.send_chat_msg('Failed to find playlist matching search term: %s' % search_str)

    def do_play_youtube_playlist(self, int_choice):
        """
        Play a previous searched playlist.

        :param int_choice: The index of the playlist.
        :type int_choice: str | int
        """
        if self.is_client_mod:
            if self.is_search_list_yt_playlist:
                try:
                    int_choice = int(int_choice)
                except ValueError:
                    self.send_chat_msg('Only numbers allowed.')
                else:
                    if 0 <= int_choice <= len(self.search_list) - 1:
                        self.send_chat_msg('Please wait while creating playlist..')
                        tracks = youtube.playlist_videos(self.search_list[int_choice])
                        if len(tracks) > 0:
                            self.playlist.add_list(self.active_user.nick, tracks)
                            self.send_chat_msg('Added %s tracks from youtube playlist.' % len(tracks))
                            if not self.playlist.has_active_track:
                                track = self.playlist.next_track
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Failed to retrieve videos from youtube playlist.')
                    else:
                        self.send_chat_msg('Please make a choice between 0-%s' % str(len(self.search_list) - 1))
            else:
                self.send_chat_msg('The search list does not contain any youtube playlist id\'s.')

    def do_show_search_list(self):
        """ Show what the search list contains. """
        if self.is_client_mod:
            if len(self.search_list) == 0:
                self.send_chat_msg('The search list is empty.')
            elif self.is_search_list_yt_playlist:
                _ = '\n'.join('(%s) - %s' % (i, d['playlist_title']) for i, d in enumerate(self.search_list))
                self.send_chat_msg('Youtube Playlist\'s\n' + _)
            else:
                _ = '\n'.join('(%s) %s %s' % (i, d['video_title'], self.format_time(d['video_time']))
                              for i, d in enumerate(self.search_list))
                self.send_chat_msg('Youtube Tracks\n' + _)

    # Level 4 Command Methods.
    def do_skip(self):
        """ Skip to the next item in the playlist. """
        if self.is_client_mod:
            if self.playlist.is_last_track is None:
                self.send_chat_msg('No tunes to skip. The playlist is empty.')
            elif self.playlist.is_last_track:
                self.send_chat_msg('This is the last track in the playlist.')
            else:
                self.cancel_timer()
                next_track = self.playlist.next_track
                self.send_yut_play(next_track.id, next_track.time, next_track.title)
                self.timer(next_track.time)

    def do_delete_playlist_item(self, to_delete):  # TODO: Make sure this is working.
        """
        Delete items from the playlist.

        :param to_delete: Item indexes to delete.
        :type to_delete: str
        """
        if self.is_client_mod:
            if len(self.playlist.track_list) == 0:
                self.send_chat_msg('The playlist is empty.')
            elif len(to_delete) == 0:
                self.send_chat_msg('No indexes provided.')
            else:
                indexes = None
                by_range = False

                try:
                    if ':' in to_delete:
                        range_indexes = map(int, to_delete.split(':'))
                        temp_indexes = range(range_indexes[0], range_indexes[1] + 1)
                        if len(temp_indexes) > 1:
                            by_range = True
                    else:
                        temp_indexes = map(int, to_delete.split(','))
                except ValueError as ve:
                    log.error('wrong format: %s' % ve)
                else:
                    indexes = []
                    for i in temp_indexes:
                        if i < len(self.playlist.track_list) and i not in indexes:
                            indexes.append(i)

                if indexes is not None and len(indexes) > 0:
                    result = self.playlist.delete(indexes, by_range)
                    if result is not None:
                        if by_range:
                            self.send_chat_msg('Deleted from index: %s to index: %s' %
                                               (result['from'], result['to']))
                        elif result['deleted_indexes_len'] is 1:
                            self.send_chat_msg('Deleted %s' % result['track_title'])
                        else:
                            self.send_chat_msg('Deleted tracks at index: %s' %
                                               ', '.join(result['deleted_indexes']))
                    else:
                        self.send_chat_msg('Nothing was deleted.')

    def do_media_replay(self):
        """ Replay the currently playing track. """
        if self.is_client_mod:
            if self.playlist.track is not None:
                self.cancel_timer()
                track = self.playlist.replay()
                self.send_yut_play(track.id, track.time, track.title)
                self.timer(track.time)

    def do_play_media(self):
        """ Play a track on pause . """
        if self.is_client_mod:
            if self.playlist.track is not None:
                if self.playlist.has_active_track:
                    self.cancel_timer()
                if self.playlist.is_paused:
                    self.playlist.play(self.playlist.elapsed)
                    self.send_yut_play(self.playlist.track.id, self.playlist.track.time,
                                       self.playlist.track.title, self.playlist.elapsed)
                    self.timer(self.playlist.remaining)

    def do_media_pause(self):
        """ Pause a track. """
        if self.is_client_mod:
            track = self.playlist.track
            if track is not None:
                if self.playlist.has_active_track:
                    self.cancel_timer()
                self.playlist.pause()
                self.send_yut_pause(track.id, track.time, self.playlist.elapsed)

    def do_close_media(self):
        """ Close a track playing. """
        if self.is_client_mod:
            if self.playlist.has_active_track:
                self.cancel_timer()
                self.playlist.stop()
                self.send_yut_stop(self.playlist.track.id, self.playlist.track.time, self.playlist.elapsed)


    def do_seek_media(self, time_point):
        """
        Time search a track.

        :param time_point: The time point in which to search to.
        :type time_point: str
        """
        if self.is_client_mod:
            if ('h' in time_point) or ('m' in time_point) or ('s' in time_point):
                offset = pinylib.string_util.convert_to_seconds(time_point)
                if offset == 0:
                    self.send_chat_msg('Invalid seek time.')
                else:
                    track = self.playlist.track
                    if track is not None:
                        if 0 < offset < track.time:
                            if self.playlist.has_active_track:
                                self.cancel_timer()
                            if self.playlist.is_paused:
                                self.playlist.pause(offset=offset)
                                self.send_yut_pause(track.id, track.time, offset)
                            else:
                                self.playlist.play(offset)
                                self.send_yut_play(track.id, track.time, track.title, offset)
                                self.timer(self.playlist.remaining)

    def do_clear_playlist(self):
        """ Clear the playlist for items."""
        if self.is_client_mod:
            if len(self.playlist.track_list) > 0:
                pl_length = str(len(self.playlist.track_list))
                self.playlist.clear()
                self.send_chat_msg('Deleted %s items in the playlist.' % pl_length)
            else:
                self.send_chat_msg('The playlist is empty, nothing to delete.')

    def do_playlist_info(self):  # TODO: this needs more work !
        """ Shows the next tracks in the playlist. """
        if self.is_client_mod:
            if len(self.playlist.track_list) > 0:
                tracks = self.playlist.get_tracks()
                if len(tracks) > 0:
                    # If i is 0 then mark that as the next track
                    _ = '\n'.join('(%s) - %s %s' % (track[0], track[1].title, self.format_time(track[1].time))
                                  for i, track in enumerate(tracks))
                    self.send_chat_msg(_)

    def do_youtube_search(self, search_str):
        """
        Search youtube for a list of matching candidates.

        :param search_str: The search term to search for.
        :type search_str: str
        """
        if self.is_client_mod:
            if len(search_str) == 0:
                self.send_chat_msg('Missing search string.')
            else:
                self.search_list = youtube.search_list(search_str, results=5)
                if len(self.search_list) > 0:
                    self.is_search_list_yt_playlist = False
                    _ = '\n'.join('(%s) %s %s' % (i, d['video_title'], self.format_time(d['video_time']))
                                  for i, d in enumerate(self.search_list))
                    self.send_chat_msg(_)
                else:
                    self.send_chat_msg('Could not find anything matching: %s' % search_str)

    def do_play_youtube_search(self, int_choice):
        """
        Play a track from a previous youtube search list.

        :param int_choice: The index of the track in the search.
        :type int_choice: str | int
        """
        if self.is_client_mod:
            if not self.is_search_list_yt_playlist:
                if len(self.search_list) > 0:
                    try:
                        int_choice = int(int_choice)
                    except ValueError:
                        self.send_chat_msg('Only numbers allowed.')
                    else:
                        if 0 <= int_choice <= len(self.search_list) - 1:

                            if self.playlist.has_active_track:
                                track = self.playlist.add(self.active_user.nick, self.search_list[int_choice])
                                self.send_chat_msg('Added (%s) %s %s' %
                                                   (self.playlist.last_index,
                                                    track.title, self.format_time(track.time)))
                            else:
                                track = self.playlist.start(self.active_user.nick, self.search_list[int_choice])
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Please make a choice between 0-%s' % str(len(self.search_list) - 1))
                else:
                    self.send_chat_msg('No youtube track id\'s in the search list.')
            else:
                self.send_chat_msg('The search list only contains youtube playlist id\'s.')

    def do_clear(self):
        """ Clears the chat box. """
        self.send_chat_msg('_\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
                           '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_')


    def do_nick(self, new_nick):
        """
        Set a new nick for the bot.

        :param new_nick: The new nick name.
        :type new_nick: str
        """
        if len(new_nick) is 0:
            self.nickname = pinylib.string_util.create_random_string(5, 25)
            self.set_nick()
        else:
            self.nickname = new_nick
            self.set_nick()

    def do_kick(self, user_name):
        """
        Kick a user out of the room.

        :param user_name: The username to kick.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            elif user_name == self.nickname:
                self.send_chat_msg('Action not allowed.')
            else:
                if user_name.startswith('*'):
                    user_name = user_name.replace('*', '')
                    _users = self.users.search_containing(user_name)
                    if len(_users) > 0:
                        for i, user in enumerate(_users):
                            if user.nick != self.nickname and user.user_level > self.active_user.user_level:
                                if i <= pinylib.CONFIG.B_MAX_MATCH_BANS - 1:
                                    self.send_kick_msg(user.id)
                else:
                    _user = self.users.search_by_nick(user_name)
                    if _user is None:
                        self.send_chat_msg('No user named: %s' % user_name)
                    elif _user.user_level < self.active_user.user_level:
                        self.send_chat_msg('Not allowed.')
                    else:
                        self.send_kick_msg(_user.id)

    def do_ban(self, user_name):
        """
        Ban a user from the room.

        :param user_name: The username to ban.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            elif user_name == self.nickname:
                self.send_chat_msg('Action not allowed.')
            else:
                if user_name.startswith('*'):
                    user_name = user_name.replace('*', '')
                    _users = self.users.search_containing(user_name)
                    if len(_users) > 0:
                        for i, user in enumerate(_users):
                            if user.nick != self.nickname and user.user_level > self.active_user.user_level:
                                if i <= pinylib.CONFIG.B_MAX_MATCH_BANS - 1:
                                    self.send_ban_msg(user.id)
                else:
                    _user = self.users.search_by_nick(user_name)
                    if _user is None:
                        self.send_chat_msg('No user named: %s' % user_name)
                    elif _user.user_level < self.active_user.user_level:
                        self.send_chat_msg('Not allowed.')
                    else:
                        self.send_ban_msg(_user.id)

    def do_bad_nick(self, bad_nick):
        """
        Adds a username to the nick bans file.

        :param bad_nick: The bad nick to write to the nick bans file.
        :type bad_nick: str
        """
        if self.is_client_mod:
            if len(bad_nick) is 0:
                self.send_chat_msg('Missing username.')
            elif bad_nick in pinylib.CONFIG.B_NICK_BANS:
                self.send_chat_msg('%s is already in list.' % bad_nick)
            else:
                pinylib.file_handler.file_writer(self.config_path,
                                                 pinylib.CONFIG.B_NICK_BANS_FILE_NAME, bad_nick)
                self.send_chat_msg('%s was added to file.' % bad_nick)
                self.load_list(nicks=True)

    def do_remove_ytlog(self, name):
        """
        Removes nick from the nick bans file.

        :param bad_nick: The bad nick to remove from the nick bans file.
        :type bad_nick: str
        """
        if self.is_client_mod:
            if len(name) is 0:
                self.send_chat_msg('Missing link...')
            else:
                if name in pinylib.CONFIG.B_Youtube_Play_List:
                    rem = pinylib.file_handler.remove_from_file(self.config_path,
                                                                pinylib.CONFIG.B_Youtube_Play_List,
                                                                name)
                    if rem:
                        self.send_chat_msg('%s was removed.' % bad_nick)
                        self.load_list(links=True)
                        
    def do_remove_bad_nick(self, bad_nick):
        """
        Removes nick from the nick bans file.

        :param bad_nick: The bad nick to remove from the nick bans file.
        :type bad_nick: str
        """
        if self.is_client_mod:
            if len(bad_nick) is 0:
                self.send_chat_msg('Missing username')
            else:
                if bad_nick in pinylib.CONFIG.B_NICK_BANS:
                    rem = pinylib.file_handler.remove_from_file(self.config_path,
                                                                pinylib.CONFIG.B_NICK_BANS_FILE_NAME,
                                                                bad_nick)
                    if rem:
                        self.send_chat_msg('%s was removed.' % bad_nick)
                        self.load_list(nicks=True)

    def do_bad_string(self, bad_string):
        """
        Adds a string to the string bans file.

        :param bad_string: The bad string to add to the string bans file.
        :type bad_string: str
        """
        if self.is_client_mod:
            if len(bad_string) is 0:
                self.send_chat_msg('Ban string can\'t be blank.')
            elif len(bad_string) < 1:
                self.send_chat_msg('Ban string to short: ' + str(len(bad_string)))
            elif bad_string in pinylib.CONFIG.B_STRING_BANS:
                self.send_chat_msg('%s is already in list.' % bad_string)
            else:
                pinylib.file_handler.file_writer(self.config_path,
                                                 pinylib.CONFIG.B_STRING_BANS_FILE_NAME, bad_string)
                self.send_chat_msg('%s was added to file.' % bad_string)
                self.load_list(strings=True)

    def do_remove_bad_string(self, bad_string):
        """
        Removes a string from the string bans file.

        :param bad_string: The bad string to remove from the string bans file.
        :type bad_string: str
        """
        if self.is_client_mod:
            if len(bad_string) is 0:
                self.send_chat_msg('Missing word string.')
            else:
                if bad_string in pinylib.CONFIG.B_STRING_BANS:
                    rem = pinylib.file_handler.remove_from_file(self.config_path,
                                                                pinylib.CONFIG.B_STRING_BANS_FILE_NAME,
                                                                bad_string)
                    if rem:
                        self.send_chat_msg('%s was removed.' % bad_string)
                        self.load_list(strings=True)

    def do_bad_account(self, bad_account_name):
        """
        Adds an account name to the account bans file.

        :param bad_account_name: The bad account name to add to the account bans file.
        :type bad_account_name: str
        """
        if self.is_client_mod:
            if len(bad_account_name) is 0:
                self.send_chat_msg('Account can\'t be blank.')
            elif len(bad_account_name) < 1:
                self.send_chat_msg('Account to short: ' + str(len(bad_account_name)))
            elif bad_account_name in pinylib.CONFIG.B_ACCOUNT_BANS:
                self.send_chat_msg('%s is already in list.' % bad_account_name)
            else:
                pinylib.file_handler.file_writer(self.config_path,
                                                 pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME,
                                                 bad_account_name)
                self.send_chat_msg('%s was added to file.' % bad_account_name)
                self.load_list(accounts=True)

    def do_remove_bad_account(self, bad_account):
        """
        Removes an account from the account bans file.

        :param bad_account: The badd account name to remove from account bans file.
        :type bad_account: str
        """
        if self.is_client_mod:
            if len(bad_account) is 0:
                self.send_chat_msg('Missing account.')
            else:
                if bad_account in pinylib.CONFIG.B_ACCOUNT_BANS:
                    rem = pinylib.file_handler.remove_from_file(self.config_path,
                                                                pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME,
                                                                bad_account)
                    if rem:
                        self.send_chat_msg('%s was removed.' % bad_account)
                        self.load_list(accounts=True)

    def do_list_info(self, list_type):
        """
        Shows info of different lists/files.

        :param list_type: The type of list to find info for.
        :type list_type: str
        """
        if self.is_client_mod:
            if len(list_type) is 0:
                self.send_chat_msg('Missing list type.')
            else:
                if list_type.lower() == 'bn':
                    if len(pinylib.CONFIG.B_NICK_BANS) is 0:
                        self.send_chat_msg('No items in this list.')
                    else:
                        self.send_chat_msg('%s nicks bans in list.' % len(pinylib.CONFIG.B_NICK_BANS))

                elif list_type.lower() == 'bs':
                    if len(pinylib.CONFIG.B_STRING_BANS) is 0:
                        self.send_chat_msg('No items in this list.')
                    else:
                        self.send_chat_msg('%s string bans in list.' % pinylib.CONFIG.B_STRING_BANS)

                elif list_type.lower() == 'ba':
                    if len(pinylib.CONFIG.B_ACCOUNT_BANS) is 0:
                        self.send_chat_msg('No items in this list.')
                    else:
                        self.send_chat_msg('%s account bans in list.' % pinylib.CONFIG.B_ACCOUNT_BANS)

                elif list_type.lower() == 'bl':
                    if len(self.users.banned_users) == 0:
                        self.send_chat_msg('The banlist is empty.')
                    else:
                        _ban_list = '\n'.join('(%s) %s:%s [%s]' %
                                              (i, banned_user.nick, banned_user.account, banned_user.ban_id)
                                              for i, banned_user in enumerate(self.users.banned_users))
                        if len(_ban_list) > 150:  # maybe have a B_MAX_MSG_LENGTH in config
                            # use string_util.chunk_string
                            pass
                        else:
                            self.send_chat_msg(_ban_list)

                elif list_type.lower() == 'mods':
                    if self.is_client_owner:
                        if len(self.privacy_.room_moderators) is 0:
                            self.send_chat_msg('There is currently no moderators for this room.')
                        elif len(self.privacy_.room_moderators) is not 0:
                            mods = ', '.join(self.privacy_.room_moderators)
                            self.send_chat_msg('Moderators: ' + mods)

    def do_user_info(self, user_name):
        """
        Shows user object info for a given user name.

        :param user_name: The user name of the user to show the info for.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is None:
                    self.send_chat_msg('No user named: %s' % user_name)
                else:
                    if _user.account and _user.tinychat_id is None:
                        user_info = pinylib.apis.tinychat.user_info(_user.account)
                        if user_info is not None:
                            _user.tinychat_id = user_info['tinychat_id']
                            _user.last_login = user_info['last_active']
                    online_time = (pinylib.time.time() - _user.join_time)

                    info = [
                        'User Level: ' + str(_user.user_level),
                        'Online Time: ' + self.format_time(online_time),
                        'Last Message: ' + str(_user.last_msg)
                    ]
                    if _user.tinychat_id is not None:
                        info.append('Account: ' + str(_user.account))
                        info.append('Tinychat ID: ' + str(_user.tinychat_id))
                        info.append('Last Login: ' + _user.last_login)

                    self.send_chat_msg('\n'.join(info))

    def do_cam_approve(self, user_name):
        if self.is_green_room and self.is_client_mod:
            if len(user_name) == 0 and self.active_user.is_waiting:
                self.send_cam_approve_msg(self.active_user.id)
            elif len(user_name) > 0:
                _user = self.users.search_by_nick(user_name)
                if _user is not None and _user.is_waiting:
                    self.send_cam_approve_msg(_user.id)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    def do_close_broadcast(self, user_name):
        """
        Close a users broadcast.

        :param user_name: The name of the user to close.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) == 0:
                self.send_chat_msg('Missing user name.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is not None and _user.is_broadcasting:
                    self.send_close_user_msg(_user.id)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    def do_banlist_search(self, user_name):
        """
        Search the banlist for matches.

        NOTE: This method/command was meant to be a private message command,
        but it seems like the private messages is broken, so for now
        it will be a room command.

        :param user_name: The user name or partial username to search for.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) == 0:
                self.send_chat_msg('Missing user name to search for.')
            else:
                self.bl_search_list = self.users.search_banlist_containing(user_name)
                if len(self.bl_search_list) == 0:
                    self.send_chat_msg('No banlist matches.')
                else:
                    _ban_list_info = '\n'.join('(%s) %s:%s [%s]' % (i, user.nick, user.account, user.ban_id)
                                               for i, user in enumerate(self.bl_search_list))
                    # maybe user string_util.chunk_string here
                    self.send_chat_msg(_ban_list_info)

    def do_forgive(self, user_index):
        """
        Forgive a user from the ban list search.

        NOTE: This method/command was meant to be a private message command,
        but it seems like the private messages is broken, so for now
        it will be a room command.

        :param user_index: The index in the ban list search.
        :type user_index: str | int
        """
        if self.is_client_mod:
            try:
                user_index = int(user_index)
            except ValueError:
                self.send_chat_msg('Only numbers allowed (%s)' % user_index)
            else:
                if len(self.bl_search_list) > 0:
                    if user_index <= len(self.bl_search_list) - 1:
                        self.send_unban_msg(self.bl_search_list[user_index].ban_id)
                    else:
                        if len(self.bl_search_list) > 1:
                            self.send_chat_msg(
                                'Please make a choice between 0-%s' % len(self.bl_search_list))
                else:
                    self.send_chat_msg('The ban search is empty.')

            # self.bl_search_list[:] = []

    def do_unban(self, user_name):
        """
        Un-ban the last banned user or a user by user name.

        NOTE: experimental. In case the user name match more than one
        user in the banlist, then the last banned user will be unbanned.

        :param user_name: The exact user name to unban.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name.strip()) == 0:
                self.send_chat_msg('Missing user name.')
            elif user_name == '/':  # shortcut to the last banned user.
                last_banned_user = self.users.last_banned
                if last_banned_user is not None:
                    self.send_unban_msg(last_banned_user.ban_id)
                else:
                    self.send_chat_msg('Failed to find the last banned user.')
            else:
                banned_user = self.users.search_banlist_by_nick(user_name)
                if banned_user is not None:
                    self.send_unban_msg(banned_user.ban_id)
                else:
                    self.send_chat_msg('No user named: %s in the banlist.' % user_name)

    # Public (Level 5) Command Methods.
    def do_playlist_status(self):
        """ Shows the playlist queue. """
        if self.is_client_mod:
            if len(self.playlist.track_list) == 0:
                self.send_chat_msg('The playlist is empty.')
            else:
                queue = self.playlist.queue
                if queue is not None:
                    self.send_chat_msg('%s items in the playlist, %s still in queue.' %
                                       (queue[0], queue[1]))

    def do_next_tune_in_playlist(self):
        """ Shows the next track in the playlist. """
        if self.is_client_mod:
            if self.playlist.is_last_track is None:
                self.send_chat_msg('The playlist is empty.')
            elif self.playlist.is_last_track:
                self.send_chat_msg('This is the last track.')
            else:
                pos, next_track = self.playlist.next_track_info()
                if next_track is not None:
                    self.send_chat_msg('(%s) %s %s' %
                                       (pos, next_track.title, self.format_time(next_track.time)))

    def do_now_playing(self):
        """ Shows what track is currently playing. """
        if self.is_client_mod:
            if self.playlist.has_active_track:
                track = self.playlist.track
                if len(self.playlist.track_list) > 0:
                    self.send_private_msg(self.active_user.id,
                                          '(%s) %s %s' % (self.playlist.current_index, track.title,
                                                          self.format_time(track.time)))
                else:
                    self.send_private_msg(self.active_user.id, '%s %s' %
                                          (track.title, self.format_time(track.time)))
            else:
                self.send_private_msg(self.active_user.id, 'No track playing.')

    def do_who_plays(self):
        """ Show who requested the currently playing track. """
        if self.is_client_mod:
            if self.playlist.has_active_track:
                track = self.playlist.track
                ago = self.format_time(int(pinylib.time.time() - track.rq_time))
                self.send_chat_msg('%s requested this track %s ago.' % (track.owner, ago))
            else:
                self.send_chat_msg('No track playing.')

    def do_version(self):
        """ Show version info. """
        self.send_private_msg(self.active_user.id, 'tinybot %s pinylib %s' %
                              (__version__, pinylib.__version__))

    def do_help(self):
        """ Posts a link to github readme/wiki or other page about the bot commands. """
        self.send_private_msg(self.active_user.id,
                              'Help: https://github.com/nortxort/tinybot-rtc/wiki/commands')
    def join_message():
        self.send_private_msg(self.active_user.id,
                              'This is an automatted message to fix a PM bug.')
    def do_uptime(self):
        """ Shows the bots uptime. """
        self.send_chat_msg('Bot-Uptime: ' + self.format_time(self.get_runtime()))

    def do_pmme(self):
        """ Opens a PM session with the bot. """
        self.send_private_msg(self.active_user.id, 'How can i help you %s?' % self.active_user.nick)

    def do_play_youtube(self, search_str):
        """
        Plays a youtube video matching the search term.

        :param search_str: The search term.
        :type search_str: str
        """
        
        log.info('user: %s:%s is searching youtube: %s' % (self.active_user.nick, self.active_user.id, search_str))
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_chat_msg('Please specify youtube title, id or link.')
            
            
            else:
                _youtube = youtube.search(search_str)

                
                if _youtube is None:
                    log.warning('youtube request returned: %s' % _youtube)
                    self.send_chat_msg('Could not find video: ' + search_str)

                else:
                    log.info('youtube found: %s' % _youtube)
                    if self.playlist.has_active_track:
                        track = self.playlist.add(self.active_user.nick, _youtube)
                        self.send_chat_msg('(%s) %s %s' %
                                           (self.playlist.last_index, track.title, self.format_time(track.time)))
                    else:
                        track = self.playlist.start(self.active_user.nick, _youtube)
                        self.send_yut_play(track.id, track.time, track.title)
                        self.timer(track.time)

    # == Tinychat API Command Methods. ==
    def do_account_spy(self, account):
        """
        Shows info about a tinychat account.

        :param account: tinychat account.
        :type account: str
        """
        if self.is_client_mod:
            if len(account) is 0:
                self.send_chat_msg('Missing username to search for.')
            else:
                tc_usr = pinylib.apis.tinychat.user_info(account)
                if tc_usr is None:
                    self.send_chat_msg('Could not find tinychat info for: %s' % account)
                else:
                    self.send_chat_msg('ID: %s, \nLast Login: %s' %
                                       (tc_usr['tinychat_id'], tc_usr['last_active']))

    def do_tube(self, search_str):

        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_chat_msg('Please specify something to look up.')
            else:
                yout = other.tube(search_str)
                if yout is None:
                    self.send_chat_msg('Could not find a definition for: %s' % search_str)
                else:
                    if len(yout) > 70:
                        chunks = pinylib.string_util.chunk_string(yout, 70)
                        for i in range(0, 2):
                            self.send_chat_msg(chunks[i])
                    else:
                        self.send_chat_msg(yout)


    # Class-level variable to track the last time do_ai method was called
    #last_do_ai_called = 0
    ai_lock = threading.Lock()

    def do_ai(self, cmd_arg, max_tokens=150, max_parts=1, delay_between_parts=1, min_response_length=3):
        with self.ai_lock:
        # Define your OpenAI API key
            api_key = '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'

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

    def do_search_urban_dictionary(self, search_str):
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_chat_msg('Please specify something to look up.')
            else:
                urban = other.urbandictionary_search(search_str)
                if urban is None:
                    self.send_chat_msg('Could not find a definition for: %s' % search_str)
                else:
                    if len(urban) > 70:
                        chunks = pinylib.string_util.chunk_string(urban, 70)
                        for i in range(0, 2):
                            self.send_chat_msg(chunks[i])
                    else:
                        self.send_chat_msg(urban)

    def do_weather_search(self, search_str):
        if len(search_str) is 0:
            self.send_chat_msg('Please specify a city to search for.')
        else:
            weather = other.weather_search(search_str)
            if weather is None:
                self.send_chat_msg('Could not find weather data for: %s' % search_str)
            else:
                self.send_chat_msg(weather)

    def do_whois_ip(self, ip_str):

        if len(ip_str) is 0:
            self.send_chat_msg('Please provide an IP address or domain.')
        else:
            whois = other.whois(ip_str)
            if whois is None:
                self.send_chat_msg('No info found for: %s' % ip_str)
            else:
                self.send_chat_msg(whois)

    # == Just For Fun Command Methods. ==
    def do_chuck_noris(self):
        """ Shows a chuck norris joke/quote. """
        chuck = other.chuck_norris()
        if chuck is not None:
            self.send_chat_msg(chuck)
            
    # == Just For Fun Command Methods. ==
    def do_check(self):
        self.send_chat_msg('Status: Online! - Bot-Uptime: ' + self.format_time(self.get_runtime()))    
    
    def do_commands(self):
        self.send_chat_msg('Public commands are located @ https://pastebin.com/CyKfR27Z')    
      
    def do_mood(self):

        self.send_chat_msg(locals_.get_mood())
     
    def do_Movie(self, title):

        self.send_chat_msg(locals_.getMovie(title))
     
  
    def do_Hyde(self):

        self.send_chat_msg(locals_.getHyde())
     
  
               
    def do_8ball(self, question):
        """
        Shows magic eight ball answer to a yes/no question.

        :param question: The yes/no question.
        :type question: str
        """
        if len(question) is 0:
            self.send_chat_msg('Question.')
        else:
            self.send_chat_msg('8Ball says:  %s' % locals_.eight_ball())

    def do_scope(self, month):
        """
        Shows magic eight ball answer to a yes/no question.

        :param question: The yes/no question.
        :type question: str
        """
        if len(month) is 0:
            self.send_chat_msg('Sign required..')
        else:
            self.send_chat_msg('Scope says:  %s' % locals_.getScope(month))

    def do_number(self, number):
        """
        Shows magic eight ball answer to a yes/no question.

        :param question: The yes/no question.
        :type question: str
        """
        if len(number) is 0:
            self.send_chat_msg('Number required..')
        else:
            self.send_chat_msg('Number says:  %s' % locals_.getNumber(number))

    def do_fact(self):

        
        self.send_chat_msg('Fact is:  %s' % locals_.get_Animal())

    def do_joke(self):

        
        self.send_chat_msg('Fact is:  %s' % locals_.getJokes())

    def do_line(self):
      
        self.send_chat_msg(locals_.getOneliner())    

    def do_mom(self):

        
        self.send_chat_msg('Api is down')        

    def do_Advice(self):

        
        self.send_chat_msg('Advice is: %s' % locals_.advice())    
        #self.send_chat_msg('Disabled by x0r till further notice')

    def do_Geek(self):

        
        self.send_chat_msg(locals_.getGeek())    
        #self.send_chat_msg('Disabled by x0r till further notice')

    def do_bitcoin(self):

        
        self.send_chat_msg('Cryptowatch says: %s' % locals_.getbitcoin())
        
    def do_eth(self):

        self.send_chat_msg('Cryptowatch says: %s' % locals_.geteth())

    def do_xmr(self):

        self.send_chat_msg('Cryptowatch says: %s' % locals_.getxmr())

    def do_ltc(self):

        self.send_chat_msg('Cryptowatch says: %s' % locals_.getlitecoins())

    def do_pot(self):

        self.send_chat_msg('Cryptowatch says: %s' % locals_.getpot())

    def do_sia(self):

        self.send_chat_msg('Cryptowatch says: %s' % locals_.getsia())

    def do_gank(self):

        self.send_chat_msg('Gods gift to women and mankind.')

    #def do_alert(self):
        #self.send_chat_msg('alert sent to meklin')
        #os.system("play ALERT1.WAV")

    #def do_niller(self):
        #os.system("play NILLER.WAV")

    #def do_oof(self):
        #os.system("play OOF.WAV")

    #def do_newb(self):
        #os.system("play NEWBIE.WAV")

    #def do_pedo(self):
        #os.system("play PEDO.WAV")

    #def do_train(self):
        #os.system("play TRAIN.WAV")

    #def do_whistle(self):
        #os.system("play TRAIN2.WAV")

    def do_jokes(self):
        self.send_chat_msg('Joker says: %s' % locals_.get_joke())
  
    def do_dice(self):
        """ roll the dice. """
        self.send_chat_msg('The dice rolled: %s' % locals_.roll_dice())

    def do_flip_coin(self):
        """ Flip a coin. """
        self.send_chat_msg('The coin was: %s' % locals_.flip_coin())

    def do_fortune(self):
        """ Flip a coin. """
        self.send_chat_msg('The fortune was: %s' % locals_.fortune())

    def do_Trump(self):
        """ Flip a coin. """
        self.send_chat_msg('Trump says: %s' % locals_.getTrump())

    def private_message_handler(self, private_msg):
        """
        Private message handler.

        Overrides private_message_handler in pinylib
        to enable private commands.

        :param private_msg: The private message.
        :type private_msg: str
        """
        
        prefix = pinylib.CONFIG.B_PREFIX
        # Split the message in to parts.
        pm_parts = private_msg.split(' ')
        # parts[0] is the command..
        pm_cmd = pm_parts[0].lower().strip()
        # The rest is a command argument.
        pm_arg = ' '.join(pm_parts[1:]).strip()
        
        #Bots operating owner
        if self.has_level(1):
            if self.is_client_owner:
                pass

            #if pm_cmd == prefix + 'key':
               # self.do_key(pm_arg)

            elif pm_cmd == prefix + 'clrbn':
                self.do_clear_bad_nicks()

            elif pm_cmd == prefix + 'clrbs':
                self.do_clear_bad_strings()

            elif pm_cmd == prefix + 'clrban':
                self.do_clear_bad_accounts()
        


        # Public commands.
        if self.has_level(5):
            if pm_cmd == prefix + 'opme1':
                self.do_opme(pm_arg)

        # Print to console.
        #msg = str(private_msg).replace(pinylib.CONFIG.B_KEY, '***KEY***'). \
           # replace(pinylib.CONFIG.B_SUPER_KEY, '***SUPER KEY***')

        #self.console_write(pinylib.COLOR['white'], 'Private message from %s: %s' % (self.active_user.nick, msg))

    def do_key(self, new_key):
        """
        Shows or sets a new secret bot controller key.

        :param new_key: The new secret key.
        :type new_key: str
        """
        if len(new_key) == 0:
            self.send_private_msg(self.active_user.id, 'The current secret key is: %s' % pinylib.CONFIG.B_KEY)
        elif len(new_key) < 6:
            self.send_private_msg(self.active_user.id, 'The key is to short, it must be atleast 6 characters long.'
                                                       'It is %s long.' % len(new_key))
        elif len(new_key) >= 6:
            # reset current bot controllers.
            for user in self.users.all:
                if self.users.all[user].user_level is 2 or self.users.all[user].user_level is 4:
                    self.users.all[user].user_level = 5

            pinylib.CONFIG.B_KEY = new_key
            self.send_private_msg(self.active_user.id, 'The key was changed to: %s' % new_key)

    def do_clear_bad_nicks(self):
        """ Clear the nick bans file. """
        pinylib.CONFIG.B_NICK_BANS[:] = []
        pinylib.file_handler.delete_file_content(self.config_path, pinylib.CONFIG.B_NICK_BANS_FILE_NAME)

    def do_clear_bad_strings(self):
        """ Clear the string bans file. """
        pinylib.CONFIG.B_STRING_BANS[:] = []
        pinylib.file_handler.delete_file_content(self.config_path, pinylib.CONFIG.B_STRING_BANS_FILE_NAME)

    def do_clear_bad_accounts(self):
        """ Clear the account bans file. """
        pinylib.CONFIG.B_ACCOUNT_BANS[:] = []
        pinylib.file_handler.delete_file_content(self.config_path, pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME)

    def do_opme(self, key):
        """
        Make a user a bot controller if the correct key is provided.

        :param key: The secret bot controller key.
        :type key: str
        """
        if len(key) == 0:
            self.send_private_msg(self.active_user.id, 'Missing key.')
        elif key == pinylib.CONFIG.B_SUPER_KEY:
            if self.is_client_owner:
                self.active_user.user_level = 1
                self.send_private_msg(self.active_user.id, 'You are now a super mod.')
            else:
                self.send_private_msg(self.active_user.id, 'The client is not using the owner account.')
        elif key == pinylib.CONFIG.B_KEY:
            if self.is_client_mod:
                self.active_user.user_level = 2
                self.send_private_msg(self.active_user.id, 'You are now a bot controller.')
            else:
                self.send_private_msg(self.active_user.id, 'The client is not moderator.')
        else:
            self.send_private_msg(self.active_user.id, 'Wrong key.')

    # Timer Related.
    def timer_event(self):
        """ This gets called when the timer has reached the time. """
        if len(self.playlist.track_list) > 0:
            if self.playlist.is_last_track:
                if self.is_connected:
                    self.send_chat_msg('Resetting playlist.')
                self.playlist.clear()
            else:
                track = self.playlist.next_track
                if track is not None and self.is_connected:
                    self.send_yut_play(track.id, track.time, track.title)
                self.timer(track.time)

    def timer(self, event_time):
        """
        Track event timer.

        This will cause an event to occur once the time is done.

        :param event_time: The time in seconds for when an event should occur.
        :type event_time: int | float
        """
        self.timer_thread = threading.Timer(event_time, self.timer_event)
        self.timer_thread.start()

    def cancel_timer(self):
        """ Cancel the track timer. """
        if self.timer_thread is not None:
            if self.timer_thread.is_alive():
                self.timer_thread.cancel()
                self.timer_thread = None
                return True
            return False
        return False

    # Helper Methods.
    def options(self):
        """ Load/set special options. """
        log.info('options: is_client_owner: %s, is_client_mod: %s' % (self.is_client_owner, self.is_client_mod))
        if self.is_client_owner:
            self.get_privacy_settings()
        if self.is_client_mod:
            self.send_banlist_msg()
            self.load_list(nicks=True, accounts=True, strings=True, links=True)

    def get_privacy_settings(self):
        """ Parse the privacy settings page. """
        log.info('Parsing %s\'s privacy page.' % self.account)
        self.privacy_ = privacy.Privacy(proxy=None)
        self.privacy_.parse_privacy_settings()

    def load_list(self, nicks=False, accounts=False, strings=False, links=False):
        """
        Loads different list to memory.

        :param nicks: bool, True load nick bans file.
        :param accounts: bool, True load account bans file.
        :param strings: bool, True load ban strings file.
        """
        if nicks:
            pinylib.CONFIG.B_NICK_BANS = pinylib.file_handler.file_reader(self.config_path,
                                                                          pinylib.CONFIG.B_NICK_BANS_FILE_NAME)
        if accounts:
            pinylib.CONFIG.B_ACCOUNT_BANS = pinylib.file_handler.file_reader(self.config_path,
                                                                             pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME)
        if strings:
            pinylib.CONFIG.B_STRING_BANS = pinylib.file_handler.file_reader(self.config_path,
                                                                            pinylib.CONFIG.B_STRING_BANS_FILE_NAME)
        if links:
            pinylib.CONFIG.B_STRING_BANS = pinylib.file_handler.file_reader(self.config_path,
                                                                            pinylib.CONFIG.B_Youtube_Play_List)    
        #pinylib.CONFIG.B_Youtube_Play_List
    def has_level(self, level):
        """
        Checks the active user for correct user level.

        :param level: The level to check the active user against.
        :type level: int
        :return: True if the user has correct level, else False
        :rtype: bool
        """
        if self.active_user.user_level == 6:
            return False
        elif self.active_user.user_level <= level:
            return True
        return False

    @staticmethod
    def format_time(time_stamp, is_milli=False):
        """
        Converts a time stamp as seconds or milliseconds to (day(s)) hours minutes seconds.

        :param time_stamp: Seconds or milliseconds to convert.
        :param is_milli: The time stamp to format is in milliseconds.
        :return: A string in the format (days) hh:mm:ss
        :rtype: str
        """
        if is_milli:
            m, s = divmod(time_stamp / 1000, 60)
        else:
            m, s = divmod(time_stamp, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d == 0 and h == 0:
            human_time = '%02d:%02d' % (m, s)
        elif d == 0:
            human_time = '%d:%02d:%02d' % (h, m, s)
        else:
            human_time = '%d Day(s) %d:%02d:%02d' % (d, h, m, s)
        return human_time

    def check_msg(self, msg):
        """
        Checks the chat message for ban string.

        :param msg: The chat message.
        :type msg: str
        """
        should_be_banned = False
        chat_words = msg.split(' ')
        for bad in pinylib.CONFIG.B_STRING_BANS:
            if bad.startswith('*'):
                _ = bad.replace('*', '')
                if _ in msg:
                    should_be_banned = True
            elif bad in chat_words:
                should_be_banned = True
        if should_be_banned:
            if pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN:
                self.send_kick_msg(self.active_user.id)
            else:
                self.send_ban_msg(self.active_user.id)


