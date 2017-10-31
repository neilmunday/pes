import glob
import logging
import multiprocessing
import os
import sys
import time
import urllib
import shutil

from datetime import datetime

import pes
from pes.common import StringMatcher
from pes.data import GameRecord, GameMatchRecord, GameTitleRecord

from PIL import Image

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtSql import QSqlDatabase, QSqlQuery

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, ParseError, SubElement

URL_TIMEOUT = 30
MATCH_LIMIT = 5
logging.getLogger("PIL").setLevel(logging.WARNING)

class RomTask(object):

	SCALE_WIDTH = 200.0
	IMG_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif']

	def __init__(self, rom, consoleId, romExtensions, ignoreRoms, coverArtDir):
		"""
			@param	rom		path to ROM
			@param	console	console object
		"""
		self._rom = rom
		self._consoleId = consoleId
		self._romExtensions = romExtensions
		self._ignoreRoms = ignoreRoms
		self._covertArtDir = coverArtDir

	def _doQuery(self, q):
		with self._lock:
			logging.debug("RomTask._doQuery: %s" % q)
			db = self._openDb()
			query = QSqlQuery(db)
			if not query.exec_(q):
				raise Exception("RomTask._doQuery: Error \"%s\" encountered whilst executing:\n%s" % (query.lastError().text(), q))
			db.commit()
			db.close()
			del db
			QSqlDatabase.removeDatabase(self._connName)
		return query

	def _openDb(self):
		logging.debug("RomTask._openDb")
		db = QSqlDatabase.addDatabase("QSQLITE", self._connName)
		db.setDatabaseName(pes.userDb)
		db.open()
		return db

	def setLock(self, lock):
		self._lock = lock

	@staticmethod
	def _scaleImage(path):
		try:
			img = Image.open(path)
			width, height = img.size
			scaleWidth = RomTask.SCALE_WIDTH
			ratio = min(float(scaleWidth / width), float(scaleWidth / height))
			newWidth = width * ratio
			newHeight = height * ratio
			if width > newWidth or height > newHeight:
				# scale image
				img.thumbnail((newWidth, newHeight), Image.ANTIALIAS)
				img.save(path)
			img.close()
		except IOError as e:
			logging.error("RomTask._scaleImage: Failed to scale: %s" % path)
			return False
		return True

class GamesDbRomTask(RomTask):

	def __init__(self, rom, consoleId, consoleApiName, romExtensions, ignoreRoms, coverArtDir):
		super(GamesDbRomTask, self).__init__(rom, consoleId, romExtensions, ignoreRoms, coverArtDir)
		self._consoleApiName = consoleApiName

	def run(self, processNumber):
		self._connName = "romTask_%d" % processNumber
		filename = os.path.split(self._rom)[1]
		logging.debug("GamesDbRomTask.run: processing -> %s" % filename)

		added = 0
		updated = 0
		thumbPath = "0"
		name = filename

		for e in self._romExtensions:
			if name.endswith(e):
				name = name.replace(e, '')
				break

		if name not in self._ignoreRoms:
			query = self._doQuery("SELECT `full_name` FROM `games_catalogue` WHERE `short_name` = \"%s\"" % name)
			if query.first():
				name = query.value(0)

			nameNoSlashes = name.replace("/", "_")

			query = self._doQuery("SELECT `game_id`, `coverart`, `path` FROM `game` WHERE `path` = \"%s\";" % self._rom)
			found = query.first()
			if not found:
				# new game
				gameApiId = None
				bestName = name
				bestGameTitleId = 0
				gameTitleId = 0
				gameMatches = []
				released = -1
				overview = ""

				# new game, but do we already have cover art for it?
				for e in RomTask.IMG_EXTENSIONS:
					path = os.path.join(self._covertArtDir, "%s.%s" % (name, e))
					if os.path.exists(path):
						thumbPath = path
						break
					path2 = os.path.join(self._covertArtDir, "%s.%s" % (nameNoSlashes, e))
					if path != path2:
						if os.path.exists(path2):
							thumbPath = path2
							break

				if thumbPath != "0":
					# can we open the image?
					imgOk = False
					try:
						img = Image.open(thumbPath)
						img.close()
						logging.debug("GamesDbRomTask: Found cover art for \"%s\" at %s" % (name, thumbPath))
					except IOError as e:
						logging.warning("GamesDbRomTask: %s is not a valid image, it will be deleted")
						os.remove(thumbPath)
						thumbPath = "0"

				if self._consoleApiName != "NULL":
					# search for ROM in theGamesDb
					urlLoaded = False
					nameLower = name.lower()
					try:
						request = urllib.request.Request("%sGetGamesList.php" % RomScanThread.GAMES_DB_URL, urllib.parse.urlencode({ "name": "%s" % name, "platform": self._consoleApiName }).encode("utf-8"), headers=RomScanThread.HEADERS)
						response = urllib.request.urlopen(request, timeout=URL_TIMEOUT)
						urlLoaded = True
					except Exception as e:
						logging.error("GamesDbRomTask: Could not perform search for \"%s\" in \"%s\"" % (name, self._consoleApiName))
						logging.error(e)

					if urlLoaded:
						dataOk = False
						bestResultDistance = -1
						try:
							xmlData = ElementTree.parse(response)
							dataOk = True
						except Exception as e:
							logging.error("GamesDbRomTask: Failed to parse response for \"%s\" in \"%s\"" % (name, self._consoleApiName))
							logging.error(e)

						if dataOk:
							count = 0
							for x in xmlData.findall("Game"):
								xname = x.find("GameTitle").text.encode('ascii', 'ignore').decode()
								xid = int(x.find("id").text)

								query = self._doQuery("SELECT `game_title_id`, `gamesdb_id`, `game_title_id`, `title` FROM `game_title` WHERE `console_id` = %d AND `title` = \"%s\";" % (self._consoleId, xname))
								with self._lock:
									if query.first():
										gameTitleId = query.value(0)
										gameTitleRecord = GameTitleRecord(self._openDb(), gameTitleId, query.record())
										gameTitleRecord.setGamesDbId(xid)
									else:
										gameTitleRecord = GameTitleRecord(self._openDb(), None)
										gameTitleRecord.setConsoleId(self._consoleId)
										gameTitleRecord.setGamesDbId(xid)
										gameTitleRecord.setTitle(xname)
										gameTitleRecord.save()
										gameTitleId = gameTitleRecord.getId()
									del gameTitleRecord
									QSqlDatabase.removeDatabase(self._connName)
								gameMatches.append(gameTitleId)

								if xname.lower() == nameLower:
									gameApiId = xid
									bestResultDistance = 0
									bestName = xname
									bestGameTitleId = gameTitleId

								stringMatcher = StringMatcher(str(nameLower.replace(" ", "")), xname.lower().replace(" ", ""))
								distance = stringMatcher.distance()

								if bestResultDistance == -1 or distance < bestResultDistance:
									bestResultDistance = distance
									bestName = xname
									bestGameTitleId = gameTitleId
									gameApiId = xid

								count += 1
								if count == MATCH_LIMIT:
									break

				if gameApiId != None:
					logging.debug("GamesDbRomTask: \"%s\" (%s) theGamesDb ID: %d" % (name, self._consoleApiName, gameApiId))
					# now get ROM meta data
					urlLoaded = False
					try:
						request = urllib.request.Request(
							"%sGetGame.php" % RomScanThread.GAMES_DB_URL,
							urllib.parse.urlencode({
								"id": "%d" % gameApiId,
							}).encode("utf-8"),
							headers=RomScanThread.HEADERS
						)
						response = urllib.request.urlopen(request, timeout=URL_TIMEOUT)
						urlLoaded = True
					except Exception as e:
						logging.error("GamesDbRomTask: Could not load URL for %d" % gameApiId)
						logging.error(e)

					if urlLoaded:
						dataOk = False
						try:
							xmlData = ElementTree.parse(response)
							dataOk = True
						except Exception as e:
							logging.error("GamesDbRomTask: Failed to parse response for %d" % gameApiId)
							logging.error(e)

						if dataOk:
							overviewElement = xmlData.find("Game/Overview")
							if overviewElement != None:
								overview = overviewElement.text.encode('ascii', 'ignore').decode()
							releasedElement = xmlData.find("Game/ReleaseDate")
							if releasedElement != None:
								released = releasedElement.text.encode('ascii', 'ignore').decode()
								# convert to Unix time stamp
								try:
									released = int(time.mktime(datetime.strptime(released, "%m/%d/%Y").timetuple()))
								except ValueError as e:
									# thrown if date is not valid
									released = -1

							if thumbPath == "0":
								# no cover art, let's download some
								boxartElement = xmlData.find("Game/Images/boxart[@side='front']")
								if boxartElement != None:
									imageSaved = False
									try:
										imgUrl = "http://thegamesdb.net/banners/%s" % boxartElement.text
										extension = imgUrl[imgUrl.rfind('.'):]
										thumbPath = os.path.join(self._covertArtDir, "%s%s" % (name.replace('/', '_'), extension))
										request = urllib.request.Request(
											imgUrl,
											headers=RomScanThread.HEADERS
										)
										response = urllib.request.urlopen(request, timeout=URL_TIMEOUT)
										with open(thumbPath, "wb") as f:
											shutil.copyfileobj(response, f)
										# resize the image (if required)
										if not self._scaleImage(thumbPath):
											thumbPath = "0"
									except Exception as e:
										logging.error("GamesDbRomTask: failed to get covert art for %d" % gameApiId)
										logging.error(e)

							with self._lock:
								logging.debug("GamesDbRomTask: creating new GameRecord object")
								db = self._openDb()
								game = GameRecord(db, None)
								game.setExists(True)
								game.setAdded(time.time())
								game.setConsoleId(self._consoleId)
								game.setCoverArt(thumbPath)
								game.setLastPlayed(0)
								game.setName(bestName)
								game.setOverview(overview)
								game.setPath(self._rom)
								game.setReleased(released)
								game.setSize(os.path.getsize(self._rom))
								game.save()
								gameId = game.getId()

								# now save matches
								for titleId in gameMatches:
									gameMatch = GameMatchRecord(db, None)
									gameMatch.setGameId(gameId)
									gameMatch.setTitleId(titleId)
									gameMatch.save()
									if titleId == bestGameTitleId:
										game.setMatchId(gameMatch.getId())
										game.save()
									del gameMatch

								del game
								del db
								QSqlDatabase.removeDatabase(self._connName)

							added += 1

		return (added, updated, name, thumbPath)

class RomProcess(multiprocessing.Process):

	def __init__(self, processNumber, taskQueue, resultQueue, exitEvent, lock, romList):
		super(RomProcess, self).__init__()
		self.__processNumber = processNumber
		self.__taskQueue = taskQueue
		self.__resultQueue = resultQueue
		self.__exitEvent = exitEvent
		self.__lock = lock
		self.__romList = romList

	def run(self):

		added = 0
		updated = 0
		while True:
			task = self.__taskQueue.get()
			if task is None:
				logging.debug("%s: exiting..." % self.name)
				self.__taskQueue.task_done()
				break
			if self.__exitEvent.is_set():
				self.__taskQueue.task_done()
			else:
				task.setLock(self.__lock)
				try:
					result = task.run(self.__processNumber)
					added += result[0]
					updated += result[1]
					if not self.__exitEvent.is_set():
						self.__romList.append((result[2], result[3]))
				except Exception as e:
					logging.error("%s: Failed to process task due to the following error:" % self.name)
					logging.error(e)
				self.__taskQueue.task_done()
		self.__resultQueue.put((added, updated))
		self.__resultQueue.close()

class RomScanThread(QThread):

	GAMES_DB_URL = 'http://thegamesdb.net/api/'
	HEADERS = {'User-Agent': 'PES Scraper'}

	romsFoundSignal = pyqtSignal(int)
	finishedSignal = pyqtSignal()

	def __init__(self, db, consoleNames, consoleMap, romScraper):
		"""
		@param 	consoleNames	list of console names to scan
		@param	consoleMap		dictionary of console objects
		"""
		super(RomScanThread, self).__init__(None)
		if romScraper not in pes.romScrapers:
			raise Exception("%s is not a known ROM scraper" % romScraper)
		self.__progress = 0
		self.__romTotal = 0
		self.__db = db
		self.__consoleNames = consoleNames
		self.__consoleMap = consoleMap
		self.__romScraper = romScraper
		self.__done = False
		self.__started = False
		self.__startTime = 0
		self.__endTime = 0
		self.__added = 0
		self.__updated = 0
		self.__tasks = None
		self.__romList = None
		self.__exitEvent = None

	@staticmethod
	def __extensionOk(extensions, filename):
		for e in extensions:
			if filename.endswith(e):
				return True
		return False

	def getAdded(self):
		return self.__added

	def getLastRom(self):
		if self.__romList == None or not self.__started or (self.__exitEvent != None and self.__exitEvent.is_set()) or len(self.__romList) == 0:
			return None
		return self.__romList[-1]

	def getProcessed(self):
		if not self.started or self.__tasks == None:
			return 0
		if self.__done:
			return self.__romTotal
		return self.__romTotal - self.__tasks.qsize()

	def getProgress(self):
		if self.__done:
			return 100
		if self.__romTotal == 0 or not self.__started or self.__tasks == None:
			return 0
		# subtract poison pills from queue size
		qsize = self.__tasks.qsize() - self.__romProcessTotal
		if qsize <= 0:
			return 100
		return int((float(self.__romTotal - qsize) / float(self.__romTotal)) * 100.0)

	def getRomTotal(self):
		return self.__romTotal

	def getTimeRemaining(self):
		processed = self.getProcessed()
		if processed == 0 or not self.__started or self.__done or self.__tasks.qsize() == 0:
			return 0
		# now work out average time taken per ROM
		return ((time.time() - self.__startTime) / processed) * self.__tasks.qsize()

	def getTimeTaken(self):
		return self.__endTime - self.__startTime

	def getUpdated(self):
		return self.__updated

	def getUnprocessed(self):
		if not self.started or self.__done or self.__tasks == None:
			return 0
		return self.__tasks.qsize()

	def isFinished(self):
		return self.__done

	def run(self):
		logging.debug("RomScanThread.run: rom scan thread started")

		self.__done = False
		self.__started = True
		self.__startTime = time.time()
		self.__romTotal = 0
		query = QSqlQuery()

		lock = multiprocessing.Lock()
		self.__tasks = multiprocessing.JoinableQueue()
		manager = multiprocessing.Manager()
		self.__romList = manager.list()
		self.__exitEvent = multiprocessing.Event()
		results = multiprocessing.Queue()
		self.__romProcessTotal = multiprocessing.cpu_count() * 2
		logging.debug("RomScanThread.run: using %d ROM processes" % self.__romProcessTotal)
		romProcesses = [RomProcess(i, self.__tasks, results, self.__exitEvent, lock, self.__romList) for i in range(self.__romProcessTotal)]

		consoles = []

		for c in self.__consoleNames:
			urlLoaded = False
			console = self.__consoleMap[c]
			consoles.append(console)
			consoleName = console.getName()
			consoleId = console.getId()
			romExtensions = console.getExtensions()
			ignoreRoms = console.getIgnoreRomList()
			coverArtDir = console.getCoverArtDir()
			logging.debug("RomScanThread.run: pre-processing %s" % consoleName)

			query.exec_("UPDATE `game` SET `exists` = 0 WHERE `console_id` = %d;" % consoleId)
			self.__db.commit()

			files = glob.glob(os.path.join(console.getRomDir(), "*"))
			extensions = console.getExtensions()

			romFiles = []
			for f in files:
				if os.path.isfile(f) and self.__extensionOk(extensions, f):
					romFiles.append(f)

			consoleRomTotal = len(romFiles)
			logging.debug("RomScanThread: found %d ROMs for %s" % (consoleRomTotal, consoleName))
			if consoleRomTotal > 0:
				self.__romTotal += consoleRomTotal
				if self.__romScraper == "theGamesDb.net":
					# do we need to get the console's name in theGamesDb?
					if console.getGamesDbName() == "NULL":
						try:
							# get API name for this console
							logging.debug("RomScanThread.run: searching for %s's GamesDb API name..." % consoleName)
							request = urllib.request.Request("%sGetPlatform.php" % self.GAMES_DB_URL, urllib.parse.urlencode({ 'id':  console.getGamesDbId() }).encode("utf-8"), headers=self.HEADERS)
							response = urllib.request.urlopen(request, timeout=URL_TIMEOUT)
							xmlData = ElementTree.parse(response)
							consoleApiName = xmlData.find('Platform/Platform').text
							logging.debug("RomScanThread.run: %s API name is: %s" % (consoleName, consoleApiName))
							urlLoaded = True
						except Exception as e:
							logging.error(e)
							logging.error("RomScanThread.run: could not get console API name for: %s" % consoleName)

						if urlLoaded:
							console.setGamesDbName(consoleApiName)
							console.save()
						else:
							logging.warning("RomScanThread.run: could not get console API name for: %s" % consoleName)
					else:
						consoleApiName = console.getGamesDbName()

					for f in romFiles:
						self.__tasks.put(GamesDbRomTask(f, consoleId, consoleApiName, romExtensions, ignoreRoms, coverArtDir))

		self.romsFoundSignal.emit(self.__romTotal)
		logging.debug("RomScanThread.run: added %d ROMs to the process queue" % self.__romTotal)

		if self.__romTotal > 0:
			self.__db.close()

			for i in range(self.__romProcessTotal):
				self.__tasks.put(None)

			logging.debug("RomScanThread.run: poison pills added to process queue")
			logging.debug("RomScanThread.run: starting ROM processes...")
			for p in romProcesses:
				p.start()
			for p in romProcesses:
				p.join()
			logging.debug("RomScanThread.run: ROM processes joined main thread")
			self.__tasks.join()
			logging.debug("RomScanThread.run: ROM tasks joined main thread")
			logging.debug("RomScanThread.run: processing result queue...")
			while not results.empty():
				(added, updated) = results.get()
				self.__added += added
				self.__updated += updated

			logging.debug("RomScanThread.run: result queue processed")

			self.__db.open()

		# delete missing games
		for c in consoles:
			logging.debug("RomScanThread.run: deleting missing ROMs")
			query.exec_("DELETE FROM `game` WHERE `exists` = 0 AND `console_id` = %d;" % console.getId())
		self.__db.commit()

		self.__endTime = time.time()
		self.__done = True
		self.__started = False
		self.finishedSignal.emit()

		logging.debug("RomScanThread.run: finished")

	def startThread(self, consoleNames):
		logging.debug("RomScanThread.startThread: starting thread")
		self.__consoleNames = consoleNames
		self.start()

	def stop(self):
		if self.__started and not self.__done:
			logging.debug("RomScanThread.stop: stopping processes...")
			self.__exitEvent.set()
		else:
			self.__done = True
			self.finishedSignal.emit()
