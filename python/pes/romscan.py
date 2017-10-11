import glob
import logging
import multiprocessing
import os
import sys
import time
import urllib

from PIL import Image

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtSql import QSqlDatabase, QSqlQuery

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, ParseError, SubElement

URL_TIMEOUT = 30
logging.getLogger("PIL").setLevel(logging.WARNING)

class RomTask(object):
	
	SCALE_WIDTH = 200.0
	
	def __init__(self, rom, consoleName, consoleApiName):
		self.__rom = rom
		self.__consoleName = consoleName
		self.__consoleApiName = consoleApiName
		
	def __doQuery(self, query):
		with self.__lock:
			db = QSqlDatabase.addDatabase("QSQLITE")
			db.setDatabaseName(pes.userDb)
			db.open()
			query = QSqlQuery()
			query.exec_(q)
			db.commit()
			db.close()
		return query
	
	def run(self):
		filename = os.path.split(self.__rom)[1]
		logging.debug("RomTask.run: processing -> %s" % filename)
		
		added = 1
		updated = 0
		
		time.sleep(0.01)
		
		return (added, updated)
	
	def setLock(self, lock):
		self.__lock = lock

class RomProcess(multiprocessing.Process):
	
	def __init__(self, taskQueue, resultQueue, exitEvent, lock):
		super(RomProcess, self).__init__()
		self.__taskQueue = taskQueue
		self.__resultQueue = resultQueue
		self.__exitEvent = exitEvent
		self.__lock = lock
		
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
				result = task.run()
				added += result[0]
				updated += result[1]
				self.__taskQueue.task_done()
		self.__resultQueue.put((added, updated))
		self.__resultQueue.close()

class RomScanThread(QThread):
	
	GAMES_DB_URL = 'http://thegamesdb.net/api/'
	HEADERS = {'User-Agent': 'PES Scraper'}
	
	romsFoundSignal = pyqtSignal(int)
	
	def __init__(self, db, consoleNames, consoleMap):
		"""
		@param 	consoleNames	list of console names to scan
		@param	consoleMap		dictionary of console objects
		"""
		super(RomScanThread, self).__init__(None)
		self.__progress = 0
		self.__romTotal = 0
		self.__db = db
		self.__consoleNames = consoleNames
		self.__consoleMap = consoleMap
		self.__done = False
		self.__started = False
		self.__startTime = 0
		self.__endTime = 0
		self.__added = 0
		self.__updated = 0
		self.__tasks = None
		
	@staticmethod
	def __extensionOk(extensions, filename):
		for e in extensions:
			if filename.endswith(e):
				return True
		return False
	
	def getAdded(self):
		return self.__added
	
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
		self.__exitEvent = multiprocessing.Event()
		results = multiprocessing.Queue()
		self.__romProcessTotal = multiprocessing.cpu_count() * 2
		logging.debug("RomScanThread.run: using %d ROM processes" % self.__romProcessTotal)
		romProcesses = [RomProcess(self.__tasks, results, self.__exitEvent, lock) for i in range(self.__romProcessTotal)]
		
		for c in self.__consoleNames:
			urlLoaded = False
			console = self.__consoleMap[c]
			consoleName = console.getName()
			consoleId = console.getId()
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
						
				consoleApiName = console.getGamesDbName()
						
				for f in romFiles:
					self.__tasks.put(RomTask(f, consoleName, consoleApiName))
		
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
			
		self.__endTime = time.time()
		self.__done = True
		self.__started = False
		
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
