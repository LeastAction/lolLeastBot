#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      MTJacobson
#
# Created:     31/05/2014
# Copyright:   (c) MTJacobson 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import xmpp
import xmpp.protocol
import xml.etree.ElementTree as ET
import time
import threading
import os
import sys
import lol_api
from chatterbotapi import ChatterBotFactory, ChatterBotType
from colorama import init, Fore
import logging
import logging.handlers
init()

class RiotServers():
    BR = 'br'
    EUN = 'eun1'
    EUW = 'eu'
    NA = 'na1'
    KR = 'kr'
    OCE = 'oc1'
    RU = 'ru'
    TR = 'tr'

class Settings():
    USER = 'LeastBot'
    PASS = "AIR_" + open(os.path.join(os.getcwd(),'lol_pass.txt'), "r").readline()
    DEFAULT_SERVER = 'chat.{0}.lol.riotgames.com'.format(RiotServers.NA)
    PORT = 5223
    STATUS_MSG = "<body>\
        <profileIcon>0</profileIcon>\
        <level>1</level>\
        <wins>0</wins>\
        <leaves>0</leaves>\
        <odinWins>0</odinWins>\
        <odinLeaves>0</odinLeaves>\
        <queueType>RANKED_SOLO_5x5</queueType>\
        <rankedWins>0</rankedWins>\
        <rankedLosses>0</rankedLosses>\
        <rankedRating>0</rankedRating>\
        <tier>BRONZE</tier>\
        <gameStatus>outOfGame</gameStatus>\
        <statusMsg>!help for information</statusMsg>\
        </body>"
    JIDTONAME_PATH = os.path.join(os.getcwd(),'JIDtoName.txt')
    LOG_FILENAME = "logs\\run_history.log"


class ChatterBots():
    def __init__(self):
        self.factory = ChatterBotFactory()
        self.jabberwacky = self.factory.create(ChatterBotType.JABBERWACKY)
        self.conversations = {}

    def respond(self,question, conversation_id):
        try:
            self.conversations[conversation_id]
        except KeyError:
            self.conversations[conversation_id] = self.jabberwacky.create_session()

        return self.conversations[conversation_id].think(question)

class BotConnection():
    RiotAPI = lol_api.RiotAPI(verbosity=1)
    def __init__(self, username, password, server, logger):
        self.username =  username
        self.password = password
        self.client = None
        self.server = server
        self.port = Settings.PORT
        self.bot = ChatterBots()
        self.auto_accept = True
        self.debug = []
        self.listening = True
        self.logger = logger
        self.interpreter = CommandInterpreter(self)
        self.live_friends = {}

    @staticmethod
    def load_text(path):
        try:
            text_file = open(path, "r")
        except IOError:
            self.logger.warning("ERROR: Could not open {0}".format(path))
            return {}
        lines = text_file.read().split('\n')

        text_dict = {}
        for line in lines:
            a = line.split("|")
            text_dict[a[0]] = a[1]
        return text_dict

    def connect(self):
        self.client = xmpp.Client('pvp.net',debug=self.debug)
        if self.client.connect(server=(self.server, self.port)) == "":
            self.logger.critical("{0}: connect failed.".format(self.username))
            self.client = None
            return
        if self.client.auth(self.username, self.password, "xiff") == None:
            self.logger.critical("{0}: auth failed.".format(self.username))
            self.client = None
            return
        if self.client.isConnected():
            self.client.sendInitPresence(requestRoster=1)
            pres = xmpp.Presence(show='chat')
            pres.setStatus(Settings.STATUS_MSG)
            self.client.send(pres)

        self.logger.info('Connected to {0} as {1}'.format(self.server,self.username))

        self.client.RegisterHandler('presence', self.presence_handler)
        self.logger.info('Set presence handler')
        self.client.RegisterHandler('message', self.message_handler)
        self.logger.info('Set message handler')


    def listen(self):
        self.listening = True
        self.logger.info('Listening...')
        i=0
        while True:
            i+=1
            if self.client.isConnected():    #Check connection on each loop
                if self.listening:
                    if i % 6 == 0: self.logger.info('Still listening...')
                    try:
                        self.client.Process(10)
                    except KeyboardInterrupt:
                        self.logger.critical('INTERRUPT')
                        self.client.disconnect()
                        break
                else:
                    self.logger.info('Stopped listening')
                    break
            else:
                self.logger.warn('DISCONNECTED')
                break

    def accept_friend_request(self,jid):
        pres = xmpp.protocol.Presence(to=jid,typ='subscribed') #ex. jid = 'sum28373870@pvp.net'
        self.logger.debug("SEND: {0}".format(pres))
        self.client.send(pres)

    def send_friend_request(self,jid):
        r = self.client.getRoster()
        self.logger.debug("SUBSCRIBE: {0}".format(jid))
        r.Subscribe(jid)

    def message_handler(self, conn, msg):
        jid = str(msg.getFrom()).rstrip('/xiff')
        name = self.get_name(jid)
        status_msg = str(msg.getBody().encode('ascii', 'ignore'))

        self.logger.info("RECEIVED FROM: {0}>{1} | {2} ".format(name, jid ,status_msg))
        self.logger.debug("msg : {0}".format(msg))

        res = self.interpreter._interpret(status_msg,jid)
        self.logger.debug(res)
        for key in res.keys():
            if key == 'ERROR':
                self.logger.warning(res[key])
            elif key == 'REPLIES':
                for send_msg in res[key]:
                    send_name = self.get_name(send_msg['ID'])
                    self.logger.info("SENT: {0}>{1} : {2}".format(send_name, send_msg['ID'],send_msg['REPLY']))
                    reply = xmpp.protocol.Message(to=send_msg['ID'], frm=msg.getTo(), body=send_msg['REPLY'], typ="chat")
                    conn.send(reply)
            elif key == 'TIMED':
                for send_msg in res[key]:
                    reply = xmpp.protocol.Message(to=send_msg['ID'], frm=msg.getTo(), body=send_msg['REPLY'], typ="chat")
                    self.send_timed_message(reply, send_msg['TIME'])
            else:
                self.logger.critical("Unknown key from interpreter")

    def presence_handler(self, conn, pres):
        #self.logger.debug("PRESENCE UPDATE: {0}".format(pres))
        pres_type = str(pres.getType())
        jid = str(pres.getFrom()).rstrip('/xiff')

        name = self.get_name(jid)

        if pres_type == 'unsubscribe':
            self.logger.info("PRESENCE UPDATE: UNSUBSCRIBE: {0}>{1}".format(name,jid))
            conn.send(xmpp.Presence(to=pres.getFrom(), frm=pres.getTo(), typ='unsubscribe'))
        elif pres_type == 'subscribe':
            self.logger.info("Pending Invites")
            if self.auto_accept:
                self.accept_friend_request(jid)
                if not name:
                    sum_id = jid[3:jid.find('@')]
                    name = BotConnection.RiotAPI.get_summoner_by_id(sum_id)[sum_id]['name']
                    with open(Settings.JIDTONAME_PATH, "a") as myfile:
                        myfile.write('\n'+jid+'|'+name)
                self.logger.info("PRESENCE UPDATE: SUBSCRIBE: {0}>{1}".format(name,jid))
        elif pres_type == "unavailable":
            self.logger.info("PRESENCE UPDATE: {0}>{1} Unavailable".format(name,jid))
            try:
                del self.live_friends[jid]
            except KeyError:
                self.logger.warning("Attempted to remove non-live friend from live friends list")
        else:
            xml_status = pres.getStatus()
            if xml_status:
                xml_status = str(xml_status.encode('ascii', 'ignore'))
                self.logger.debug("STATUS: {0}".format(xml_status))
                xml_status = ET.fromstring(xml_status)
                #if self.live_friends[jid]['status'] is None: self.live_friends[jid]['status'] = xml_status

                if xml_status.findtext('statusMsg') != self.live_friends[jid]['status'].findtext('statusMsg'): #status changed
                    self.logger.info("PRESENCE UPDATE: {0}>{1} STATUS: {2}".format(name, jid, xml_status.findtext('statusMsg')))

                if xml_status.findtext('gameStatus') != self.live_friends[jid]['status'].findtext('gameStatus'): #game status changed
                    if xml_status.findtext('gameStatus') == 'inGame':
                        self.logger.info("PRESENCE UPDATE: {0}>{1} IN GAME: {2} PLAYING AS: {3}".format(name, jid, xml_status.findtext('gameQueueType'), xml_status.findtext('skinname')))
                    elif xml_status.findtext('gameStatus') == 'spectating':
                        self.logger.info("PRESENCE UPDATE: {0}>{1} SPECTATING: {2}".format(name, jid, xml_status.findtext('dropInSpectateGameId')))
                    else:
                        self.logger.info("PRESENCE UPDATE: {0}>{1} GAME STATUS: {2}".format(name, jid, xml_status.findtext('gameStatus')))

                self.live_friends[jid]['status'] = xml_status

            else:
                xml_status = str(xml_status)
                self.logger.debug("STATUS: {0}".format(xml_status))




    def send_message(self, msg, jid):
        pass

    def send_timed_message(self, reply, seconds): #REWRITE USING threading.Timer()
        """Queues message to be sent after certain time"""
        self.logger.info('SENDING MESSAGE IN {0}s: {1}'.format(seconds, reply.getBody()))
        def send(reply, seconds):
            start_time = time.time()
            while (1):
                if time.time()-start_time > seconds:
                    self.client.send(reply)
                    self.logger.info('SENT: {0}'.format(reply.getBody()))
                    break
                else:
                    time.sleep(1)
        t1 = threading.Thread(target=send,args=(reply,seconds))
        t1.start()

    def get_name(self, jid):
        """Attempts to get name associated with JID from memory if that fails it
        attempts to get from local database, else returns None"""

        try:
            name = self.live_friends[jid]['name']
        except KeyError:
            jid_to_name = BotConnection.load_text(Settings.JIDTONAME_PATH)
            try:
                name = jid_to_name[jid]
            except KeyError:
                name = None
            self.live_friends[jid] = {"name":name,"status":ET.fromstring('<body></body>')}

        return name

    def get_summoner_id(self, jid):
        """extracts Summoner ID from JID"""
        jid = str(jid)
        jid = jid[:jid.find('@')].lstrip('sum')
        return jid



class CommandInterpreter():

    def __init__(self, bot_connection):
        self.administrators = ['sum26202814@pvp.net']
        self._available_commands = [method for method in dir(self) if callable(getattr(self, method)) and method[0] != '_']
        self._admin_only = ['close','say','enable','disable','message']
        self._disabled = []
        self.bot_connection = bot_connection

    def _interpret(self, message, ID):
        self.bot_connection.logger.debug("_interpret message: {0}".format(message))
        self.bot_connection.logger.debug("_interpret ID: {0}".format(ID))
        args = [x.rstrip('\r\n') for x in message.split(" ")]
        command_name = args[0]
        method_args = args[1:]
        #ID = ID.rstrip('/xiff')

        if command_name[0:1] =='!':
            if command_name[1:] not in self._disabled:

                if command_name[1:] in self._available_commands:

                    if command_name[1:] in self._admin_only:
                        if ID in self.administrators:
                            command = getattr(self,command_name[1:])
                        else:
                            return {'ERROR':'Insufficient priveleges'}

                    else:
                        command = getattr(self,command_name[1:])

                else:
                    self.bot_connection.logger.info('Command not recognized')
                    return {"REPLIES":[{'ID':ID, 'REPLY':'Command not recognized'}]}

                return command(method_args,ID)

            else:
                self.bot_connection.logger.info('Command disabled')
                return {"REPLIES":[{'ID':ID,'REPLY':'Command disabled'}]}

        else:
            if self.bot_connection.bot:
                return {"REPLIES":[{'ID':ID,'REPLY':self.bot_connection.bot.respond(message,ID)}]}
            else:
                return {'ERROR':'No chatter bot connected'}

    def close(self,args, ID):
        """!close"""
        self.bot_connection.logger.info("Stopping")
        self.bot_connection.listening = False
        return {"REPLIES":[{'ID':ID,'REPLY':'Stopping'}]}

    def rank(self, args, ID):
        """!rank -region=[optional region][SummonerName]"""
        region = None
        if args[0][0] == '-':
            opt = args[0]
            del args[0]
            if opt[0:8] == '-region=':
                region = opt[8:]
                all_regions = [getattr(lol_api.Regions,attr) for attr in dir(lol_api.Regions) if '_' not in attr]
                if region not in all_regions:
                    return {"REPLIES":[{'ID':ID,'REPLY':'Unknown Region'}]}


        user = "".join(args)
        self.bot_connection.logger.info("GET RANK: {0}".format(user))
        if user:
            try:
                reply = " ".join(args) + " is:\n" + self.bot_connection.RiotAPI.get_stuff(user, region)
            except (ValueError, AttributeError):
                reply = 'User Not Found.'
            return {"REPLIES":[{'ID':ID,'REPLY':reply}]}
        else:
            return {"REPLIES":[{'ID':ID,'REPLY':'To look up summoner ranked stats use: !rank [SummonerName]'}]}

    def runes(self,args,ID):
        """!runes [SummonerName]"""
        def add(vec1,vec2):
            res = []
            for i in range(len(vec1)):
                res.append(vec1[i]+vec2[i])

            return res
        user = " ".join(args)
        name = "".join(args)
        self.bot_connection.logger.info("GET RUNES: {0}".format(user))
        if name:
            try:
                json_dict = self.bot_connection.RiotAPI.get_summoner_by_name(name)
                id = str(json_dict[name.lower()]['id'])
                runes = self.bot_connection.RiotAPI.get_summoner_runes(id)
                for page in runes[id]['pages']:
                    if page['current'] == True:
                        slots = page['slots'] #runeSlotId RuneId
                        self.bot_connection.logger.debug("RUNE PAGE: {0}".format(slots))
                        slot_type = {} #red,blue,yellow,quint
                        for r in slots:
                            try:
                                slot_type[lol_api.RUNES[r['runeId']]['description']]
                                slot_type[lol_api.RUNES[r['runeId']]['description']] = add(lol_api.RUNES[r['runeId']]['numbers'],slot_type[lol_api.RUNES[r['runeId']]['description']])
                            except KeyError:
                                slot_type[lol_api.RUNES[r['runeId']]['description']] = lol_api.RUNES[r['runeId']]['numbers']

                #create response
                reply = user + "\'s runes:"
                for rune in slot_type:
                    text = rune.format(*slot_type[rune])
                    reply = reply + '\n' + text

            except (ValueError, KeyError):
                reply = 'User Not Found.'
            return {"REPLIES":[{'ID':ID,'REPLY':reply}]}
        else:
            return {"REPLIES":[{'ID':ID,'REPLY':"To lookup current runes use: !runes [SummonerName]"}]}

    def timer(self, args, ID):
        """!timer [dragon|baron|blue|red]"""
        if args:
            name = " ".join(args).lower()
            timer = None
            if 'drag' in name or 'drake' in name:
                timer = 5*60
                name = 'Dragon'
            elif 'bar' in name:
                timer = 6*60
                name = 'Baron'
            elif 'red' in name:
                timer = 4*60
                name = 'Red Buff'
            elif 'blue' in name:
                timer = 4*60
                name = 'Blue Buff'
            else:
                name = ''

            if name:
                reply = {'REPLIES':[{'ID':ID,'REPLY':name + ' timer set.'}],
                        'TIMED':{'ID':ID,'REPLY':name + ' spawning in 1 minute.',"TIME":timer}}
            else:
                reply = {"REPLIES":[{'ID':ID,'REPLY':'Objective not recognized'}]}

            return reply
        else:
            return {"REPLIES":[{'ID':ID,'REPLY':"To set an objective timer use: !timer [dragon|baron|blue|red]"}]}

    def help(self, args, ID):
        """!help"""
        reply = 'Commands are:\n'
        for com in self._available_commands:
            if com not in self._admin_only:
                reply = reply + getattr(self,com).__doc__ + '\n'
        reply = reply + "Otherwise just talk to the bot, it's lonely"
        return {"REPLIES":[{'ID':ID,'REPLY':reply}]}

    def say(self,args,ID):
        """!say"""
        return {"REPLIES":[{'ID':ID,'REPLY':" ".join(args)}]}

    def disable(self, args, ID):
        """!disable [command]"""
        self.bot_connection.logger.info('Disabling: {0}'.format(args[0]))
        args[0] = args[0].lstrip('!')
        if args[0] not in self._disabled:
            self._disabled.append(args[0])
            return {"REPLIES":[{'ID':ID,'REPLY':'Command disabled'}]}


    def enable(self, args, ID):
        """!enable [command]"""
        self.bot_connection.logger.info('Enabling: {0}'.format(args[0]))
        args[0] = args[0].lstrip('!')
        if args[0] in self._disabled:
            self._disabled.remove(args[0])
            return {"REPLIES":[{'ID':ID,'REPLY':'Command enabled'}]}

    def message(self, args, ID):
        """!message [jid] [message]"""
        self.bot_connection.logger.info('Messaging: {0}'.format(args[0]))
        jid = args[0]
        msg = " ".join(args[1:])
        return {"REPLIES":[{'ID':ID,'REPLY':'Sent.'}, {'ID':jid,'REPLY':msg}]}


if __name__ == '__main__':
    logger = logging.getLogger(Settings.USER)
    logger.setLevel(logging.DEBUG)

    needRoll = False
    if os.path.isfile(Settings.LOG_FILENAME):
        needRoll = True

    handler = logging.handlers.RotatingFileHandler(Settings.LOG_FILENAME, backupCount=10)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if needRoll: logger.handlers[0].doRollover()

    l = BotConnection(username = Settings.USER, password = Settings.PASS,  server = Settings.DEFAULT_SERVER, logger = logger)
    #l.debug = 1
    l.connect()
    l.listen()
