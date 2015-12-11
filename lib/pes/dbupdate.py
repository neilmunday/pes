#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2015 Neil Munday (neil@mundayweb.com)
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
from pes import *
from pes.data import *
from pes.util import *
from threading import Thread
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import glob
import logging
import sqlite3
import sys
import urllib
import urllib2
import time
import multiprocessing

#
# TO DO:
#
# Report number of ROMs added / updated - add another queue to receive results?
#
	
class ConsoleTask(object):
	
	def __init__(self, rom, consoleApiName, console):
		self.rom = rom
		self.consoleApiName = consoleApiName
		self.console = console
		
	def __repr__(self):
		return self.rom
	
	def __execute(self, query, fetch=False):
		row = None
		con = None
		row = None
		with self.lock:
			try:
				con = sqlite3.connect(userPesDb, timeout=10)
				con.row_factory = sqlite3.Row
				cur = con.cursor()
				cur.execute(query)
				if fetch:
					row = cur.fetchone()
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

			row = self.__execute("SELECT `game_id`, `name`, `cover_art`, `game_path`, `api_id` FROM `games` WHERE `game_path` = \"%s\";" % rom, True)
			if row == None or (row['cover_art'] == "0" and row['api_id'] == -1) or (row['cover_art'] != "0" and not os.path.exists(row['cover_art'])):
				gameApiId = None
				bestName = name
				thumbPath = '0'
				
				# has cover art already been provided by the user or downloaded previously?
				for e in imgExtensions:
					path = cacheDir + os.sep + filename + '.' + e
					if os.path.exists(path):
						thumbPath = path
						break
					path = cacheDir + os.sep + name.replace('/', '_') + '.' + e
					if os.path.exists(path):
						thumbPath = path
						break
				
				overview = ''
				released = -1
				if consoleApiName != None:
					# now grab thumbnail
					obj = { 'name': '%s' % name, 'platform': consoleApiName }
					data = urllib.urlencode(obj)
					urlLoaded = False
					nameLower = name.lower()
					fullUrl = ''

					try:
						request = urllib2.Request("%sGetGamesList.php" % url, urllib.urlencode(obj), headers=headers)
						fullUrl = '%s?%s' % (request.get_full_url(), request.get_data())
						response = urllib2.urlopen(request)
						urlLoaded = True
					except urllib2.URLError, e:
						print e

					if urlLoaded:
						bestResultDistance = -1
						dataOk = False
						try:
							xmlData = ElementTree.parse(response)
							dataOk = True
						except ParseError, e:
							print e
						
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
					try:
						request = urllib2.Request("%sGetGame.php" % url, urllib.urlencode({"id": gameApiId}), headers=headers)
						response = urllib2.urlopen(request)
						urlLoaded = True
					except urllib2.URLError, e:
						print e

					if urlLoaded:
						xmlData = ElementTree.parse(response)
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
									response = urllib2.urlopen(request).read()
									output = open(thumbPath, 'wb')
									output.write(response)
									output.close()
									imageSaved = True
								except urllib2.URLError, e:
									print e

								if imageSaved:
									# resize the image if it is too big
									self.__scaleImage(thumbPath, name)
						else:
							# does the provided image need to be scaled?
							self.__scaleImage(thumbPath, name)
										
				else:
					gameApiId = -1

				if row == None:
					self.__execute("INSERT INTO `games`(`exists`, `console_id`, `name`, `game_path`, `api_id`, `cover_art`, `overview`, `released`, `favourite`, `last_played`, `play_count`, `size`) VALUES (1, %d, '%s', '%s', %d, '%s', '%s', %d, 0, -1, 0, %d);" % (consoleId, name.replace("'", "''"), rom.replace("'", "''"), gameApiId, thumbPath.replace("'", "''"), overview.replace("'", "''"), released, fileSize))
				elif gameApiId != -1:
					self.__execute("UPDATE `games` SET `api_id` = %d, `cover_art` = '%s', `overview` = '%s', `exists` = 1 WHERE `game_id` = %d;" % (gameApiId, thumbPath.replace("'", "''"), overview.replace("'", "''"), row['game_id']))
				else:
					self.__execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])
			else:
				self.__execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])
				
	@staticmethod
	def __scaleImage(path, name):
		img = Image.open(path)
		width, height = img.size
		ratio = min(float(400.0 / width), float(400.0 / height))
		newWidth = width * ratio
		newHeight = height * ratio
		if width > newWidth or height > newHeight:
			# scale image
			img.thumbnail((newWidth, newHeight), Image.ANTIALIAS)
			img.save(path)
			
	def setLock(self, lock):
		self.lock = lock
			
class Consumer(multiprocessing.Process):
	def __init__(self, taskQueue, lock):
		multiprocessing.Process.__init__(self)
		self.taskQueue = taskQueue
		self.lock = lock
		
	def run(self):
		while True:
			task = self.taskQueue.get()
			if task is None:
				logging.debug("%s: exiting..." % self.name)
				self.taskQueue.task_done()
				return
			task.setLock(self.lock)
			task.run()
			self.taskQueue.task_done()
		return
	
class UpdateDbThread(Thread):
	
	def __init__(self, consoles):
		Thread.__init__(self)
		self.done =  False
		self.started = False
		self.__tasks = None
		self.consoles = consoles
		self.progress = 0
		self.status = ""
		self.romTotal = 0
		
	@staticmethod
	def __extensionOk(extensions, filename):
		for e in extensions:
			if filename.endswith(e):
				return True
		return False
	
	def run(self):
		lock = multiprocessing.Lock()
		self.__tasks = multiprocessing.JoinableQueue()
		self.started = True
		self.num_consumers = multiprocessing.cpu_count() * 2
		logging.debug("UpdateDbThread.run: creating %d consumers" % self.num_consumers)
		consumers = [Consumer(self.__tasks, lock) for i in xrange(self.num_consumers)]
		for w in consumers:
			w.start()
		
		url = 'http://thegamesdb.net/api/'
		headers = {'User-Agent': 'PES Scraper'}
		
		con = None
		cur = None
		
		try:
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute("UPDATE `games` SET `exists` = 0")
			con.commit()
		except sqlite3.Error, e:
			print e
			if con:
				con.rollback()
			sys.exit(1)
		finally:
			if con:
				con.close()
		
		logging.debug("UpdateDbThread.run: getting console API names...")
		for c in self.consoles:
			consoleName = c.getName()
			consoleId = c.getId()
			cacheDir = c.getImgCacheDir()

			urlLoaded = False
			consoleApiName = None

			try:
				# get API name for this console
				request = urllib2.Request("%sGetPlatform.php" % url, urllib.urlencode({ 'id':  c.getApiId() }), headers=headers)
				response = urllib2.urlopen(request)
				urlLoaded = True
				xmlData = ElementTree.parse(response)
				consoleApiName = xmlData.find('Platform/Platform').text
			except urllib2.URLError, e:
				print e
				
			files = glob.glob("%s%s*" % (c.getRomDir(), os.sep))
			fileTotal = len(files)
			extensions = c.getExtensions()

			for f in files:
				if os.path.isfile(f) and self.__extensionOk(extensions, f):
					self.__tasks.put(ConsoleTask(f, consoleApiName, c))
					self.romTotal += 1
					
		logging.debug("UpdateDbThread.run: added %d roms to the queue" % self.romTotal)
		
		for i in xrange(self.num_consumers):
			self.__tasks.put(None)
			
		self.__tasks.join()
		
		logging.debug("UpdateDbThread.run: processes finished")
		
		try:
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute("DELETE FROM `games` WHERE `exists` = 0")
			con.commit()
		except sqlite3.Error, e:
			print e
			if con:
				con.rollback()
		finally:
			if con:
				con.close()
				
		self.done = True
		self.progress = 100
		
		logging.debug("UpdateDbThread.run: exiting")
		
	def getProcessed(self):
		return self.romTotal - self.__tasks.qsize()
		
	def getProgress(self):
		if self.romTotal == 0:
			return 0
		if self.done:
			return 100
		if not self.started:
			return 0
		return int((float(self.romTotal - self.__tasks.qsize()) / float(self.romTotal)) * 100.0)
		
	def stop(self):
		if self.started:
			logging.debug("UpdateDbThread.stop: stoppping processes...")
			while not self.__tasks.empty():
				self.__tasks.get()
				self.__tasks.task_done()
			for i in xrange(self.num_consumers):
				self.__tasks.put(None)
			logging.debug("UpdateDbThread.stop: poison pills in place")
		self.progress = 100
		self.done = True
		self.started = False
		
	def getUnprocessed(self):
		return self.__tasks.qsize()
