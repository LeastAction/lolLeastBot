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
import threading
import os
import sys
import lol_api
import aiml
from chatterbotapi import ChatterBotFactory, ChatterBotType
from colorama import init, Fore
init()

JIDTONAME_PATH = os.path.join(os.getcwd(),'JIDtoName.txt')
PASS_PATH = os.path.join(os.getcwd(),'lol_pass.txt')

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

class RiotServers():
    BR = 'br'
    EUN = 'eun1'
    EUW = 'eu'
    NA = 'na1'
    KR = 'kr'
    OCE = 'oc1'
    RU = 'ru'
    TR = 'tr'

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

def load_text(path):
    text_file = open(path, "r")
    lines = text_file.read().split('\n')
    i=0
    for line in lines:
        lines[i] = line.split("|")
        i+=1
    return lines

class LeastBot():
    RiotAPI = lol_api.RiotAPI(verbosity=1)
    def __init__(self, username='LeastBot', password="AIR_" + open(PASS_PATH, "r").readline(), server = RiotServers.NA, port = 5223):
        self.username =  username
        self.password = password
        self.client = None
        self.server = 'chat.{0}.lol.riotgames.com'.format(server)
        self.port = port
        self.bot = ChatterBots()
        self.config = {'autoaccept':True,
                        'debug':[],
                        }
        self.listening = True

    def connect(self):
        self.client = xmpp.Client('pvp.net',debug=self.config['debug'])
        if self.client.connect(server=(self.server, self.port)) == "":
            print "connect failed."
            self.client = None
            return
        if self.client.auth(self.username, self.password, "xiff") == None:
            print "auth failed."
            self.client = None
            return
        if self.client.isConnected():
            self.client.sendInitPresence(requestRoster=1)
            pres = xmpp.Presence(show='chat')
            pres.setStatus(STATUS_MSG)
            self.client.send(pres)

        print 'Connected to {0} as {1}'.format(self.server,self.username)

        messageHandler = CheckMessages(self.client, self, self.config['autoaccept'])
        self.client.RegisterHandler('presence', messageHandler.presence_update)
        self.client.RegisterHandler('message', messageHandler.message_update)


    def listen(self):
        self.listening = True
        while True:
            if self.client.isConnected():    #Check connection on each loop
                if self.listening:
                    try:
                        self.client.Process(10)
                    except KeyboardInterrupt:
                        self.client.disconnect()
                        break
                else:
                    print 'Stopped listening'
                    break
            else:
                print 'DISCONNECTED'
                break

    def accept_friend_request(self,jid):
        pres = xmpp.protocol.Presence(to=jid,typ='subscribed') #ex. jid = 'sum28373870@pvp.net'
        self.client.send(pres)

    def send_friend_request(self,jid):
        r = self.client.getRoster()
        r.Subscribe(jid)

    def get_runes(self,user):

        def add(vec1,vec2):
            res = []
            for i in range(len(vec1)):
                res.append(vec1[i]+vec2[i])

            return res

        name = user.replace(" ","")
        print 'Get Runes: ' + name
        try:
            json_dict = self.RiotAPI.get_summoner_by_name(name)
            id = str(json_dict[name.lower()]['id'])
            runes = self.RiotAPI.get_summoner_runes(id)
            for page in runes[id]['pages']:
                if page['current'] == True:
                    slots = page['slots'] #runeSlotId RuneId
                    #have RUNES constnt in lol_api, compare runes to get descriptions, possibly multiply numbers beforehand to get a nice format to read
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

        except ValueError:
            reply = 'User Not Found.'
        return reply

    def get_rank(self,user):
        try:
            reply = user + " is:\n" + self.RiotAPI.get_stuff(user)
        except ValueError:
            reply = 'User Not Found.'
        return reply

class CheckMessages():
    """
    Constantly check for network data in a separate thread.
    """
    def __init__(self, conn, leastbot, autoaccept=False):
        self.conn = conn
        self.alive_users = []
        self.conversations = {}
        self.leastbot = leastbot
        self.configAutoAccept = self.leastbot.config['autoaccept']

    def get_name(self, msg_from):
        roster = self.conn.getRoster()
        received_from = None
##        for user in self.alive_users:
##            if str(user) == str(msg_from):
##                received_from = roster.getName(user)

        if not received_from:
            received_from = '#:#BLANK#:#'
            convert = load_text(JIDTONAME_PATH)
            for jid in convert:
##                print '*****************************************************'
##                print str(jid[0])
##                print str(msg_from)
                if str(jid[0]) == str(msg_from):
                    received_from = jid[1]
                    break

        return str(received_from)

    def presence_update(self, conn, msg):
        """
        Receive and process jabber presence updates.
        """
        print Fore.YELLOW
        if str(msg.getType()) not in ["unavailable",'subscribe','unsubscribe']:
            if str(msg.getFrom()) not in self.alive_users:
                self.alive_users.append(str(msg.getFrom()))
            received_from = self.get_name(msg.getFrom())
            if received_from != "None":
                status_msg = msg.getStatus()
                if status_msg:
                    status_msg = str(msg.getStatus().encode('ascii', 'ignore'))
                else:
                    status_msg = str(msg.getStatus())
                endpoint = status_msg.find("</statusMsg>")
                if endpoint != -1:
                    startpoint = status_msg.find("<statusMsg>") + 11
                    print "#:#statusupdate#:#%s:%s" % (received_from, status_msg[startpoint:endpoint])
                else:
                    print "#:#statusupdate#:#%s:%s" % (received_from, '')
                endpoint = status_msg.find("</gameStatus>")
                if endpoint != -1:
                    startpoint = status_msg.find("<gameStatus>") + 12
                    if status_msg[startpoint:endpoint] == 'inGame':
                        endpoint = status_msg.find("</skinname>")
                        if endpoint != -1:
                            startpoint = status_msg.find("<skinname>") + 10
                            champion_name = status_msg[startpoint:endpoint]
                        else:
                            champion_name = 'Unknown'
                        endpoint = status_msg.find("</timeStamp>")
                        if endpoint != -1:
                            startpoint = status_msg.find("<timeStamp>") + 11
                            timestamp = status_msg[startpoint:startpoint+10]
                        else:
                            timestamp = str(time.time())[:10]
                        print "#:#gameupdate#:#%s:%s" % (received_from, 'In Game as %s' % champion_name)
                        print "#:#gametimeupdate#:#%s:%s" % (received_from, timestamp)
                    elif status_msg[startpoint:endpoint] == 'inQueue':
                        print "#:#gameupdate#:#%s:%s" % (received_from, 'In Queue')
                    elif status_msg[startpoint:endpoint] == 'outOfGame':
                        print Fore.MAGENTA + "#:#gameupdate#:#%s:%s" % (received_from, 'Online')
                    elif status_msg[startpoint:endpoint] == 'hostingPracticeGame':
                        print "#:#gameupdate#:#%s:%s" % (received_from, 'Hosting a Practice Game')
                    elif status_msg[startpoint:endpoint] == 'championSelect':
                        print"#:#gameupdate#:#%s:%s" % (received_from, 'In Champion Select')
                    elif status_msg[startpoint:endpoint] == 'teamSelect':
                        print "#:#gameupdate#:#%s:%s" % (received_from, 'In Team Select')
                    elif status_msg[startpoint:endpoint] == 'spectating':
                        endpoint = status_msg.find("</dropInSpectateGameId>")
                        if endpoint != -1:
                            startpoint = status_msg.find("<dropInSpectateGameId>") + 22
                            if 'featured_game' in status_msg[startpoint:endpoint]:
                                game_name = 'Featured Game'
                            else:
                                game_name = status_msg[startpoint:endpoint]
                        else:
                            game_name = ''
                        print "#:#gameupdate#:#%s:%s" % (received_from, 'Spectating %s' % game_name)
                    else:
                        print "#:#gameupdate#:#%s:%s" % (received_from, status_msg[startpoint:endpoint])
        elif str(msg.getType()) == 'unsubscribe':
            self.conn.send(xmpp.Presence(to=msg.getFrom(), frm=msg.getTo(), typ='unsubscribe'))
        elif str(msg.getType()) == 'subscribe':
            print 'Pending Invites'

            if self.configAutoAccept:
                self.leastbot.accept_friend_request(str(msg.getFrom()))
                received_from = self.get_name(msg.getFrom())
                if received_from == '#:#BLANK#:#':
                    jid = str(msg.getFrom()) + '/xiff'
                    id = jid[3:jid.find('@')]
                    received_from = LeastBot.RiotAPI.get_summoner_by_id(id)[id]['name']
                    with open(JIDTONAME_PATH, "a") as myfile:
                        myfile.write('\n'+jid+'|'+received_from)
                print 'Subscribed to: ' + received_from

        elif str(msg.getType()) == "unavailable":
            received_from = self.get_name(msg.getFrom())
            print Fore.RED + "#:#removefriend#:#%s" % received_from
            self.alive_users.remove(str(msg.getFrom()))

    def message_update(self, conn, msg):
        """
        Receive and process jabber messages.
        """
        print Fore.GREEN
        received_from = self.get_name(msg.getFrom())
        status_msg = str(msg.getBody().encode('ascii', 'ignore'))
        #status_msg = str(msg.getBody())


        endpoint = status_msg.find("</gameType>")
        if ((endpoint != -1) and (status_msg.find('<inviteId>') != -1)):    #Redundant on the offchance someone uses one of these tags in a real message
            startpoint = status_msg.find("<gameType>") + 10
            print "#:#gameinvite#:#%s:%s" % (received_from, status_msg[startpoint:endpoint])
        else:
            print "#:#message#:#%s:%s: %s" % (str(msg.getFrom()),received_from, status_msg)

        if status_msg == '!help':
            reply = 'To lookup summoner info use: ![SummonerName]\nTo lookup current runes use: !runes [SummonerName]\nOtherwise just talk to the bot, it\'s lonely.'
        elif status_msg == '!CLOSE' and received_from == 'LeastAction':
            self.leastbot.listening = False
            reply = 'Stopping'
        elif status_msg[0:7] == '!runes ':
            name = status_msg.split(" ",1)[1]
            reply = self.leastbot.get_runes(name)
        elif status_msg[0] == '!':
            reply = self.leastbot.get_rank(status_msg[1:])
        else:
            reply = self.leastbot.bot.respond(status_msg,received_from)
            #reply = 'Echo mode on cause bot is an idiot: ' + status_msg

        print Fore.WHITE + '#:#SENT#:# ' + reply
        reply = msg.buildReply(reply)
        reply.setType("chat")
        conn.send(reply)

if __name__ == '__main__':
    l = LeastBot()
    l.connect()
    l.listen()