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

#
#JIDTONAME FILE auto add!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
import xmpp
import threading
import os
import sys
import lol_api
import aiml

BOT = aiml.Kernel()

#ALICE
##base_path = "D:\\Dropbox\\Coding\\Python Codes\\General\\AIML REPO\\Social-Robot"
##r = os.listdir(base_path)
##r = [base_path + '\\' + a for a in r if '.aiml' in a]
##for path in r:
##    BOT.learn(path)

#STANDARD
#BOT.loadBrain("standard.brn")

##os.chdir("D:\Dropbox\Coding\Python Codes\General\AIML REPO")
##BOT.learn("std-startup.xml")
##BOT.respond("load aiml b")
####BOT.learn("blackjack.aiml")
##BOT.learn("bornin.aiml")
##BOT.learn("jokes.aiml")
####BOT.learn("howmany.aiml")
##BOT.learn("maths.aiml")



BOT.setBotPredicate("name","LeastBot")
BOT.setBotPredicate("master","LeastAction")

##BOT.saveBrain("standard.brn")

api_queue = 0
RiotAPI = lol_api.RiotAPI()
JIDTONAME_PATH = os.path.join(os.getcwd(),'JIDtoName.txt')

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

CONN_ERROR = 'error'
roster = None
api_queue = 0



def apiqueuetimer(): #function for resetting the queue every 10 seconds
    global api_queue
    #print 'api queue reset'
    if api_queue != 0:
        print 'API QUEUE: ' + str(api_queue)
    api_queue = 0
    threading.Timer(10,apiqueuetimer).start()

def load_text(path):
    text_file = open(path, "r")
    lines = text_file.read().split('\n')
    i=0
    for line in lines:
        lines[i] = line.split("|")
        i+=1
    return lines

def connect():
    global roster
    apiqueuetimer()
    username = 'LeastBot'
    passwd = "AIR_" + open(os.path.join(os.getcwd(),'lol_pass.txt'), "r").readline()
    client = xmpp.Client('pvp.net',debug=[])
    if client.connect(server=('chat.na1.lol.riotgames.com', 5223)) == "":
        print "connect failed."
        return
    if client.auth(username, passwd, "xiff") == None:
        print "auth failed."
        return
    if client.isConnected():
        client.sendInitPresence(requestRoster=1)
        pres = xmpp.Presence(show='chat')
        pres.setStatus(STATUS_MSG)
        client.send(pres)


        incoming_thread = CheckMessages(client)
##        incoming_thread.setDaemon(True)
##        incoming_thread.start()

        client.RegisterHandler('presence', incoming_thread.presence_update)
        client.RegisterHandler('message', incoming_thread.message_update)
        roster = client.getRoster()
        print "--------------------------------------------------------------------------------------------------"

        while True:
            if client.isConnected():    #Check connection on each loop
                try:
                    client.Process(10)
                except KeyboardInterrupt:
                    client.disconnect()
                    break
            else:
                print 'DISCONNECTED'
                break

def send_friend_request(jid, client):
    pres = xmpp.protocol.Presence(to=jid,typ='subscribed') #ex. jid = 'sum28373870@pvp.net'
    client.send(pres)
##    r = client.getRoster()
##    r.Subscribe('sum28373870@pvp.net')

def get_runes(user):

    def add(vec1,vec2):
        res = []
        for i in range(len(vec1)):
            res.append(vec1[i]+vec2[i])

        return res

    global api_queue
    name = user.replace(" ","")
    print 'Get Runes: ' + name
    try:
        while (1):
            if api_queue <= 7:
                json_dict = RiotAPI.get_summoner_by_name(name)
                id = str(json_dict[name.lower()]['id'])
                runes = RiotAPI.get_summoner_runes(id)
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
                api_queue += 2
                break
    except ValueError:
        reply = 'User Not Found.'
    return reply


def get_rank(user):
    global api_queue
    try:
        while (1):
            if api_queue <= 7:
                reply = user + " is:\n" + RiotAPI.get_stuff(user)
                api_queue += 3
                break
    except ValueError:
        reply = 'User Not Found.'
    return reply

class CheckMessages(threading.Thread):
    """
    Constantly check for network data in a separate thread.
    """
    def __init__(self, conn):
        threading.Thread.__init__(self)
        self.conn = conn
        self.user_length = 0
        self.alive_users = []
        self.conversations = {}
        self.first_run = True
        self.configAutoAccept = True

    def get_name(self, msg_from):
        roster = self.conn.getRoster()
        received_from = None
        for user in self.alive_users:
            if str(user) == str(msg_from):
                received_from = roster.getName(user)

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
                        print "#:#gameupdate#:#%s:%s" % (received_from, 'Online')
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
                send_friend_request(str(msg.getFrom()), self.conn)
                received_from = self.get_name(msg.getFrom())
                if received_from == '#:#BLANK#:#':
                    jid = str(msg.getFrom()) + '/xiff'
                    id = jid[3:jid.find('@')]
                    received_from = RiotAPI.get_summoner_by_id(id)[id]['name']
                print 'Subscribed to: ' + received_from




        elif str(msg.getType()) == "unavailable":
            received_from = self.get_name(msg.getFrom())
            print "#:#removefriend#:#%s" % received_from
            self.alive_users.remove(str(msg.getFrom()))

    def message_update(self, conn, msg):
        """
        Receive and process jabber messages.
        """
        received_from = self.get_name(msg.getFrom())
        status_msg = str(msg.getBody())


        endpoint = status_msg.find("</gameType>")
        if ((endpoint != -1) and (status_msg.find('<inviteId>') != -1)):    #Redundant on the offchance someone uses one of these tags in a real message
            startpoint = status_msg.find("<gameType>") + 10
            print "#:#gameinvite#:#%s:%s" % (received_from, status_msg[startpoint:endpoint])
        else:
            print "#:#message#:#%s:%s: %s" % (str(msg.getFrom()),received_from, str(msg.getBody()))

        if status_msg == '!help':
            reply = 'To lookup summoner info use: ![SummonerName]\nTo lookup current runes use: !runes [SummonerName]\nOtherwise just talk to the bot, it\'s lonely.'
        elif status_msg[0:7] == '!runes ':
            name = status_msg.split(" ",1)[1]
            reply = get_runes(name)
        elif status_msg[0] == '!':
            reply = get_rank(status_msg[1:])
        else:
            #reply = BOT.respond(status_msg,received_from)
            reply = 'Echo mode on cause bot is an idiot: ' + status_msg

        print '#:#SENT#:# ' + reply
        reply = msg.buildReply(reply)
        reply.setType("chat")
        conn.send(reply)

    def step_on(self):
        """
        Keep the connection alive and process network data on an interval.
        """

        if self.conn.isConnected():
            try:
                self.conn.Process(1)
                roster = self.conn.getRoster()

                if self.user_length != len(self.alive_users):
                    print "#:#clearfriends#:#"
                    for user in self.alive_users:
                        if roster.getName(user) != None:
                            print "#:#friendupdate#:#%s" % roster.getName(user)
                    for user in roster.getItems():
                        if ((roster.getName(user) != None) and ((str(user)+'/xiff') not in self.alive_users)):
                            print "#:#friendupdateoff#:#%s" % roster.getName(user)
                self.user_length = len(self.alive_users)
            except:
                print CONN_ERROR
                return 0
        else:
            print CONN_ERROR
            return 0
        return 1

    def run(self):
        """
        Maintain iteration while the connection exists.
        """

        while self.step_on():
            pass

connect()