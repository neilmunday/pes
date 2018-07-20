import datetime
import logging
import json
import multiprocessing
import os
import requests
import time

import pes.data

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread
from PyQt5.QtSql import QSqlDatabase, QSqlQuery

URL_TIMEOUT = 30
RETRO_URL = "http://retroachievements.org/dorequest.php"
RETRO_BADGE_URL = "http://i.retroachievements.org/Badge"

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class BadgeScanWorkerThread(QThread):

	__INSERT_CACHE = 100

	badgeProcessedSignal = pyqtSignal(str, str) # name, path
	romProcessedSignal = pyqtSignal()

	def __init__(self, i, db, retroUser, queue, badgeDir):
		super(BadgeScanWorkerThread, self).__init__(None)
		self.__id = i
		self.__db = db
		self.__retroUser = retroUser
		self.__queue = queue
		self.__badgeDir = badgeDir
		self.__added = 0
		self.__updated = 0
		self.__earned = 0
		self.__stop = False
		logging.debug("BadgeScanWorkerThread.__init__: created with id %d" % self.__id)

	def __downloadBadge(self, url, path):
		logging.debug("BadgeScanWorkerThread(%d).__downloadBadge: downloading %s to %s" % (self.__id, url, path))
		try:
			response = requests.get(
				url,
				timeout=URL_TIMEOUT,
				stream=True
			)
			if response.status_code == requests.codes.ok:
				with open(path, 'wb') as f:
					for chunk in response.iter_content(chunk_size=128):
						f.write(chunk)
		except Exception as e:
			logging.error("BadgeScanWorkerThread(%d).__downloadBadge: failed to download %s to %s" % (url, path))
			logging.error(e)

	def getAdded(self):
		return self.__added

	def getEarned(self):
		return self.__earned

	def getId(self):
		return self.__id

	def getUpdated(self):
		return self.__updated

	def run(self):
		logging.debug("BadgeScanWorkerThread(%d).run: run started" % self.__id)
		self.__stop = False
		batchEarnedInsertQuery = pes.data.BatchInsertQuery(self.__db, "retroachievement_earned", ["user_id", "badge_id", "date_earned", "date_earned_hardcore"])
		batchUpdateQuery = pes.data.BatchQuery(self.__db)
		batchBadgeInsertQuery = pes.data.BatchInsertQuery(self.__db)
		userId = self.__retroUser.getId()

		while not self.__queue.empty():
			retroGameId = self.__queue.get()
			if self.__stop:
				break
			logging.debug("BadgeScanWorkerThread(%d).run: processing retro game id %d" % (self.__id, retroGameId))

			try:
				result = self.__retroUser.getGameInfoAndProgress(retroGameId)
			except Exception as e:
				logging.error("BadgeScanWorkerThread(%d).run: could not get game data for %d" % (self.__id, retroGameId))
				logging.error(e)
				self.__queue.task_done()
				continue

			achievementTotal = 0
			scoreTotal = 0

			badgeRomDir = os.path.join(self.__badgeDir, str(retroGameId))
			if not os.path.exists(badgeRomDir):
				logging.debug("BadgeScanWorkerThread(%d).run: creating %s" % (self.__id, badgeRomDir))
				os.mkdir(badgeRomDir)

			if "Achievements" in result and result["Achievements"] != None:

				for a in result["Achievements"]:
					achievement = result["Achievements"][a]
					achievementTotal += 1
					points = int(achievement["Points"])
					scoreTotal += points

					badgeId = int(achievement["ID"])
					badgePath = os.path.join(badgeRomDir, "%s.png" % badgeId)
					badgeLockedPath = os.path.join(badgeRomDir, "%s_locked.png" % badgeId)
					# does this badge exist in the db?
					badge = pes.data.RetroAchievementBadgeRecord(self.__db, badgeId)
					badge.setGameId(retroGameId)
					badge.setTitle(achievement["Title"])
					badge.setDescription(achievement["Description"])
					badge.setPoints(achievement["Points"])
					badge.setPath(badgePath)
					badge.setLockedPath(badgeLockedPath)

					if not os.path.exists(badgePath):
						self.__downloadBadge("%s/%s.png" % (RETRO_BADGE_URL, achievement["BadgeName"]), badgePath)
					if not os.path.exists(badgeLockedPath):
						self.__downloadBadge("%s/%s_lock.png" % (RETRO_BADGE_URL, achievement["BadgeName"]), badgeLockedPath)

					self.badgeProcessedSignal.emit(achievement["BadgeName"], badgePath)

					if badge.isNew():
						batchBadgeInsertQuery.addRecord(badge)
						self.__added += 1
					else:
						if badge.save():
							self.__updated += 1

					# has the user earned this achievement?
					if 'DateEarned' in achievement or 'DateEarnedHardcore' in achievement:
						earnedTs = 0
						earnedHardcoreTs = 0
						if 'DateEarned' in achievement:
							earnedTs = time.mktime(datetime.datetime.strptime(achievement['DateEarned'], '%Y-%m-%d %H:%M:%S').timetuple())
						if 'DateEarnedHardcore' in achievement:
							earnedHardcoreTs = time.mktime(datetime.datetime.strptime(achievement['DateEarnedHardcore'], '%Y-%m-%d %H:%M:%S').timetuple())
						query = pes.data.doQuery(self.__db, "SELECT `date_earned`, `date_earned_hardcore` FROM `retroachievement_earned` WHERE `user_id` = :user_id AND `badge_id` = :badge_id;", {"user_id": userId, "badge_id": badgeId})
						query.first()
						if query.first():
							dbEarnedTs = int(query.value(0))
							dbEarnedHardcoreTs = int(query.value(1))
							if dbEarnedTs != earnedTs and dbEarnedHardcoreTs != earnedHardcoreTs:
								query = "UPDATE `retroachievement_earned` SET "
								if dbEarnedTs != earnedTs:
									query += " `date_earned` = %d " % earnedTs
								if dbEarnedHardcoreTs != earnedHardcoreTs:
									query += " `date_earned_hardcore` = %d " % earnedHardcoreTs
								query += " WHERE `user_id` = %d AND `badge_id` = %d" % (userId, badgeId)
								batchUpdateQuery.addQuery(query)
								self.__earned += 1
						else:
							# new entry
							batchEarnedInsertQuery.add({"user_id": userId, "badge_id": badgeId, "date_earned": earnedTs, "date_earned_hardcore": earnedHardcoreTs})
							self.__earned += 1

				retroGame = pes.data.RetroAchievementGameRecord(self.__db, retroGameId)
				retroGame.setAchievementTotal(achievementTotal)
				retroGame.setScoreTotal(scoreTotal)
				retroGame.save()

			self.__queue.task_done()
			self.romProcessedSignal.emit()

		batchBadgeInsertQuery.finish()
		batchEarnedInsertQuery.finish()
		batchUpdateQuery.finish()

		logging.debug("BadgeScanWorkerThread(%d).run: finished" % self.__id)

	def stop(self):
		logging.info("BadgeScanThread(%d).stop: stoppping..." % self.__id)
		self.__stop = True

#class BadgeScanThread(QThread):
#
#	badgesFoundSignal = pyqtSignal(int)
#	finishedSignal = pyqtSignal()
#	__threadTotal = 4
#
#	def __init__(self, db, retroUser):
#		super(BadgeScanThread, self).__init__(None)
#		self.__db = db
#		self.__retroUser = retroUser
#		self.__progress = 0
#		self.__badgeTotal = 0
#		self.__done = False
#		self.__started = False
#		self.__startTime = 0
#		self.__endTime = 0
#		self.__added = 0
#		self.__updated = 0
#		self.__badgeList = None
#
#	def getAdded(self):
#		return self.__added
#
#	def getBadgeTotal(self):
# 		return self.__badgeTotal
#
#	def getProcessed(self):
#		return 0
#
#	def getProgress(self):
#		return 0
#
#	def getTimeRemaining(self):
#		return 1
#
#	def getUpdated(self):
# 		return self.__updated
#
#	def getTimeTaken(self):
# 		return self.__endTime - self.__startTime
#
#	def isFinished(self):
# 		return self.__done
#
#	def getLastBadge(self):
#		if self.__badgeList == None or len(self.__badgeList) == 0:
#			return None
#		return self.__badgeList[-1]
#
#	def run(self):
#		logging.debug("BadgeScanThread.run: started")
#		self.__startTime = time.time()
#		self.__done = False
#		self.__badgeTotal = 0
#		self.__gameTotal = 0
#
#		threads = []
#
#		for i in range(0, BadgeScanThread.__threadTotal):
#			t = BadgeScanWorkerThread(i, self.__retroUser)
#			threads.append(t)
#			t.start()
#
#		for t in threads:
#			t.wait()
#
#		self.__endTime = time.time()
#		self.__done = True
#		self.__started = False
#		self.finishedSignal.emit()
#		logging.debug("BadgeScanThread.run: finished")
#
#	def stop(self):
# 		self.__done = True
# 		self.finishedSignal.emit()

# class BadgeScanThread(QThread):
# 	badgesFoundSignal = pyqtSignal(int)
# 	finishedSignal = pyqtSignal()
#
# 	def __init__(self, db):
# 		super(BadgeScanThread, self).__init__(None)
# 		self.__db = db
# 		self.__progress = 0
# 		self.__badgeTotal = 0
# 		self.__done = False
# 		self.__started = False
# 		self.__startTime = 0
# 		self.__endTime = 0
# 		self.__added = 0
# 		self.__updated = 0
# 		self.__tasks = None
# 		self.__exitEvent = None
# 		self.__gameTotal = 0
# 		self.__badgeList = None
#
# 	def getAdded(self):
# 		return self.__added
#
# 	def getBadgeTotal(self):
# 		return self.__badgeTotal
#
# 	def getLastBadge(self):
# 		if self.__badgeList == None or not self.__started or (self.__exitEvent != None and self.__exitEvent.is_set()) or len(self.__badgeList) == 0:
# 			return None
# 		return self.__badgeList[-1]
#
# 	def getProcessed(self):
# 		if not self.__started or not self.__queueSetUp:
# 			return 0
# 		if self.__done:
# 			return self.__gameTotal
# 		return self.__gameTotal - self.__tasks.qsize()
#
# 	def getProgress(self):
# 		if self.__done:
# 			return 100
# 		if self.__gameTotal == 0 or not self.__started or self.__tasks == None:
# 			return 0
# 		# subtract poison pills from queue size
# 		qsize = self.__tasks.qsize() - self.__badgeProcessTotal
# 		if qsize <= 0:
# 			return 100
# 		return int((float(self.__gameTotal - qsize) / float(self.__gameTotal)) * 100.0)
#
# 	def getTimeRemaining(self):
# 		processed = self.getProcessed()
# 		if processed == 0 or not self.__started or self.__done or self.__tasks.qsize() == 0:
# 			return 0
# 		# now work out average time taken per game
# 		return ((time.time() - self.__startTime) / processed) * self.__tasks.qsize()
#
# 	def getUpdated(self):
# 		return self.__updated
#
# 	def getTimeTaken(self):
# 		return self.__endTime - self.__startTime
#
# 	def isFinished(self):
# 		return self.__done
#
# 	def run(self):
# 		logging.debug("BadgeScanThread.run: scan thread started")
# 		self.__startTime = time.time()
# 		self.__done = False
# 		self.__badgeTotal = 0
# 		self.__gameTotal = 0
# 		self.__endTime = time.time()
# 		lock = multiprocessing.Lock()
# 		results = multiprocessing.Queue()
# 		self.__tasks = multiprocessing.JoinableQueue()
# 		self.__exitEvent = multiprocessing.Event()
# 		self.__badgeProcessTotal = multiprocessing.cpu_count() * 2
# 		logging.debug("BadgeScanThread.run: using %d processes" % self.__badgeProcessTotal)
#
# 		badgeProcesses = [BadgeProcess(i, self.__tasks, results, self.__exitEvent, lock) for i in range(self.__badgeProcessTotal)]
#
# 		for i in range(self.__badgeProcessTotal):
# 			self.__tasks.put(None)
# 		logging.debug("BadgeScanThread.run: poison pills added to process queue")
#
# 		for p in badgeProcesses:
# 			p.start()
# 		for p in badgeProcesses:
# 			p.join()
# 		logging.debug("BadgeScanThread.run: badge processes joined main thread")
# 		self.__tasks.join()
# 		logging.debug("BadgeScanThread.run: ROM tasks joined main thread")
# 		while not results.empty():
# 			results.get()
# 		logging.debug("BadgeScanThread.run: result queue processed")
#
# 		self.__endTime = time.time()
# 		self.__done = True
# 		self.__started = False
# 		self.finishedSignal.emit()
#
# 		logging.debug("BadgeScanThread.run: finished")
#
# 	def stop(self):
# 		if self.__started and not self.__done:
# 			logging.debug("BadgeScanThread.stop: stopping processes...")
# 			self.__exitEvent.set()
# 		else:
# 			self.__done = True
# 			self.finishedSignal.emit()

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
								self.__retroAchievementUserRecord = pes.data.RetroAchievementUserRecord(self.__db, self.__userId)
								self.__retroAchievementUserRecord.setName(self.__username)
								self.__retroAchievementUserRecord.setRank(int(data["Rank"]))
								self.__retroAchievementUserRecord.setTotalPoints(int(data["TotalPoints"]))
								self.__retroAchievementUserRecord.setTotalTruePoints(int(data["TotalTruePoints"]))
								self.__retroAchievementUserRecord.save()

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
