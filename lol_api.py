#coding: utf8
from __future__ import unicode_literals
from requests import get
import json
import re
import os
'''
RiotAPI.py isn’t endorsed by Riot Games and doesn’t reflect the views or opinions of Riot Games
or anyone officially involved in producing or managing League of Legends.
League of Legends and Riot Games are trademarks or registered trademarks of
Riot Games,Inc. League of Legends © Riot Games, Inc.
'''

class RiotAPI(object):
    default_region = 'na'
    default_api_url = 'http://prod.api.pvp.net/api/lol/{0}/{1}/'
    static_api_url = 'http://prod.api.pvp.net/api/lol/static-data/{0}/{1}/'

    api_version = {'champion':'v1.2',
                 'game':'v1.3',
                 'league':'v2.4',
                 'lol-static-data':'v1.2',
                 'stats':'v1.3',
                 'summoner':'v1.4',
                 'team':'v2.3'
                 }

    def __init__(self, key=None):
        self.key = open(os.path.join(os.getcwd(),'api_key.txt'), "r").readline()

    def _get(self, url, region=default_region, payload={},category=''):
        payload['api_key'] = self.key

        if not category:
            category = url.split('/')[0]

        api_url = self.default_api_url
        if category == 'lol-static-data': api_url = self.static_api_url

        uri = api_url.format(region.lower(),self.api_version[category]) + url
        #a = get(uri, params=payload).json()
        a = get(uri, params=payload).json()
        return a

    ##More complex##

    def get_stuff(self, name, region=default_region):
        name = name.replace(" ","")
        json_dict = self.get_summoner_by_name(name,region)
        level = str(json_dict[name.lower()]['summonerLevel'])
        id = str(json_dict[name.lower()]['id'])
        try:
            json_dict = self.get_league_entry(id,region)
        except ValueError:
            return 'Level: ' + level + '\nNo Ranked Data'
        leagues = json_dict[id]
        rank = None
        for league in leagues:
            if league['queue'] == 'RANKED_SOLO_5x5':
                leaguePoints = league['entries'][0]['leaguePoints']
                tier = league['tier']
                division = league['entries'][0]['division']
                rank = tier + ' ' + division + ' ' + str(leaguePoints) + ' lp'

        if not rank:
            rank = 'UNRANKED'

        reply = rank + '\n' + 'Level: ' + level


        json_dict = self.get_stats_ranked(id)
        maxPlayed = 0
        topChampion = None
        won = None
        lost = None
        for champion in json_dict['champions']:
            played = champion['stats']['totalSessionsPlayed']
            if played > maxPlayed:
                if champion['id'] == 0:
                    won = champion['stats']['totalSessionsWon']
                    lost = champion['stats']['totalSessionsLost']
                else:
                    topChampion = CHAMP_ID[champion['id']]
                    maxPlayed = played

        if won and lost:
            reply = reply + '\nWin/Loss: ' + str(won) + '/' + str(lost) + ' : ' + str(round(100*won/float(lost+won),2)) + '%'

        if topChampion:
            reply = reply + '\nMost Played Champ: ' + topChampion + ' ' + str(maxPlayed) + ' games'

        return reply

    def get_solo_rank_by_name(self, name, region=default_region):
        name = name.replace(" ","")
        json_dict = self.get_summoner_by_name(name,region)
        id = str(json_dict[name.lower()]['id'])
        json_dict = self.get_league_entry(id,region)
        leagues = json_dict[id]
        rank = None
        for league in leagues:
            if league['queue'] == 'RANKED_SOLO_5x5':
                leaguePoints = league['entries'][0]['leaguePoints']
                tier = league['tier']
                division = league['entries'][0]['division']
                rank = tier + ' ' + division + ' ' + str(leaguePoints) + ' lp'

        if not rank:
            return 'UNRANKED'

        return rank

    ##CHAMPION##
    def get_champions(self, free_to_play=None):
        return self._get('champion', payload={'freeToPlay': free_to_play})

    ###GAME###
    def get_recent_games(self, summoner_id, region=default_region):
        return self._get('game/by-summoner/%s/recent' % summoner_id, region=region)

    ###LEAGUE###
    def get_league(self, summoner_id, region=default_region):
        return self._get('league/by-summoner/%s' % summoner_id, region=region)

    def get_league_entry(self, summoner_id, region=default_region):
        return self._get('league/by-summoner/%s/entry' % summoner_id, region=region)

    ###STATS###
    def get_stats_summary(self, summoner_id, region=default_region, season=None):
        return self._get('stats/by-summoner/%s/summary' % summoner_id, region=region, payload={'season': season})

    def get_stats_ranked(self, summoner_id, region=default_region, season=None):
        return self._get('stats/by-summoner/%s/ranked' % summoner_id, region=region, payload={'season': season})

    ##SUMMONER##
    def get_summoner_by_name(self, name, region=default_region):
        #TODO: fix non ascii names
        return self._get('summoner/by-name/%s' % name.replace(' ', ''), region=region)

    def get_summoner_by_id(self, summoner_id, region=default_region):
        return self._get('summoner/%s' % summoner_id, region=region)

    def get_summoner_masteries(self, summoner_id, region=default_region):
        return self._get('summoner/%s/masteries' % summoner_id, region=region)

    def get_summoner_runes(self, summoner_id, region=default_region):
        return self._get('summoner/%s/runes' % summoner_id, region=region)

    def get_summoner_name(self, summoner_id, region=default_region):
        return self._get('summoner/%s/name' % summoner_id, region=region)

    ##TEAMS##
    def get_teams_by_summoner(self, summoner_id, region=default_region):
        return self._get('team/by-summoner/%s' % summoner_id, region=region)

    ##STATIC##
    def get_static_data_rune(self, region=default_region):
        return self._get('rune', region=region, category='lol-static-data')

    def get_static_data_champion(self, region=default_region):
        return self._get('champion', region=region, category='lol-static-data')


def repl(matchobj):
    return matchobj.group(0)[0] + '{}'

#useful 'constants'
r=RiotAPI()
a = r.get_static_data_rune()['data']
RUNES = {}

##for rune in a.keys():
##    RUNES[a[rune]['id']] = {'description': a[rune]['description'], 'name':a[rune]['name']}

for rune in a.keys():
    text = a[rune]['description']
    RUNES[int(rune)] = {'description':re.sub(r'[+-][\d.]+', repl,text),
                    'numbers' : map(abs,map(float,re.findall(r'[+-][\d.]+', text))),
                    'name': a[rune]['name']}
##    if (RUNES[rune]['description'].format(*RUNES[rune]['numbers']) != a[rune]['description']):
##        print RUNES[rune]['description'].format(*RUNES[rune]['numbers'])
##        print a[rune]['description']
##        print '-------'

a = r.get_static_data_champion()['data']
CHAMP_ID = {}
for champ in a.keys():
    CHAMP_ID[a[champ]['id']] = a[champ]['name']
