#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2019 Neil Munday (neil@mundayweb.com)
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

from PIL import Image
from datetime import datetime
from time import sleep
from pes import *
from pes.data import *
from pes.util import *
from subprocess import Popen, PIPE
from threading import Thread
import glob
import json
import logging
import pes.event
import sqlite3
import sys
import urllib
import urllib2
import time
import multiprocessing

URL_TIMEOUT = 30
logging.getLogger("PIL").setLevel(logging.WARNING)

# my theGamesDbApi public key - rate limited per IP per month
API_KEY = "d12fb5ce1f84c6cb3cec2b89861551905540c0ab564a5a21b3e06e34b2206928"
API_URL = "https://api.thegamesdb.net"

class ConsoleTask(object):

	SCALE_WIDTH = 200.0

	def __init__(self, rom, console):
		self.rom = rom
		self.console = console

	def __repr__(self):
		return self.rom

	def __execute(self, query, fetch=False):
		row = None
		con = None
		with self.lock:
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
				logging.exception(e)
			finally:
				if con:
					con.close()
		return row

	def run(self):
		headers = { "accept": "application/json", 'User-Agent': 'PES Scraper'}
		imgExtensions = ['jpg', 'jpeg', 'png', 'gif']

		rom = self.rom
		cacheDir = self.console.getImgCacheDir()
		consoleId = self.console.getId()
		consoleName = self.console.getName()
		consoleApiId = self.console.getTheGamesDbApiId()

		added = 0
		updated = 0

		filename = os.path.split(rom)[1]
		#if not console.ignoreRom(filename):
		logging.debug("ConsoleTask: processing -> %s" % filename)
		name = filename
		fileSize = os.path.getsize(rom)
		for e in self.console.getExtensions():
			name = name.replace(e, '')

		if not self.console.ignoreRom(name):

			row = self.__execute("SELECT `full_name` FROM `games_catalogue` WHERE `short_name` = \"%s\"" % name, True)
			if row:
				name = row['full_name']

			row = self.__execute("SELECT `game_id`, `name`, `cover_art`, `game_path`, `thegamesdb_id` FROM `games` WHERE `game_path` = \"%s\";" % rom, True)
			if row == None or (row['cover_art'] == "0" and row['thegamesdb_id'] == -1) or (row['cover_art'] != "0" and not os.path.exists(row['cover_art'])):
				gameApiId = -1
				thumbPath = '0'

				# has cover art already been provided by the user or downloaded previously?
				for e in imgExtensions:
					path = os.path.join(cacheDir, "%s.%s" % (filename, e))
					if os.path.exists(path):
						thumbPath = path
						break
					path2 = os.path.join(cacheDir, "%s.%s" % (name.replace('/', '_'), e))
					if path != path2:
						path = path2
						if os.path.exists(path):
							thumbPath = path
							break

				if thumbPath != '0':
					# can the image be opened?
					imgOk = False
					try:
						img = Image.open(thumbPath)
						img.close()
					except IOError as e:
						logging.warning("ConsoleTask: %s is not a valid image, it will be deleted" % thumbPath)
						os.remove(thumbPath)
						thumbPath = '0'

				overview = ''
				released = -1

				# now grab thumbnail
				obj = {
					'apikey': '%s' % API_KEY,
					'name': name,
					'fields': 'overview',
					'filter[platform]': consoleApiId,
					'include': 'boxart'
				}
				urlLoaded = False
				nameLower = name.lower()

				try:
					request = urllib2.Request("%s/Games/ByGameName?%s" % (API_URL, urllib.urlencode(obj)), headers=headers)
					response = urllib2.urlopen(request, timeout=URL_TIMEOUT)
					logging.debug("ConsoleTask: %s" % response.geturl())
					urlLoaded = True
				except Exception as e:
					logging.error(e)
					logging.error("Failed to process: %s" % filename)

				if urlLoaded:
					bestResultDistance = -1
					dataOk = False
					try:
						data = json.load(response)
						logging.debug(data)
						if "code" not in data or data["code"] != 200:
							raise Exception("Query not successful")
						if data["data"]["count"] == 0:
							# no results!
							logging.warning("No search results found for %s from theGamesDb.net" % filename)
						else:
							dataOk = True
					except Exception, e:
						logging.error(e)

					if dataOk:
						for game in data["data"]["games"]:
							gameNameLower = game["game_title"].lower()
							if gameNameLower == nameLower:
								gameApiId = game["id"]
								overview = game["overview"].encode('ascii', 'ignore').strip()
								if game["release_date"] != None:
									released = game["release_date"].encode('ascii', 'ignore').strip()
								break

							stringMatcher = StringMatcher(str(nameLower), str(gameNameLower))
							distance = stringMatcher.distance()

							if bestResultDistance == -1 or distance < bestResultDistance:
								bestResultDistance = distance
								gameApiId = game["id"]
								overview = game["overview"].encode('ascii', 'ignore').strip()
								if game["release_date"] != None:
									released = game["release_date"].encode('ascii', 'ignore').strip()

						# try to convert released str into a Unix timestamp
						if released != -1:
							try:
								released = int(time.mktime(datetime.strptime(released, "%Y-%m-%d").timetuple()))
							except ValueError, e:
								# thrown if date is not valid
								released = -1

						# get cover art
						gameApiIdStr = str(gameApiId)
						if thumbPath == "0" and gameApiIdStr in data["include"]["boxart"]["data"]:
							#mediumUrl = data["include"]["boxart"]["base_url"]["medium"]
							#origUrl =
							for image in data["include"]["boxart"]["data"][gameApiIdStr]:
								if image["side"] == "front":
									for i in ["medium", "large", "original"]:
										imgUrl = "%s%s" % (data["include"]["boxart"]["base_url"][i], image["filename"])
										logging.debug("Downloading image from: %s" % imgUrl)
										extension = imgUrl[imgUrl.rfind('.'):]
										thumbPath =  self.console.getImgCacheDir() + os.sep + name.replace('/', '_') + extension
										imgSaved = False
										urlLoaded = False
										try:
											request = urllib2.Request(imgUrl, headers={'User-Agent': 'PES Scraper'})
											response = urllib2.urlopen(request, timeout=URL_TIMEOUT).read()
											urlLoaded = True
										except Exception as e:
											logging.error("Failed to load URL: %s" % imgUrl)
											logging.error(e)
										if urlLoaded:
											try:
												with open(thumbPath, 'wb') as f:
													f.write(response)
											except Exception as e:
												logging.error("Failed to save: %s")
												logging.error(e)
												thumbPath = '0'
											if thumbPath != '0':
												# can we open the image
												try:
													img = Image.open(thumbPath)
													img.close()
													# opened ok
													break
												except Exception as e:
													logging.warning("Could not open saved image from: %s" % imgUrl)
									break

				if thumbPath != '0':
					try:
						thumbPathNew = self.__scaleImage(thumbPath)
						thumbPath = thumbPathNew
					except Exception as e:
						logging.error("Failed to scale %s" % thumbPath)
						logging.error(e)
						thumbPath = '0'

				if row == None:
					rasum = "NULL"
					achievementApiId = -1
					if self.console.getAchievementApiId() != "NULL":
						# work out rasum (if applicable)
						if consoleName == "MegaDrive" or consoleName == "Genesis":
							command = "%s -t genesis \"%s\"" % (rasumExe, rom)
						elif consoleName == "NES":
							command = "%s -t nes \"%s\"" % (rasumExe, rom)
						elif consoleName == "SNES":
							command = "%s -t snes \"%s\"" % (rasumExe, rom)
						else:
							command = "%s \"%s\"" % (rasumExe, rom)
						process = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
						stdout, stderr = process.communicate()
						if process.returncode != 0:
							logging.error("Failed to run command: %s\nstdout: %s\nstderr: %s\n" % (command, stdout, stderr))
						else:
							rasum = stdout.replace("\n", "")
							# now look-up achievement API ID from retroachievements.org
							try:
								request = urllib2.Request("http://www.retroachievements.org/dorequest.php", urllib.urlencode({'r': 'gameid', 'm': rasum}))
								fullUrl = '%s?%s' % (request.get_full_url(), request.get_data())
								response = urllib2.urlopen(fullUrl)
								contents = response.read()
								s = json.loads(contents)
								if s["Success"]:
									achievementApiId = int(s["GameID"])
								else:
									logging.error("Failed to process %s for %s" % (fullUrl, rom))
							except Exception as e:
								logging.error("The following error occurred when processing: %s" % rom)
								logging.error(e)

					self.__execute("INSERT INTO `games`(`exists`, `console_id`, `name`, `game_path`, `thegamesdb_id`, `cover_art`, `overview`, `released`, `added`, `favourite`, `last_played`, `play_count`, `size`, `rasum`, `achievement_api_id`) VALUES (1, %d, '%s', '%s', %d, '%s', '%s', %d, %d, 0, -1, 0, %d, '%s', %d);" % (consoleId, name.replace("'", "''"), rom.replace("'", "''"), int(gameApiId), thumbPath.replace("'", "''"), overview.replace("'", "''"), released, time.time(), fileSize, rasum, achievementApiId))
					added += 1
				elif gameApiId != -1:
					self.__execute("UPDATE `games` SET `thegamesdb_id` = %d, `cover_art` = '%s', `overview` = '%s', `released` = %d, `exists` = 1 WHERE `game_id` = %d;" % (int(gameApiId), thumbPath.replace("'", "''"), overview.replace("'", "''"), released, row['game_id']))
					updated += 1
				else:
					self.__execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])
			else:
				self.__execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])

		return (added, updated)

	@staticmethod
	def __scaleImage(path):
		img = Image.open(path)
		imgFormat = img.format
		filename, extension = os.path.splitext(path)
		logging.debug("%s format is %s" % (path, imgFormat))
		width, height = img.size
		scaleWidth = ConsoleTask.SCALE_WIDTH
		ratio = min(float(scaleWidth / width), float(scaleWidth / height))
		newWidth = width * ratio
		newHeight = height * ratio
		if width > newWidth or height > newHeight:
			# scale image
			img.thumbnail((newWidth, newHeight), Image.ANTIALIAS)
		if imgFormat == "JPEG":
			extension = ".jpg"
		elif imgFormat == "PNG":
			extension = ".png"
		elif imgFormat == "GIF":
			extension = ".gif"
		else:
			imgFormat = "PNG"
			extension = ".png"
		newPath = "%s%s" % (filename, extension)
		if newPath != path:
			logging.warning("%s will be deleted and saved as %s due to incorrect image format" % (path, newPath))
			os.remove(path)
		img.save(newPath, imgFormat)
		img.close()
		return newPath

	def setLock(self, lock):
		self.lock = lock

class Consumer(multiprocessing.Process):
	def __init__(self, taskQueue, resultQueue, exitEvent, lock):
	#def __init__(self, taskQueue, lock):
		multiprocessing.Process.__init__(self)
		self.taskQueue = taskQueue
		self.resultQueue = resultQueue
		self.lock = lock
		self.exitEvent = exitEvent

	def run(self):
		# keep track of updated and added totals within the consumer
		# rather than adding to the result queue, thus keeping the maximum
		# result queue to the number of consumers and preventing deadlock
		added = 0
		updated = 0
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
				result = task.run()
				added += result[0]
				updated += result[1]
				self.taskQueue.task_done()
		self.resultQueue.put((added, updated))
		self.resultQueue.close()

class UpdateDbThread(Thread):

	def __init__(self, consoles):
		Thread.__init__(self)
		self.done =  False
		self.started = False
		self.__tasks = None
		self.__exitEvent = None
		self.consoles = consoles
		self.romTotal = 0
		self.added = 0
		self.updated = 0
		self.deleted = 0
		self.interrupted = False
		self.__queueSetUp = False

	@staticmethod
	def __extensionOk(extensions, filename):
		for e in extensions:
			if filename.endswith(e):
				return True
		return False

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

	def getProcessed(self):
		if not self.started or not self.__queueSetUp:
			return 0
		if self.done:
			return self.romTotal
		return self.romTotal - self.__tasks.qsize()

	def getProgress(self):
		if self.done:
			return 100
		if self.romTotal == 0:
			return 0
		if not self.started or not self.__queueSetUp:
			return 0
		# subtract poison pills from queue size
		qsize = self.__tasks.qsize() - self.consumerTotal
		if qsize <= 0:
			return 100
		return int((float(self.romTotal - qsize) / float(self.romTotal)) * 100.0)

	def getRemaining(self):
		processed = self.getProcessed()
		if processed == 0 or not self.started or self.done or self.__tasks.qsize() == 0:
			return self.formatTime(0)
		# now work out average time taken per ROM
		return self.formatTime(((time.time() - self.__startTime) / processed) * self.__tasks.qsize())

	def getUnprocessed(self):
		if not self.__queueSetUp:
			return self.romTotal
		return self.__tasks.qsize()

	def run(self):
		self.__startTime = time.time()
		self.added = 0
		self.updated = 0
		self.deleted = 0
		self.interrupted = False
		self.__queueSetUp = False
		lock = multiprocessing.Lock()
		self.__tasks = multiprocessing.JoinableQueue()
		self.__exitEvent = multiprocessing.Event()
		results = multiprocessing.Queue()
		self.started = True
		self.consumerTotal = multiprocessing.cpu_count() * 2
		logging.debug("UpdateDbThread.run: creating %d consumers" % self.consumerTotal)
		consumers = [Consumer(self.__tasks, results, self.__exitEvent, lock) for i in xrange(self.consumerTotal)]

		headers = { "accept": "application/json"}

		con = None
		cur = None

		for c in self.consoles:
			consoleName = c.getName()
			consoleId = c.getId()
			cacheDir = c.getImgCacheDir()

			urlLoaded = False

			try:
				con = sqlite3.connect(userPesDb)
				con.row_factory = sqlite3.Row
				cur = con.cursor()
				cur.execute("UPDATE `games` SET `exists` = 0 WHERE `console_id` = %d" % consoleId)
				con.commit()
			except sqlite3.Error, e:
				logging.error(e)
				if con:
					con.rollback()
				sys.exit(1)
			finally:
				if con:
					con.close()

			files = glob.glob("%s%s*" % (c.getRomDir(), os.sep))
			fileTotal = len(files)
			extensions = c.getExtensions()

			romFiles = []

			for f in files:
				if os.path.isfile(f) and self.__extensionOk(extensions, f):
					romFiles.append(f)
					self.romTotal += 1

			if len(romFiles) > 0:
				for f in romFiles:
					self.__tasks.put(ConsoleTask(f, c))

		logging.debug("UpdateDbThread.run: added %d ROMs to the queue" % self.romTotal)

		for i in xrange(self.consumerTotal):
			self.__tasks.put(None)

		logging.debug("UpdateDbThread.run: added poison pills")
		self.__queueSetUp = True

		logging.debug("UpdateDbThread.run: starting consumers...")
		for w in consumers:
			w.start()

		for w in consumers:
			w.join()
		logging.debug("UpdateDbThread.run: consumers joined!")

		self.__tasks.join()
		logging.debug("UpdateDbThread.run: tasks joined!")

		logging.debug("UpdateDbThread.run: processing results...")
		while not results.empty():
			(added, updated) = results.get()
			self.added += added
			self.updated += updated

		logging.debug("UpdateDbThread.run: processes finished")

		try:
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()

			if self.interrupted:
				cur.execute("UPDATE `games` SET `exists` = 1 WHERE `exists` = 0")
			else:
				cur.execute("DELETE FROM `games` WHERE `exists` = 0")
				self.deleted = con.total_changes
			con.commit()
		except sqlite3.Error, e:
			logging.error(e)
			if con:
				con.rollback()
		finally:
			if con:
				con.close()

		logging.debug("UpdateDbThread.run: pushing PES event...")
		pes.event.pushPesEvent(pes.event.EVENT_DB_UPDATE)

		self.done = True
		self.__endTime = time.time()
		logging.debug("UpdateDbThread.run: exiting")

	def stop(self):
		if self.started and not self.done:
			self.interrupted = True
			logging.debug("UpdateDbThread.stop: stopping processes...")
			self.__exitEvent.set()
		else:
			self.done = True
