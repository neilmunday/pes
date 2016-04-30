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

from PIL import Image
from datetime import datetime
from time import sleep
from pes import *
from pes.data import *
from pes.util import *
from subprocess import Popen, PIPE
from threading import Thread
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
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

URL_TIMEOUT = 10
	
class ConsoleTask(object):
	
	SCALE_WIDTH = 200.0
	
	def __init__(self, rom, consoleApiName, console):
		self.rom = rom
		self.consoleApiName = consoleApiName
		self.console = console
		self.consoleName = console.getName()
		
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
		url = 'http://thegamesdb.net/api/'
		headers = {'User-Agent': 'PES Scraper'}
		imgExtensions = ['jpg', 'jpeg', 'png', 'gif']
		
		rom = self.rom
		consoleApiName = self.consoleApiName
		console = self.console
		cacheDir = console.getImgCacheDir()
		consoleId = self.console.getId()
		
		added = 0
		updated = 0
		
		filename = os.path.split(rom)[1]
		if not console.ignoreRom(filename):
			logging.debug("ConsoleTask: processing -> %s" % filename)
			name = filename
			fileSize = os.path.getsize(rom)
			for e in console.getExtensions():
				name = name.replace(e, '')
				
			row = self.__execute("SELECT `full_name` FROM `games_catalogue` WHERE `short_name` = \"%s\"" % name, True)
			if row:
				name = row['full_name']
				
			row = self.__execute("SELECT `game_id`, `name`, `cover_art`, `game_path`, `thegamesdb_id` FROM `games` WHERE `game_path` = \"%s\";" % rom, True)
			if row == None or (row['cover_art'] == "0" and row['thegamesdb_id'] == -1) or (row['cover_art'] != "0" and not os.path.exists(row['cover_art'])):
				gameApiId = None
				bestName = name
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
						logging.warning("ConsoleTask: %s is not a valid image, it will be deleted")
						os.remove(thumbPath)
						thumbPath = '0'
				
				overview = ''
				released = -1
				if consoleApiName != None:
					# now grab thumbnail
					obj = { 'name': '%s' % name, 'platform': consoleApiName }
					urlLoaded = False
					nameLower = name.lower()

					try:
						request = urllib2.Request("%sGetGamesList.php" % url, urllib.urlencode(obj), headers=headers)
						response = urllib2.urlopen(request, timeout=URL_TIMEOUT)
						urlLoaded = True
					#except (urllib2.HTTPError, urllib2.URLError) as e:
					except Exception as e:
						logging.error(e)
						logging.error("Failed to process: %s" % filename)

					if urlLoaded:
						bestResultDistance = -1
						dataOk = False
						try:
							xmlData = ElementTree.parse(response)
							dataOk = True
						except ParseError, e:
							logging.error(e)
							logging.error("Failed response for console %s was: %s" % (name, response))
						
						if dataOk:
							for x in xmlData.findall("Game"):
								xname = x.find("GameTitle").text.encode('ascii', 'ignore')
								xid = int(x.find("id").text)

								if xname.lower() == nameLower:
									gameApiId = xid
									break

								stringMatcher = StringMatcher(str(nameLower), xname.lower())
								distance = stringMatcher.distance()

								if bestResultDistance == -1 or distance < bestResultDistance:
									bestResultDistance = distance
									bestName = xname
									gameApiId = xid

				if gameApiId != None:
					urlLoaded = False
					gameUrl = "%sGetGame.php" % url
					try:
						request = urllib2.Request(gameUrl, urllib.urlencode({"id": gameApiId}), headers=headers)
						response = urllib2.urlopen(request, timeout=URL_TIMEOUT)
						urlLoaded = True
					#except (urllib2.HTTPError, urllib2.URLError) as e:
					except Exception as e:
						logging.error(e)
						logging.error("Failed URL was: %s" % gameUrl)

					if urlLoaded:
						dataOk = False
						try:
							xmlData = ElementTree.parse(response)
							dataOk = True
						except ParseError, e:
							logging.error(e)
							logging.error("Failed URL was: %s" % gameUrl)
							logging.error("Failed content was: %s" % response)
							
						if dataOk:
							overviewElement = xmlData.find("Game/Overview")
							if overviewElement != None:
								overview = overviewElement.text.encode('ascii', 'ignore')
							releasedElement = xmlData.find("Game/ReleaseDate")
							if releasedElement != None:
								released = releasedElement.text.encode('ascii', 'ignore')
								# convert to Unix time stamp
								try:
									released = int(time.mktime(datetime.strptime(released, "%m/%d/%Y").timetuple()))
								except ValueError, e:
									# thrown if date is not valid
									released = -1
									
							if thumbPath == "0":
								boxartElement = xmlData.find("Game/Images/boxart[@side='front']")
								if boxartElement != None:
									imageSaved = False
									try:
										imgUrl = "http://thegamesdb.net/banners/%s" % boxartElement.text
										extension = imgUrl[imgUrl.rfind('.'):]
										thumbPath =  console.getImgCacheDir() + os.sep + name.replace('/', '_') + extension
										request = urllib2.Request(imgUrl, headers=headers)
										response = urllib2.urlopen(request, timeout=URL_TIMEOUT).read()
										output = open(thumbPath, 'wb')
										output.write(response)
										output.close()
										imageSaved = True
									#except (urllib2.HTTPError, urllib2.URLError) as e:
									except Exception as e:
										logging.error(e)
										logging.error("Failed to process url: %s" % imgUrl)

									if imageSaved:
										# resize the image if it is too big
										if not self.__scaleImage(thumbPath, name):
											thumbPath = '0'
							else:
								# does the provided image need to be scaled?
								if not self.__scaleImage(thumbPath, name):
									thumbPath = '0'
						else:
							if thumbPath != "0":
								# does the provided image need to be scaled?
								if not self.__scaleImage(thumbPath, name):
									thumbPath = '0'
				else:
					gameApiId = -1

				if row == None:
					rasum = "NULL"
					achievementApiId = -1
					if self.console.getAchievementApiId() != "NULL":
						# work out rasum (if applicable)
						if self.consoleName == "MegaDrive" or self.consoleName == "Genesis":
							command = "%s -t genesis \"%s\"" % (rasumExe, rom)
						elif self.consoleName == "NES":
							command = "%s -t nes \"%s\"" % (rasumExe, rom)
						elif self.consoleName == "SNES":
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
					
					self.__execute("INSERT INTO `games`(`exists`, `console_id`, `name`, `game_path`, `thegamesdb_id`, `cover_art`, `overview`, `released`, `added`, `favourite`, `last_played`, `play_count`, `size`, `rasum`, `achievement_api_id`) VALUES (1, %d, '%s', '%s', %d, '%s', '%s', %d, %d, 0, -1, 0, %d, '%s', %d);" % (consoleId, name.replace("'", "''"), rom.replace("'", "''"), gameApiId, thumbPath.replace("'", "''"), overview.replace("'", "''"), released, time.time(), fileSize, rasum, achievementApiId))
					added += 1
				elif gameApiId != -1:
					self.__execute("UPDATE `games` SET `thegamesdb_id` = %d, `cover_art` = '%s', `overview` = '%s', `exists` = 1 WHERE `game_id` = %d;" % (gameApiId, thumbPath.replace("'", "''"), overview.replace("'", "''"), row['game_id']))
					updated += 1
				else:
					self.__execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])
			else:
				self.__execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])
				
		return (added, updated)
				
	@staticmethod
	def __scaleImage(path, name):
		try:
			img = Image.open(path)
			width, height = img.size
			scaleWidth = ConsoleTask.SCALE_WIDTH
			ratio = min(float(scaleWidth / width), float(scaleWidth / height))
			newWidth = width * ratio
			newHeight = height * ratio
			if width > newWidth or height > newHeight:
				# scale image
				img.thumbnail((newWidth, newHeight), Image.ANTIALIAS)
				img.save(path)
			img.close()
		except IOError as e:
			logging.error("Failed to scale: %s" % path)
			return False
		return True
			
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
				self.taskQueue.task_done()
				self.resultQueue.put(result)
		self.resultQueue.close()
		return
	
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
		#for w in consumers:
		#	w.start()
		
		url = 'http://thegamesdb.net/api/'
		headers = {'User-Agent': 'PES Scraper'}
		
		con = None
		cur = None
		
		for c in self.consoles:
			consoleName = c.getName()
			consoleId = c.getId()
			cacheDir = c.getImgCacheDir()

			urlLoaded = False
			consoleApiName = None
			
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
				try:
					# get API name for this console
					request = urllib2.Request("%sGetPlatform.php" % url, urllib.urlencode({ 'id':  c.getTheGamesDbApiId() }), headers=headers)
					response = urllib2.urlopen(request, timeout=URL_TIMEOUT)
					urlLoaded = True
					xmlData = ElementTree.parse(response)
					consoleApiName = xmlData.find('Platform/Platform').text
				#except (urllib2.HTTPError, urllib2.URLError) as e:
				except Exception as e:
					logging.error(e)
					logging.error("UpdateDbThread.run: not get console API name for: %s" % consoleName)
				
				if not urlLoaded:
					logging.warning("UpdateDbThread.run: Could not get console API name for: %s" % consoleName)
					
				for f in romFiles:
					self.__tasks.put(ConsoleTask(f, consoleApiName, c))
					
		logging.debug("UpdateDbThread.run: added %d ROMs to the queue" % self.romTotal)
		
		for i in xrange(self.consumerTotal):
			self.__tasks.put(None)
			
		logging.debug("UpdateDbThread.run: added poison pills")
		self.__queueSetUp = True
		
		for w in consumers:
			w.start()
		
		for w in consumers:
			w.join()
		
		self.__tasks.join()
		
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
