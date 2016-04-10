#!/usr/bin/env python2

import json
import urllib
import urllib2
import logging

class RetroAchievement(object):
	
	URL = 'http://retroachievements.org/API/'
	URL_TIMEOUT = 10
	
	def __init__(self, user, apiKey):
		self.__user = user
		self.__apiKey = apiKey
		logging.debug("RetroAchievement.init: initialised")
		
	def __doRequest(self, apiUrl, params=None):
		obj = {'z' : self.__user, 'y': self.__apiKey }
		if params:
			for k, v in params.iteritems():
				obj[k] = v
		request = urllib2.Request("%s%s" % (RetroAchievement.URL, apiUrl), urllib.urlencode(obj))
		fullUrl = '%s?%s' % (request.get_full_url(), request.get_data())
		logging.debug("RetroAchievement.__doRequest: performing request for %s" % fullUrl)
		response = urllib2.urlopen(fullUrl)
		contents = response.read()
		if contents == "Invalid API Key":
			raise RetroAchievementException("Invalid API Key")
		s = json.loads(contents)
		return s
		
	def getConsoleIds(self):
		logging.debug("RetroAchievement.getConsoleIds: getting console IDs...")
		return self.__doRequest('API_GetConsoleIDs.php')
	
	def getGameInfo(self, gameId):
		logging.debug("RetroAchievement.getGameInfo: gameId = %d" % gameId)
		return self.__doRequest('API_GetGame.php', {'i': gameId})
	
	def getGameInfoAndUserProgress(self, user, gameId):
		logging.debug("RetroAchievement.getGameInfoAndUserProgress: user = %s, gameId = %d" % (user, gameId))
		return self.__doRequest('API_GetGameInfoAndUserProgress.php', {'u': user, 'g': gameId})
	
	def getGameList(self, consoleId):
		logging.debug("RetroAchievement.getGameList: console = %d" % consoleId)
		return self.__doRequest('API_GetGameList.php', {'i': consoleId})
	
	def getFeedFor(self, user, count, offset=0):
		logging.debug("RetroAchievement.getFeedFor: user = %s, count = %d, offset = %d" % (user, count, offset))
		return self.__doRequest('API_GetFeed.php', {'u': user, 'c': count, 'o': offset })

	def getUserProgress(self, user, gameIds):
		gameCsv = ','.join(str(x) for x in gameIds)
		logging.debug("RetroAchievement.getUserProgress: user = %s, gameIds = %s" (user, gameCsv))
		return self.__doRequest('API_GetUserProgress.php', {'u': user, 'i': gameCsv})
	
	def getUsername(self):
		return self.__user
	
	def getUserAllGames(self, user):
		logging.debug("RetroAchievement.getAllGames: getting all games for %s" % user)
		offset=0
		count=10
		result = []
		while True:
			output = self.getUserRecentlyPlayedGames(user, count, offset)
			for o in output:
				result.append(o)
			if len(output) < count:
				break
			offset += count
		return output
	
	def getUserRecentlyPlayedGames(self, user, count, offset=0):
		logging.debug("RetroAchievement.getRecentlyPlayedGames: user = %s, count = %d, offset = %d" % (user, count, offset))
		return self.__doRequest('API_GetUserRecentlyPlayedGames.php', {'u': user, 'c': count, 'o': offset })
	
	def getUserSummary(self, user, recentGames):
		logging.debug("RetroAchievement.getUserSummary: getting user %s and games %s" % (user, recentGames))
		return self.__doRequest('API_GetUserSummary.php', {'u': user, 'g': recentGames, 'a': 5})
	
class RetroAchievementException(Exception):
	
	def __init__(self, msg):
		Exception.__init__(self, msg)
