import logging
import json
import requests
import time

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread
from PyQt5.QtSql import QSqlDatabase, QSqlQuery

URL_TIMEOUT = 30
RETRO_URL = "http://retroachievements.org/dorequest.php"

logging.getLogger("requests").setLevel(logging.WARNING)

class BadgeScanThread(QThread):
	badgesFoundSignal = pyqtSignal(int)
	finishedSignal = pyqtSignal()

	def __init__(self, db):
		super(BadgeScanThread, self).__init__(None)
		self.__db = db
		self.__progress = 0
		self.__badgeTotal = 0
		self.__done = False
		self.__started = False
		self.__startTime = 0
		self.__endTime = 0
		self.__added = 0
		self.__updated = 0
		self.__tasks = None
		self.__exitEvent = None
		self.__gameTotal = 0

	def getProgress(self):
		if self.__done:
			return 100
		if self.__gameTotal == 0 or not self.__started or self.__tasks == None:
			return 0
		# subtract poison pills from queue size
		qsize = self.__tasks.qsize() - self.__badgeProcessTotal
		if qsize <= 0:
			return 100
		return int((float(self.__gameTotal - qsize) / float(self.__gameTotal)) * 100.0)

	def isFinished(self):
		return self.__done

	def run(self):
		logging.debug("BadgeScanThread.run: rom scan thread started")
		self.__startTime = time.time()
		self.__done = False
		self.__badgeTotal = 0
		self.__gameTotal = 0
		self.__endTime = time.time()
		self.__done = True
		lock = multiprocessing.Lock()
		self.__tasks = multiprocessing.JoinableQueue()
		self.__exitEvent = multiprocessing.Event()
		self.__badgeProcessTotal = multiprocessing.cpu_count() * 2
		logging.debug("BadgeScanThread.run: using %d processes" % self.__badgeProcessTotal)

		self.__done = True

	def stop(self):
		if self.__started and not self.__done:
			logging.debug("BadgeScanThread.stop: stopping processes...")
			self.__exitEvent.set()
		else:
			self.__done = True
			self.finishedSignal.emit()

class RetroAchievementException(Exception):

	def __init__(self, msg):
		Exception.__init__(self, msg)

class RetroAchievementUser(QObject):

	__URL = 'http://retroachievements.org/API/'

	loggedInSignal = pyqtSignal()

	def __init__(self, username, password, apikey):
		super(RetroAchievementUser, self).__init__()
		logging.debug("RetroAchievementUser.__init__: %s" % username)
		self.__username = username
		self.__password = password
		self.__apikey = apikey
		self.__token = None
		self.__score = 0

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

	def getGameInfoAndUserProgress(self, user, gameId):
		logging.debug("RetroAchievementUser.getGameInfoAndUserProgress: user = %s, gameId = %d" % (user, gameId))
		return self.__doRequest('API_GetGameInfoAndUserProgress.php', {'u': user, 'g': gameId})

	def getUserSummary(self, user=None, recentGames=0):
		if user == None:
			user = self.__username
		logging.debug("RetroAchievementUser.getUserSummary: getting user %s and games %s" % (user, recentGames))
		return self.__doRequest('API_GetUserSummary.php', {'u': user, 'g': recentGames, 'a': 5})

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
							self.__score = int(data["Score"])
							logging.info("RetroAchievementUser.login: %s (%d)" % (self.__username, self.__score))
							logging.debug("RetroAchievementUser.login: token: %s" % self.__token)
							self.loggedInSignal.emit()
							return True
						else:
							logging.error("RetroAchievementUser.login: could not log in - token not in response")
					elif "Error" in data:
						logging.error("RetroAchievementUser.login: could not log in - %s" % data["Error"])
					else:
						logging.error("RetroAchievementUser.login: could not log in")
						print(data)
			else:
				logging.error("RetroAchievementUser.login: could not log in, response code - %s" % response.status_code)
		except Exception as e:
			logging.error("RetroAchievementUser.login: could not log in")
			logging.error(e)
		return False

	@staticmethod
	def getRetroAchievementId(rasum):
		try:
			response = requests.get(RETRO_URL, params={"r": "gameid", "m": rasum}, timeout=URL_TIMEOUT)
			if response.status_code != requests.codes.ok:
				return None
			data = response.json()
			if "Success" not in data:
				logging.error("RetroAchievementUser.getRetroAchievementId: could not find \"Success\" in JSON")
				return None
			if not data["Success"]:
				logging.error("RetroAchievementUser.getRetroAchievementId: could not get ID for hash \"%s\"" % rasum)
				return None
			return data["GameID"]
		except Exception as e:
			logging.error("RetroAchievementUser.getRetroAchievementId: could not get ID for hash \"%s\"" % rasum)
			logging.error(e)
		return None
