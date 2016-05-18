#!/usr/bin/env python2

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2016 Neil Munday (neil@mundayweb.com)
#
#    PES is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PES is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PES.  If not, see <http://www.gnu.org/licenses/>.
#

import json
import os
import urllib
import urllib2
import logging
import multiprocessing
import pes.event
import sqlite3
import time
from datetime import datetime
from pes import *
from threading import Thread

class RetroAchievementGameTask(object):
	
	def __init__(self, userId, username, gameId, raConn, badgeDir):
		self.__userId = userId
		self.__gameId = gameId
		self.__username = username
		self.__raConn = raConn
		self.__badgeDir = badgeDir
		
	def __execute(self, query, fetch=False):
		row = None
		con = None
		with self.__lock:
			try:
				con = sqlite3.connect(userPesDb)
				con.row_factory = sqlite3.Row
				cur = con.cursor()
				cur.execute(query)
				if fetch:
					row = cur.fetchone()
				else:	
					con.commit()
				con.close()
			except sqlite3.Error, e:
				logging.error("Query failed: %s" % query)
				logging.exception(e)
			finally:
				if con:
					con.close()
		return row
	
	def __downloadBadge(self, url, path):
		try:
			logging.debug("RetroAchievementGameTask.__download: attempting to download %s" % url)
			request = urllib2.Request(url)
			response = urllib2.urlopen(request).read()
			logging.debug("RetroAchievementGameTask.__download: saving badge to %s" % path)
			output = open(path, 'wb')
			output.write(response)
			output.close()
		except Exception as e:
			logging.error("Failed to download %s to %s" % (url, path))
			logging.error(e)
		
	def run(self):
		try:
			result = self.__raConn.getGameInfoAndUserProgress(self.__username, self.__gameId)
		except Exception, e:
			logging.error("RetroAchievementGameTask.run: could not get game data for %s" % self.__gameId)
			logging.error(e)
			return
		
		achievementTotal = 0
		scoreTotal = 0
		
		if "Achievements" in result and result["Achievements"] != None:
			insertBadgesValues = []
			insertEarnedValues = []
			for a in result["Achievements"]:
				achievement = result["Achievements"][a]
				achievementTotal += 1
				points = int(achievement["Points"])
				scoreTotal += points
				badgeId = int(achievement["ID"])
				badgePath = os.path.join(self.__badgeDir, "%s.png" % badgeId)
				badgeLockedPath = os.path.join(self.__badgeDir, "%s_locked.png" % badgeId)
				# process achievement and badges here
				row = self.__execute("SELECT `title`, `description`, `points` FROM `achievements_badges` WHERE `badge_id` = %d;" % badgeId, True)
				if row == None:
					logging.debug("RetroAchievementGameTask.run: creating badge %d" % badgeId)
					insertBadgesValues.append("(%d, %d, '%s', '%s', %d, '%s', '%s')" % (badgeId, self.__gameId, achievement['Title'].replace("'", "''"), achievement['Description'].replace("'", "''"), points, badgePath, badgeLockedPath))
				else:
					if achievement['Title'] != row['title'] or points != int(row['points']) or achievement['Description'] != row['description']:
						logging.debug("RetroAchievementGameTask.run: updating %d" % badgeId)
						self.__execute("UPDATE `achievements_badges` SET `title` = '%s', `description` = '%s', `points` = %d WHERE `badge_id` = %d;" % (achievement['Title'].replace("'", "''"), achievement['Description'].replace("'", "''"), points, badgeId))
					else:
						logging.debug("RetroAchievementGameTask.run: no need to update %d" % badgeId)
				# download badges
				if not os.path.exists(badgePath):
					self.__downloadBadge("http://i.retroachievements.org/Badge/%s.png" % achievement["BadgeName"], badgePath)
				if not os.path.exists(badgeLockedPath):
					self.__downloadBadge("http://i.retroachievements.org/Badge/%s_lock.png" % achievement["BadgeName"], badgeLockedPath)
				# has the user earned this achievement?
				if 'DateEarned' in achievement:
					row = self.__execute("SELECT COUNT(*) AS `total` FROM `achievements_earned` WHERE `user_id` = %d AND `badge_id` = %d;" % (self.__userId, badgeId), True)
					if row == None or row['total'] == 0:
						ts = time.mktime(datetime.strptime(achievement['DateEarned'], '%Y-%m-%d %H:%M:%S').timetuple())
						insertEarnedValues.append("(%d, %d, %d)" % (self.__userId, badgeId, ts))
			# process inserts in one go - much quicker!
			if len(insertBadgesValues) > 0:
				self.__execute("INSERT INTO `achievements_badges` (`badge_id`, `game_id`, `title`, `description`, `points`, `badge_path`, `badge_locked_path`) VALUES %s;" % ",".join(insertBadgesValues))
			if len(insertEarnedValues) > 0:
				self.__execute("INSERT INTO `achievements_earned` (`user_id`, `badge_id`, `date_earned`) VALUES %s;" % ",".join(insertEarnedValues))
				
			row = self.__execute("SELECT `achievement_total`, `score_total` FROM `achievements_games` WHERE `game_id` = %d" % self.__gameId, True)
			if row == None:
				self.__execute("INSERT INTO `achievements_games` (`game_id`, `console_id`, `achievement_total`, `score_total`) VALUES (%d, %d, %d, %d);" % (self.__gameId, int(result["ConsoleID"]), achievementTotal, scoreTotal))
			else:
				if int(row['achievement_total']) != achievementTotal or int(row['score_total']) != scoreTotal:
					self.__execute("UPDATE `achievements_games` SET `achievement_total` = %d, `score_total` = %d WHERE `game_id` = %d;" % (achievementTotal, scoreTotal, self.__gameId))
	
		return achievementTotal
	
	def setLock(self, lock):
		self.__lock = lock

class RetroAchievementConn(object):
	
	URL = 'http://retroachievements.org/API/'
	URL_TIMEOUT = 10
	
	def __init__(self, user, apiKey):
		self.__user = user
		self.__apiKey = apiKey
		logging.debug("RetroAchievementConn.init: initialised")
		
	def __doRequest(self, apiUrl, params=None):
		obj = {'z' : self.__user, 'y': self.__apiKey }
		if params:
			for k, v in params.iteritems():
				obj[k] = v
		request = urllib2.Request("%s%s" % (RetroAchievementConn.URL, apiUrl), urllib.urlencode(obj))
		fullUrl = '%s?%s' % (request.get_full_url(), request.get_data())
		logging.debug("RetroAchievementConn.__doRequest: performing request for %s" % fullUrl)
		response = urllib2.urlopen(fullUrl)
		contents = response.read()
		if contents == "Invalid API Key":
			raise RetroAchievementConnException("Invalid API Key")
		s = json.loads(contents)
		return s
		
	def getConsoleIds(self):
		logging.debug("RetroAchievementConn.getConsoleIds: getting console IDs...")
		return self.__doRequest('API_GetConsoleIDs.php')
	
	def getGameInfo(self, gameId):
		logging.debug("RetroAchievementConn.getGameInfo: gameId = %d" % gameId)
		return self.__doRequest('API_GetGame.php', {'i': gameId})
	
	def getGameInfoAndUserProgress(self, user, gameId):
		logging.debug("RetroAchievementConn.getGameInfoAndUserProgress: user = %s, gameId = %d" % (user, gameId))
		return self.__doRequest('API_GetGameInfoAndUserProgress.php', {'u': user, 'g': gameId})
	
	def getGameList(self, consoleId):
		logging.debug("RetroAchievementConn.getGameList: console = %d" % consoleId)
		return self.__doRequest('API_GetGameList.php', {'i': consoleId})
	
	def getFeedFor(self, user, count, offset=0):
		logging.debug("RetroAchievementConn.getFeedFor: user = %s, count = %d, offset = %d" % (user, count, offset))
		return self.__doRequest('API_GetFeed.php', {'u': user, 'c': count, 'o': offset })

	def getUserProgress(self, user, gameIds):
		gameCsv = ','.join(str(x) for x in gameIds)
		logging.debug("RetroAchievementConn.getUserProgress: user = %s, gameIds = %s" % (user, gameCsv))
		return self.__doRequest('API_GetUserProgress.php', {'u': user, 'i': gameCsv})
	
	def getUsername(self):
		return self.__user
	
	def getUserAllGames(self, user):
		logging.debug("RetroAchievementConn.getAllGames: getting all games for %s" % user)
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
		logging.debug("RetroAchievementConn.getRecentlyPlayedGames: user = %s, count = %d, offset = %d" % (user, count, offset))
		return self.__doRequest('API_GetUserRecentlyPlayedGames.php', {'u': user, 'c': count, 'o': offset })
	
	def getUserSummary(self, user, recentGames):
		logging.debug("RetroAchievementConn.getUserSummary: getting user %s and games %s" % (user, recentGames))
		return self.__doRequest('API_GetUserSummary.php', {'u': user, 'g': recentGames, 'a': 5})
	
	def saveBadge(self, badgeId, path, locked=False):
		if locked:
			url = "http://i.retroachievements.org/Badge/%s_lock.png" % badgeId
		else:
			url = "http://i.retroachievements.org/Badge/%s.png" % badgeId
		logging.debug("RetroAchievementConn.saveBadge: attempting to download %s" % url)
		request = urllib2.Request(url)
		response = urllib2.urlopen(request).read()
		logging.debug("RetroAchievementConn.saveBadge: saving badge %s to %s" % (badgeId, path))
		output = open(path, 'wb')
		output.write(response)
		output.close()
	
class RetroAchievementConnException(Exception):
	
	def __init__(self, msg):
		Exception.__init__(self, msg)
	
class RetroAchievementGameConsumer(multiprocessing.Process):
	def __init__(self, taskQueue, resultQueue, exitEvent, lock):
		multiprocessing.Process.__init__(self)
		self.taskQueue = taskQueue
		self.resultQueue = resultQueue
		self.exitEvent = exitEvent
		self.lock = lock
		
	def run(self):
		# keep track of achievement total within the consumer
		# rather than adding to the result queue, thus keeping the maximum
		# result queue to the number of consumers and preventing deadlock
		achievementTotal = 0
		while True:
			task = self.taskQueue.get()
			if task is None:
				logging.debug("%s: exiting..." % self.name)
				self.taskQueue.task_done()
				break
			if self.exitEvent.is_set():
				self.taskQueue.task_done()
			else:
				task.setLock(self.lock)
				achievementTotal += task.run()
				self.taskQueue.task_done()
		self.resultQueue.put(achievementTotal)
		self.resultQueue.close()
		return
	
class RetroAchievementsUpdateThread(Thread):
	
	def __init__(self, raConn, badgeDir):
		Thread.__init__(self)
		self.done =  False
		self.started = False
		self.__tasks = None
		self.__exitEvent = None
		self.__raConn = raConn
		self.__badgeDir = badgeDir
		self.interrupted = False
		self.__queueSetUp = False
		self.success = True
		self.__badgeDownloadTotal = 0
		self.__gameTotal = 0
		self.__badgeTotal = 0
		logging.debug("RetroAchievementsUpdateThread.init: initialised")
		
	def __fail(self):
		logging.error("RetroAchievementsUpdateThread.__fail: failing...")
		self.__endTime = time.time()
		self.success = False
		self.done = True
		
	@staticmethod
	def formatTime(time):
		if time < 60:
			return "%ds" % time
		m, s = divmod(time, 60)
		h, m = divmod(m, 60)
		if h == 0:
			return "%dm %ds" % (m, s)
		return "%dh %dm %ds" % (h, m, s)
	
	def getBadgeTotal(self):
		return self.__badgeTotal
	
	def getElapsed(self):
		if not self.started:
			return self.formatTime(0)
		if self.started and not self.done:
			return self.formatTime(time.time() - self.__startTime)
		if self.done:
			return self.formatTime(self.__endTime - self.__startTime)
		
	def getProcessed(self):
		if not self.started or not self.__queueSetUp:
			return 0
		if self.done:
			return self.__gameTotal
		return self.__gameTotal - self.__tasks.qsize()
		
	def getProgress(self):
		if self.done:
			return 100
		if not self.started or not self.__queueSetUp or self.__gameTotal == 0:
			return 0
		# subtract poison pills from queue size
		qsize = self.__tasks.qsize() - self.consumerTotal
		if qsize <= 0:
			return 100
		return int((float(self.__gameTotal - qsize) / float(self.__gameTotal)) * 100.0)
	
	def getRemaining(self):
		processed = self.getProcessed()
		if processed == 0 or not self.started or self.done or self.__tasks.qsize() == 0:
			return self.formatTime(0)
		# now work out average time taken per game
		return self.formatTime(((time.time() - self.__startTime) / processed) * self.__tasks.qsize())
	
	def getTotal(self):
		return self.__gameTotal
		
	def run(self):
		logging.debug("RetroAchievementsUpdateThread.run: starting...")
		self.started = True
		self.__startTime = time.time()
		self.__exitEvent = multiprocessing.Event()
		self.__tasks = multiprocessing.JoinableQueue()
		results = multiprocessing.Queue()
		lock = multiprocessing.Lock()
		self.consumerTotal = multiprocessing.cpu_count() * 2
		logging.debug("RetroAchievementsUpdateThread.run: creating %d consumers" % self.consumerTotal)
		#consumers = [RetroAchievementImageConsumer(self.__tasks, self.__exitEvent) for i in xrange(self.consumerTotal)]
		consumers = [RetroAchievementGameConsumer(self.__tasks, results, self.__exitEvent, lock) for i in xrange(self.consumerTotal)]
		
		username = self.__raConn.getUsername()
		
		row = None
		con = None
		# update user table first
		try:
			result = self.__raConn.getUserSummary(username, 0)
		except Exception, e:
			logging.error(e)
			self.__fail()
			return
		
		logging.debug("RetroAchievementsUpdateThread.run: downloaded user stats ok!")
		try:
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			userId = int(result['ID'])
			cur.execute("INSERT OR REPLACE INTO `achievements_user` (`user_id`, `user_name`, `rank`, `total_points`, `total_truepoints`) VALUES (%d, '%s', %d, %d, %d);" % (userId, username.replace("'", "''"), int(result['Rank']), int(result['TotalPoints']), int(result['TotalTruePoints'])))
			cur.execute("SELECT COUNT(*) AS `total` FROM `games` WHERE `achievement_api_id` > 0;")
			row = cur.fetchone()
			logging.debug("RetroAchievementsUpdateThread.run: found %d games to process..." % row['total'])
			self.__gameTotal = int(row['total'])
			if self.__gameTotal > 0:
				cur.execute("SELECT `achievement_api_id` FROM `games` WHERE `achievement_api_id` > 0;")
				ok = False
				while True:
					row = cur.fetchone()
					if row == None:
						break
					self.__tasks.put(RetroAchievementGameTask(userId, username, row['achievement_api_id'], self.__raConn, self.__badgeDir))
			con.commit()
			con.close()
		except sqlite3.Error, e:
			if con:
				con.rollback()
			logging.error(e)
			self.__fail()
			return
		finally:
			if con:
				con.close()
		
		if self.interrupted:
			self.__stopHelper()
			return
		
		# use sub processes to download badges in parallel
		for i in xrange(self.consumerTotal):
			self.__tasks.put(None)
			
		logging.debug("RetroAchievementsUpdateThread.run: added poison pills")
		self.__queueSetUp = True
		
		for w in consumers:
			w.start()
		
		for w in consumers:
			w.join()
		
		self.__tasks.join()
		
		logging.debug("RetroAchievementsUpdateThread.run: processing results...")
		while not results.empty():
			self.__badgeTotal += results.get()
		
		self.__endTime = time.time()
		self.done = True
		self.success = True
		pes.event.pushPesEvent(pes.event.EVENT_ACHIEVEMENTS_UPDATE)
		logging.debug("RetroAchievementsUpdateThread.run: finished!")
		
	def stop(self):
		if self.started and not self.done:
			self.interrupted = True
			logging.debug("RetroAchievementsUpdateThread.stop: stopping processes...")
			self.__exitEvent.set()
		else:
			self.done = True
			
	def __stopHelper(self):
		self.__endTime = time.time()
		self.done = True
		self.success = False
		logging.debug("RetroAchievementsUpdateThread.run: finished!")

