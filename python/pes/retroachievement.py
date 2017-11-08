#import urllib
import logging
import json
import requests

from PyQt5.QtCore import pyqtSignal, QObject

URL_TIMEOUT = 30
RETRO_URL = "http://retroachievements.org/dorequest.php"

logging.getLogger("requests").setLevel(logging.WARNING)

class RetroAchievementUser(QObject):

	loggedInSignal = pyqtSignal()

	def __init__(self, username, password, apikey):
		super(RetroAchievementUser, self).__init__()
		logging.debug("RetroAchievementUser.__init__: %s" % username)
		self.__username = username
		self.__password = password
		self.__apikey = apikey
		self.__token = None
		self.__score = 0

	def getCredentials(self):
		return (self.__username, self.__password)

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
