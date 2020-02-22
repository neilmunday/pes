import datetime
import logging
import json
import multiprocessing
import os
import requests
import time

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread
from PyQt5.QtSql import QSqlDatabase, QSqlQuery

URL_TIMEOUT = 30
RETRO_URL = "https://www.retroachievements.org/dorequest.php"
RETRO_BADGE_URL = "http://i.retroachievements.org/Badge"

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def getGameHashes(consoleId):
	logging.debug("retroachievement.getGameHashes: consoleId = %d" % consoleId)
	response = requests.get(RETRO_URL, params={ "r": "hashlibrary", "c": consoleId }, timeout=URL_TIMEOUT)
	if not response.status_code == requests.codes.ok:
		logging.error("retroachievement.getGameHashes: could not download game hashes, response code - %s" % response.status_code)
		return None
	hashData = response.json()
	if not hashData['Success']:
		logging.error("retroachievement.getGameHashes: failed to download hashes")
		return None
	games = {}
	for hash, gameId in hashData['MD5List'].items():
		games[int(gameId)] = { 'hash': hash }
	response = requests.get(RETRO_URL, params={ "r": "gameslist", "c": consoleId }, timeout=URL_TIMEOUT)
	if not response.status_code == requests.codes.ok:
		logging.error("retroachievement.getGameHashes: could not download game list, response code - %s" % response.status_code)
		return None
	gameData = response.json()
	if not gameData['Success']:
		logging.error("retroachievement.getGameHashes: failed to download game list data")
		return None
	for gameId, title in gameData['Response'].items():
		gameId = int(gameId)
		if gameId in games.keys():
			games[gameId]['name'] = title.strip()
	return games

def getRetroAchievementId(rasum):
	try:
		response = requests.get(RETRO_URL, params={"r": "gameid", "m": rasum}, timeout=URL_TIMEOUT)
		if response.status_code != requests.codes.ok:
			return None
		data = response.json()
		if "Success" not in data:
			logging.error("retroachievement.getRetroAchievementId: could not find \"Success\" in JSON")
			return None
		if not data["Success"]:
			logging.error("retroachievement.getRetroAchievementId: could not get ID for hash \"%s\"" % rasum)
			return None
		return data["GameID"]
	except Exception as e:
		logging.error("retroachievement.getRetroAchievementId: could not get ID for hash \"%s\"" % rasum)
		logging.error(e)
	return None

class RetroAchievementException(Exception):

	def __init__(self, msg):
		Exception.__init__(self, msg)

class RetroAchievementUser(QObject):

	__URL = 'http://retroachievements.org/API/'

	loggedInSignal = pyqtSignal()

	def __init__(self, username=None, password=None, apikey=None):
		super(RetroAchievementUser, self).__init__()
		logging.debug("RetroAchievementUser.__init__: %s" % username)
		self.__username = username
		self.__password = password
		self.__apikey = apikey
		self.__token = None
		self.__score = 0
		self.__retroAchievementUserRecord = None
		self.__userId = -1
		self.__db = None

	def __doRequest(self, apiUrl, parameters=None):
		params = {'z' : self.__username, 'y': self.__apikey }
		if parameters:
			for k, v in parameters.items():
				params[k] = v
		url = "%s/%s" % (RetroAchievementUser.__URL, apiUrl)
		logging.debug('RetroachievementUser.__doRequest: loading URL %s with %s' % (url, params))
		response = requests.get(
			url,
			params=params,
			timeout=URL_TIMEOUT
		)
		if response.status_code == requests.codes.ok:
			if response.text == 'Invalid API Key':
				raise RetroAchievementException("Invalid RetroAchievement API key")
			return response.json()
		raise RetroAchievementException("Failed to load URL %s with %s" % (url, params))

	def getCredentials(self):
		return (self.__username, self.__password)

	def getGameInfoAndProgress(self, gameId):
		return self.getGameInfoAndUserProgress(self.__username, gameId)

	def getGameInfoAndUserProgress(self, user, gameId):
		logging.debug("RetroAchievementUser.getGameInfoAndUserProgress: user = %s, gameId = %d" % (user, gameId))
		return self.__doRequest('API_GetGameInfoAndUserProgress.php', {'u': user, 'g': gameId})

	def enableDbSync(self, db):
		self.__db = db

	def getId(self):
		if self.__userId == -1:
			self.login()
		return self.__userId

	def getUserSummary(self, user=None, recentGames=0):
		if user == None:
			user = self.__username
		logging.debug("RetroAchievementUser.getUserSummary: getting user %s and games %s" % (user, recentGames))
		return self.__doRequest('API_GetUserSummary.php', {'u': user, 'g': recentGames, 'a': 5})

	def hasEarnedBadge(self, badgeId):
		# has the user earned this badge?
		if self.__db == None:
			self.login()
		return self.__retroAchievementUserRecord.hasEarnedBadge(badgeId)

	def hasEarnedHardcoreBadge(self, badgeId):
		# has the user earned this hardcore badge?
		if self.__db == None:
			self.login()
		return self.__retroAchievementUserRecord.hasEarnedHardcoreBadge(badgeId)

	def isLoggedIn(self):
		return self.__token != None

	def login(self):
		try:
			response = requests.get(RETRO_URL, params={ "r": "login", "u": self.__username, "p": self.__password }, timeout=URL_TIMEOUT)
			if response.status_code == requests.codes.ok:
				data = response.json()
				if "Success" in data:
					if data["Success"]:
						if "Token" in data:
							self.__token = data["Token"]
							# score == total_points
							self.__score = int(data["Score"])
							logging.info("RetroAchievementUser.login: %s (%d)" % (self.__username, self.__score))
							logging.debug("RetroAchievementUser.login: token: %s" % self.__token)

							if self.__db:
								data = self.getUserSummary()
								self.__userId = int(data["ID"])
								#self.__retroAchievementUserRecord = pes.data.RetroAchievementUserRecord(self.__db, self.__userId)
								#self.__retroAchievementUserRecord.setName(self.__username)
								#self.__retroAchievementUserRecord.setRank(int(data["Rank"]))
								#self.__retroAchievementUserRecord.setTotalPoints(int(data["TotalPoints"]))
								#self.__retroAchievementUserRecord.setTotalTruePoints(int(data["TotalTruePoints"]))
								#self.__retroAchievementUserRecord.save()

							self.loggedInSignal.emit()
							return True
						else:
							logging.error("RetroAchievementUser.login: could not log in - token not in response")
					elif "Error" in data:
						logging.error("RetroAchievementUser.login: could not log in - %s" % data["Error"])
					else:
						logging.error("RetroAchievementUser.login: could not log in")
			else:
				logging.error("RetroAchievementUser.login: could not log in, response code - %s" % response.status_code)
		except Exception as e:
			logging.error("RetroAchievementUser.login: could not log in")
			logging.error(e)
		return False
