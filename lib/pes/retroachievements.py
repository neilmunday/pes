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
import sqlite3
import time
from datetime import datetime
from pes import *
from threading import Thread

class RetroAchievementBadgeTask(object):
	
	def __init__(self, badgeName, path, locked=False):
		if locked:
			self.__url = "http://i.retroachievements.org/Badge/%s_lock.png" % badgeName
		else:
			self.__url = "http://i.retroachievements.org/Badge/%s.png" % badgeName
		self.__path = path
		
	def run(self):
		logging.debug("RetroAchievementBadgeTask.run: attempting to download %s" % self.__url)
		request = urllib2.Request(self.__url)
		response = urllib2.urlopen(request).read()
		logging.debug("RetroAchievementConn.saveBadge: saving badge to %s" % self.__path)
		output = open(self.__path, 'wb')
		output.write(response)
		output.close()

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
			raise RetroAchievementException("Invalid API Key")
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

class RetroAchievementImageConsumer(multiprocessing.Process):
	def __init__(self, taskQueue, exitEvent):
		multiprocessing.Process.__init__(self)
		self.taskQueue = taskQueue
		self.exitEvent = exitEvent
		
	def run(self):
		while True:
			task = self.taskQueue.get()
			if task is None:
				logging.debug("%s: exiting..." % self.name)
				self.taskQueue.task_done()
				return
			if not self.exitEvent.is_set():
				task.run()
			self.taskQueue.task_done()
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
	
	def getElapsed(self):
		if not self.started:
			return self.formatTime(0)
		if self.started and not self.done:
			return self.formatTime(time.time() - self.__startTime)
		if self.done:
			return self.formatTime(self.__endTime - self.__startTime)
		
	def getProgress(self):
		if self.done:
			return 100
		if not self.started or not self.__queueSetUp:
			return 0
		# subtract poison pills from queue size
		qsize = self.__tasks.qsize() - self.consumerTotal
		if qsize <= 0:
			return 100
		return int((float(self.__badgeDownloadTotal - qsize) / float(self.__badgeDownloadTotal)) * 100.0)
		
	def run(self):
		logging.debug("RetroAchievementsUpdateThread.run: starting...")
		self.started = True
		self.__startTime = time.time()
		self.__exitEvent = multiprocessing.Event()
		self.__tasks = multiprocessing.JoinableQueue()
		self.consumerTotal = multiprocessing.cpu_count() * 2
		logging.debug("RetroAchievementsUpdateThread.run: creating %d consumers" % self.consumerTotal)
		consumers = [RetroAchievementImageConsumer(self.__tasks, self.__exitEvent) for i in xrange(self.consumerTotal)]
		
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
				
			# now get all the user's games
			try:
				games = self.__raConn.getUserAllGames(username)
			except Exception, e:
				logging.error(e)
				self.__fail()
				return
			logging.debug("RetroAchievementsUpdateThread.run: downloaded user games ok!")
			for g in games:
				if self.interrupted:
					self.__stopHelper()
					return
				if g["NumPossibleAchievements"] > 0:
					gameId = int(g['GameID'])
					cur.execute("INSERT OR REPLACE INTO `achievements_games` (`game_id`, `console_id`, `name`, `achievement_total`, `score_total`) VALUES (%d, %d, '%s', %d, %d);" % (gameId, int(g['ConsoleID']), g['Title'].replace("'", "''"), int(g['NumPossibleAchievements']), int(g['PossibleScore'])))

					# now get all the achievements for the game
					try:
						achievements = self.__raConn.getGameInfoAndUserProgress(username, gameId)
						#print json.dumps(achievements, sort_keys=True, indent=4, separators=(',', ': '))
					except Exception, e:
						logging.error(e)
						self.__fail()
						return
					
					for k, v in achievements['Achievements'].iteritems():
						if self.interrupted:
							self.__stopHelper()
							return
						badgeId = int(k)
						badgePath = os.path.join(self.__badgeDir, "%s.png" % k)
						badgeLockedPath = os.path.join(self.__badgeDir, "%s_locked.png" % k)
						cur.execute("INSERT OR REPLACE INTO `achievements_badges` (`badge_id`, `game_id`, `title`, `description`, `points`, `badge_path`, `badge_locked_path`) VALUES (%d, %d, '%s', '%s', %d, '%s', '%s');" % (badgeId, gameId, v['Title'].replace("'", "''"), v['Description'].replace("'", "''"), int(v['Points']), badgePath, badgeLockedPath))
						
						if 'DateEarned' in v:
							ts = time.mktime(datetime.strptime(v['DateEarned'], '%Y-%m-%d %H:%M:%S').timetuple())
							cur.execute("INSERT OR IGNORE INTO `achievements_earned` (`user_id`, `badge_id`, `game_id`, `date_earned`) VALUES (%d, %d, %d, %d);" % (userId, badgeId, gameId, ts))
						
						# create badge download task (if needed)
						if not os.path.exists(badgePath):
							self.__tasks.put(RetroAchievementBadgeTask(v['BadgeName'], badgePath))
							self.__badgeDownloadTotal += 1
						if not os.path.exists(badgeLockedPath):
							self.__tasks.put(RetroAchievementBadgeTask(v['BadgeName'], badgeLockedPath, True))
							self.__badgeDownloadTotal += 1
					
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
		
		self.__endTime = time.time()
		self.done = True
		self.success = True
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
