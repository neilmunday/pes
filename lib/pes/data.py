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

import logging
import sqlite3
import os
import sys

class Record(object):

	def __init__(self, db, table, fields, keyField, keyValue = None, autoIncrement = True, loadData = True):
		self.__db = db
		self.__autoIncrement = autoIncrement
		self.__table = table
		self.__fields = fields
		self.__keyField = keyField
		self.__keyValue = keyValue
		self.__properties = {}
		self.__properties[self.__keyField] = keyValue
		self.__isDirty = False
		self.__con = None
		self.__dirtyFields = []

		if loadData:
			self.refresh()
			self.__dataLoaded = True
		else:
			self.__dataLoaded = False

	def connect(self):
		if self.__con:
			return self.__con

		self.__con = sqlite3.connect(self.__db)
		self.__con.row_factory = sqlite3.Row
		self.__cur = self.__con.cursor()
		#logging.debug("connected to %s database, using table %s" % (self.__db, self.__table))
		return self.__con

	@staticmethod
	def convertValue(v):
		isNumeric = False
		try:
			float(v)
			isNumeric = True
		except ValueError:
			pass

		if not isNumeric:
			return '"%s"' % v
		return str(v)

	def dataLoaded(self):
		return self.__dataLoaded
		
	def disconnect(self):
		if self.__con:
			self.__con.close()
		self.__con = None
		#logging.debug("disconnected from %s database, using table %s" % (self.__db, self.__table))

	def doQuery(self, query):
		if not self.__con:
			raise sqlite3.Error('Database %s not connected' % self.__db)
		logging.debug('executing query: %s' % query)
		self.__cur.execute(query)
		return self.__cur

	def __getFieldsQuery(self):
		i = 0
		total = len(self.__fields)
		query = ''
		for f in self.__fields:
			query += '`%s`' % f
			if i < total - 1:
				query += ','
			i += 1
		return query

	def getDb(self):
		return self.__db

	def getId(self):
		return self.__properties[self.__keyField]

	def getProperty(self, field):
		if self.__dataLoaded:
			return self.__properties[field]
		return None

	def __getWritableFields(self):
		l = []
		for f in self.__fields:
			if f != self.__keyField:
				l.append(f)

		return l

	def isDirty(self):
		return len(self.__dirtyFields) > 0

	def isNew(self):
		return self.__isNew

	def refresh(self):
		self.connect()
		if not self.__con:
			raise sqlite3.Error('Database %s not connected' % self.__db)

		if self.__properties[self.__keyField] != None:
			self.doQuery('SELECT %s FROM `%s` WHERE `%s` = %d;' % (self.__getFieldsQuery(), self.__table, self.__keyField, self.__properties[self.__keyField]))
			row = self.__cur.fetchone()
			if row == None:
				#raise sqlite3.Error('No record found for field "%s" in table "%s"' % (self.__primaryKey, self.__table)
				self.__isNew = True
				self.__dirtyFields = self.__getWritableFields()
			else:
				for f in self.__fields:
					self.__properties[f] = row[f]
				self.__isNew = False
				self._dirtyFields = []
			self.__dataLoaded = True
		else:
			self.__isNew = True
			self.__dataLoaded = False
		self.disconnect()

	def save(self):
		self.connect()
		if not self.__con:
			raise sqlite3.Error('Database %s not connected' % self.__db)

		query = ''
		if self.__isNew:
			i = 0
			writableFields = None
			if self.__autoIncrement:
				writableFields = self.__getWritableFields()
			else:
				writableFields = self.__fields
			total = len(writableFields)
			query = 'INSERT INTO `%s` (' % self.__table
			endQuery = ''
			for f in writableFields:
				query += '`%s`' % f
				endQuery += self.convertValue(self.__properties[f])
				if i < total - 1:
					query += ','
					endQuery += ','
				i += 1

			query += ') VALUES (%s);' % endQuery
				
		else:
			i = 0
			total = len(self.__dirtyFields)
			query = 'UPDATE `%s` SET ' % self.__table
			for f in self.__dirtyFields:
				query += '`%s` = %s' % (f, self.convertValue(self.__properties[f]))
				if i < total - 1:
					query += ','
				i += 1
			query += ' WHERE `%s` = %d;' % (self.__keyField, self.__properties[self.__keyField])

		self.doQuery(query)
		self.__con.commit()
		self.disconnect()

		if self.__isNew:
			self.__isNew = False
			self.__properties[self.__keyField] = self.__cur.lastrowid
		self.__dirtyFields = []

	def setProperty(self, field, value):
		self.__properties[field] = value
		if not field in self.__dirtyFields:
			self.__dirtyFields.append(field)

class Console(Record):

	def __init__(self, name, consoleId, apiId, extensions, romDir, command, db, consoleImg, noCoverArtImg, imgCacheDir, emulator):
		super(Console, self).__init__(db, 'consoles', ['console_id', 'name'], 'console_id', consoleId, True)
		self.setProperty('name', name)
		self.__apiId = apiId
		self.__extensions = extensions
		self.__romDir = romDir
		self.__consoleImg = consoleImg
		self.__noCoverArtImg = noCoverArtImg
		self.__emulator = emulator
		self.__games = None
		self.__command = command
		self.__imgCacheDir = imgCacheDir
		self.__gameTotal = None
		self.__ignoreRoms = []
		self.__recentlyAdded = None
		self.__recentlyPlayed = None
		self.__mostPlayed = None
		
	def addIgnoreRom(self, rom):
		if rom not in self.__ignoreRoms:
			self.__ignoreRoms.append(rom)
		
	def getApiId(self):
		return self.__apiId

	def getCommand(self, game):
		return self.__command.replace('%%GAME%%', "\"%s\"" % game.getPath())

	def getDir(self):
		return self.__dir

	def getEmulator(self):
		return self.__emulator
		
	def getGames(self, limit=0, count=0, refeshGames=False):
		if self.__games == None or refeshGames:
			self.connect()
			query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d ORDER BY UPPER(`name`)' % self.getId()
			if limit >= 0 and count > 0:
				query += ' LIMIT %d, %d' % (limit, count)
			query += ';'
			cur = self.doQuery(query)
			self.__games = []
			while True:
				row = cur.fetchone()
				if row == None:
					break
				self.__games.append(Game(row['game_id'], self.getDb(), self, False))
			self.disconnect()
		return self.__games

	def getGameTotal(self):
		if self.__gameTotal == None:
			self.connect()
			cur = self.doQuery('SELECT COUNT(`game_id`) AS `total` FROM `games` WHERE `console_id` = %d;' % self.getId())
			row = cur.fetchone()
			self.disconnect()
			self.__gameTotal = row['total']	
		return self.__gameTotal

	def getExtensions(self):
		return self.__extensions
		
	def getFavouriteTotal(self):
		self.connect()
		cur = self.doQuery('SELECT COUNT(`game_id`) AS `total` FROM `games` WHERE `favourite` = 1 AND `console_id` = %d;' % self.getId())
		row = cur.fetchone()
		self.disconnect()
		return row['total']	

	def getImgCacheDir(self):
		return self.__imgCacheDir
	
	def getImg(self):
		return self.__consoleImg

	def getName(self):
		return self.getProperty('name')

	def getNoCoverArtImg(self):
		return self.__noCoverArtImg
	
	def getMostPlayedGames(self, limit=10):
		if self.__mostPlayed == None:
			self.connect()
			self.__mostPlayed = []
			cur = self.doQuery('SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `play_count` > 0 ORDER BY `play_count` DESC LIMIT 0,%d;' % (self.getId(), limit))
			while True:
				row = cur.fetchone()
				if row == None:
					break
				self.__mostPlayed.append(Game(row['game_id'], self.getDb(), self))
			self.disconnect()
		return self.__mostPlayed
	
	def getRecentlyAddedGames(self, limit=10):
		if self.__recentlyAdded == None:
			self.connect()
			self.__recentlyAdded = []
			cur = self.doQuery('SELECT `game_id` FROM `games` WHERE `console_id` = %d ORDER BY `added` DESC LIMIT 0,%d;' % (self.getId(), limit))
			while True:
				row = cur.fetchone()
				if row == None:
					break
				self.__recentlyAdded.append(Game(row['game_id'], self.getDb(), self))
			self.disconnect()
		return self.__recentlyAdded
	
	def getRecentlyPlayedGames(self, limit=10):
		if self.__recentlyPlayed == None:
			self.connect()
			self.__recentlyPlayed = []
			cur = self.doQuery('SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `last_played` > -1 ORDER BY `last_played` DESC LIMIT 0,%d;' % (self.getId(), limit))
			while True:
				row = cur.fetchone()
				if row == None:
					break
				self.__recentlyPlayed.append(Game(row['game_id'], self.getDb(), self))
			self.disconnect()
		return self.__recentlyPlayed

	def getRomDir(self):
		return self.__romDir
		
	def ignoreRom(self, rom):
		return rom in self.__ignoreRoms
	
	def refresh(self):
		super(Console, self).refresh()
		self.__mostPlayed = None
		self.__recentlyAdded = None
		self.__recentlyPlayed = None
		self.__gameTotal = None
		self.__games = None

class Game(Record):

	def __init__(self, gameId, db, console=None, loadData=True):
		super(Game, self).__init__(db, 'games', ['api_id', 'exists', 'console_id', 'name', 'cover_art', 'game_path', 'overview', 'released', 'last_played', 'favourite', 'play_count', 'size'], 'game_id', int(gameId), True, loadData)
		self.__console = console

	def getCommand(self):
		return self.__console.getCommand(self)

	def getConsole(self):
		return self.__console

	def getConsoleId(self):
		return self.getProperty('console_id')

	def getCoverArt(self):
		coverArt = self.getProperty('cover_art')
		if coverArt == '0':
			return None
		if not os.path.exists(coverArt):
			logging.warning('cover art %s does not exist!' % coverArt)
			return None
		return coverArt

	def getLastPlayed(self, fmt=None):
		timestamp = int(self.getProperty('last_played'))
		if timestamp == -1:
			return None
		if fmt == None:
			return timestamp
		return datetime.fromtimestamp(timestamp).strftime(fmt)

	def getName(self):
		return self.getProperty('name')

	def getOverview(self):
		return self.getProperty('overview')

	def getPath(self):
		return self.getProperty('game_path')

	def getReleased(self, fmt=None):
		timestamp = self.getProperty('released')
		if fmt == None:
			return timestamp
		return datetime.fromtimestamp(timestamp).strftime(fmt)

	def getPlayCount(self):
		return self.getProperty('play_count')

	def getSize(self):
		return self.getProperty('size')

	def isFavourite(self, yesNoMap=None):
		fav = self.getProperty('favourite') == 1
		if yesNoMap == None:
			return fav
		if fav:
			return yesNoMap[0]
		return yesNoMap[1]

	def setConsoleId(self, consoleId):
		self.setProperty('console_id', consoleId)

	def setCoverArt(self, path):
		self.setProperty('game_path', path)

	def setFavourite(self, fav):
		if fav:
			self.setProperty('favourite', 1)
		else:
			self.setProperty('favourite', 0)

	def setLastPlayed(self, date=None):
		if date == None:
			# use current date/time
			date = int(time.time())
		self.setProperty('last_played', date)

	def setName(self, name):
		self.setProperty('name', name)

	def setOverview(self, overview):
		self.setProperty('overview', overview)

	def setReleased(self, released):
		self.setProperty('released', released)

	def setPath(self, path):
		self.setProperty('game_path', path)

	def setPlayCount(self, x=None):
		if x == None:
			x = self.getPlayCount() + 1
		self.setProperty('play_count', x)

	def setSize(self, s):
		self.setProperty('size')