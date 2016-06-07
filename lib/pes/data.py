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

from datetime import datetime
from pes import *
import logging
import re
import sqlite3
import os
import sys
import time

def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None

class Record(object):

	def __init__(self, db, table, fields, keyField, keyValue = None, autoIncrement = True, loadData = True, row = None):
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
			if row != None and self.__keyValue != None:
				# check all our fields are present in the record
				keys = row.keys()
				for f in self.__fields:
					if f not in keys:
						raise Exception("Record.init: field \"%s\" not found in row for a \"%s\" record" % (f, self.__table))
					self.__properties[f] = row[f]
				print self.__properties
				self.__isNew = False
				self.__dataLoaded = True
			else:
				self.__dataLoaded = False

	def connect(self):
		if self.__con:
			return self.__con

		self.__con = sqlite3.connect(self.__db)
		self.__con.create_function("REGEXP", 2, regexp)
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
		logging.debug('Record.doQuery: executing query: %s' % query)
		self.__cur.execute(query)
		return self.__cur

	def getDb(self):
		return self.__db
	
	def getFieldsAsSql(self, includeTableName=False):
		if not includeTableName:
			return ','.join("`%s`" % f for f in self.__fields)
		fields = []
		for f in self.__fields:
			fields.append("`%s`.`%s`" % (self.__table, f))
		return ','.join(fields)

	def getId(self):
		return self.__properties[self.__keyField]

	def getProperty(self, field):
		if self.__dataLoaded:
			if field in self.__properties:
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
			self.doQuery('SELECT %s FROM `%s` WHERE `%s` = %d;' % (','.join("`%s`" % f for f in self.__fields), self.__table, self.__keyField, self.__properties[self.__keyField]))
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
				if not f in self.__properties:
					self.__properties[f] = "NULL"
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
			
class AchievementUser(Record):
	
	def __init__(self, db, userId):
		super(AchievementUser, self).__init__(db, 'achievements_user', ['user_id', 'user_name', 'rank', 'total_points', 'total_truepoints'], 'user_id', userId)
		
	def getGame(self, gameId):
		self.connect()
		cur = self.doQuery('SELECT (SELECT COUNT(*) FROM `achievements_earned`, `achievements_badges` WHERE `achievements_badges`.`game_id` = %d AND `achievements_earned`.`user_id` = %d AND `achievements_badges`.`badge_id` = `achievements_earned`.`badge_id`) AS `totalEarned`, (SELECT SUM(`points`) FROM `achievements_earned`, `achievements_badges` WHERE `achievements_badges`.`game_id` = %d AND `achievements_earned`.`user_id` = %d AND `achievements_badges`.`badge_id` = `achievements_earned`.`badge_id`) AS `totalPoints` FROM `achievements_games` WHERE `achievements_games`.`game_id` = %d ;' % (gameId, self.getId(), gameId, self.getId(), gameId))
		row = cur.fetchone()
		if row == None:
			self.disconnect()
			return None
		totalPoints = 0
		if row['totalPoints']:
			totalPoints = int(row['totalPoints'])
		self.disconnect()
		return AchievementGame(self.getDb(), self.getId(), gameId, int(row['totalEarned']), totalPoints)
	
	def getGames(self):
		self.connect()
		cur = self.doQuery('SELECT `achievements_games`.`game_id`, (SELECT COUNT(*) FROM `achievements_earned`, `achievements_badges` WHERE `achievements_badges`.`game_id` = `achievements_games`.`game_id` AND `achievements_earned`.`user_id` = %d AND `achievements_badges`.`badge_id` = `achievements_earned`.`badge_id`) AS `totalEarned`, (SELECT SUM(`points`) FROM `achievements_earned`, `achievements_badges` WHERE `achievements_badges`.`game_id` = `achievements_games`.`game_id` AND `achievements_earned`.`user_id` = %d AND `achievements_badges`.`badge_id` = `achievements_earned`.`badge_id`) AS `totalPoints` FROM `achievements_games`;' % (self.getId(), self.getId()))
		games = []
		while True:
			row = cur.fetchone()
			if row == None:
				break
			totalPoints = 0
			if row['totalPoints']:
				totalPoints = int(row['totalPoints'])
			games.append(AchievementGame(self.getDb(), self.getId(), int(row['game_id']), int(row['totalEarned']), totalPoints))
		self.disconnect()
		return games
	
	def getName(self):
		return self.getProperty('user_name')
	
	def getRank(self):
		return int(self.getProperty('rank'))
	
	def getRecentBadges(self, count):
		self.connect()
		cur = self.doQuery('SELECT `achievements_badges`.`badge_id`, `date_earned` FROM `achievements_earned`, `achievements_badges` WHERE `achievements_earned`.`badge_id` = `achievements_badges`.`badge_id` AND `user_id` = %d ORDER BY `date_earned` DESC LIMIT 0,%d;' % (self.getProperty('user_id'), count))
		badges = []
		while True:
			row = cur.fetchone()
			if row == None:
				break
			badges.append(Badge(self.getDb(), int(row['badge_id']), int(row['date_earned'])))
		self.disconnect()
		return badges
	
	def getTotalPoints(self):
		return int(self.getProperty('total_points'))
	
	def getTotalTruePoints(self):
		return int(self.getProperty('total_truepoints'))
	
	def setName(self, name):
		self.setProperty('user_name', name)
		
	def setTotalPoints(self, points):
		self.setProperty('total_points', int(points))
		
	def setTotalTruePoints(self, points):
		self.setProperty('total_truepoints', int(points))
		
class AchievementGame(Record):
	
	def __init__(self, db, userId, gameId, userEarnedTotal=0, userPointsTotal=0):
		super(AchievementGame, self).__init__(db, 'achievements_games', ['game_id', 'console_id', 'achievement_total', 'score_total'], 'game_id', gameId)
		self.__userEarnedTotal = userEarnedTotal
		self.__userPointsTotal = userPointsTotal
		self.__consoleName = None
		self.__userId = userId
		self.__badges = None
		self.__gameId = None
		self.__name = None
		
	def getAchievementTotal(self):
		return self.getProperty('achievement_total')
	
	def getConsoleId(self):
		return self.getProperty('console_id')
	
	def getConsoleName(self):
		if not self.__consoleName:
			self.connect()
			cur = self.doQuery('SELECT `name` FROM `consoles` WHERE `achievement_api_id` = %s' % self.getProperty('console_id'))
			if cur.rowcount == 0:
				raise Exception("Could not find corresponding console for game %s" % self.getId())
			row = cur.fetchone()
			self.__consoleName = row['name'] 
			self.disconnect()
		return self.__consoleName
	
	def getBadges(self):
		if self.__badges == None:
			self.connect()
			cur = self.doQuery('SELECT `badge_id`, (SELECT `date_earned` FROM `achievements_earned` WHERE `achievements_badges`.`badge_id` = `achievements_earned`.`badge_id` AND `achievements_earned`.`user_id` = %d) As `date_earned` FROM `achievements_badges` WHERE `game_id` = %d ORDER BY `title`;' % (self.__userId, self.getId()))
			self.__badges = []
			while True:
				row = cur.fetchone()
				if row == None:
					break
				if row['date_earned']:
					self.__badges.append(Badge(self.getDb(), int(row['badge_id']), int(row['date_earned'])))
				else:
					self.__badges.append(Badge(self.getDb(), int(row['badge_id']), None))
			self.disconnect()
		return self.__badges
	
	def getGameId(self):
		# attempt to find the corresponding game
		if self.__gameId == None:
			self.connect()
			name = self.getName().replace("'", "''")
			cur = self.doQuery('SELECT `game_id` FROM `games`, `consoles` WHERE `games`.`console_id` = `consoles`.`console_id` AND `consoles`.`achievement_api_id` = "%d" AND `games`.`achievement_api_id` = %d LIMIT 0,1;' % (self.getConsoleId(), self.getId()))
			row = cur.fetchone()
			if row == None:
				return None
			self.__gameId = int(row['game_id'])
			self.disconnect()
		return self.__gameId
		
	def getName(self):
		if self.__name == None:
			self.connect()
			cur = self.doQuery('SELECT `name` FROM `games` WHERE `achievement_api_id` = %d;' % self.getId())
			row = cur.fetchone()
			if row == None:
				return None
			self.disconnect()
			self.__name = row['name']
		return self.__name
	
	def getPercentComplete(self):
		return (float(self.__userEarnedTotal) / float(self.getAchievementTotal())) * 100.0
	
	def getScoreTotal(self):
		return self.getProperty('score_total')
	
	def getUserEarnedTotal(self):
		return self.__userEarnedTotal
	
	def getUserPointsTotal(self):
		return self.__userPointsTotal
		
class Badge(Record):
	def __init__(self, db, badgeId, dateEarned=None):
		super(Badge, self).__init__(db, 'achievements_badges', ['badge_id', 'title', 'game_id', 'description', 'points', 'badge_path', 'badge_locked_path'], 'badge_id', badgeId, True)
		self.__dateEarned = dateEarned
		if self.__dateEarned:
			self.__isLocked = False
		else:
			self.__isLocked = True
		logging.debug("Badge.init: created badge with title: \"%s\"" % self.getTitle())
		
	def getDateEarned(self, fmt=None):
		if self.__isLocked:
			return None
		timestamp = int(self.__dateEarned)
		if timestamp == -1:
			return None
		if fmt == None:
			return timestamp
		return datetime.fromtimestamp(timestamp).strftime(fmt)
		
	def getDescription(self):
		return self.getProperty('description')
	
	def getGameId(self):
		return self.getProperty('game_id')
	
	def getPath(self):
		if self.__isLocked:
			return self.getProperty('badge_locked_path')
		return self.getProperty('badge_path')
	
	def getPoints(self):
		return self.getProperty('points')
		
	def getTitle(self):
		return self.getProperty('title')
	
	def isLocked(self):
		return self.__isLocked

	def setDateEarned(self, earned):
		self.__dateEarned = earned
		if earned:
			self.__locked = False
		else:
			self.__locked = True

class Console(Record):

	def __init__(self, name, consoleId, thegamesdbApiId, extensions, romDir, command, db, consoleImg, noCoverArtImg, imgCacheDir, emulator):
		super(Console, self).__init__(db, 'consoles', ['console_id', 'name', 'thegamesdb_api_id', 'achievement_api_id'], 'console_id', consoleId, True)
		self.setProperty('name', name)
		self.setProperty('thegamesdb_api_id', thegamesdbApiId)
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
		self.__gameDict = {}
		
	def addIgnoreRom(self, rom):
		if rom not in self.__ignoreRoms:
			self.__ignoreRoms.append(rom)
			
	def getAchievementApiId(self):
		return self.getProperty('achievement_api_id')

	def getCommand(self, game):
		return self.__command.replace('%%GAME%%', "\"%s\"" % game.getPath()).replace('%%USERCONFDIR%%', userConfDir)

	def getDir(self):
		return self.__dir

	def getEmulator(self):
		return self.__emulator
	
	def getGame(self, i):
		return self.__gameDict[i]
		
	def getGames(self, limit=0, count=0, refeshGames=False):
		if self.__games == None or refeshGames:
			self.__gameDict = {}
			self.connect()
			#query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d ORDER BY UPPER(`name`)' % self.getId()
			query = 'SELECT * FROM `games` WHERE `console_id` = %d ORDER BY UPPER(`name`)' % self.getId()
			if limit >= 0 and count > 0:
				query += ' LIMIT %d, %d' % (limit, count)
			query += ';'
			cur = self.doQuery(query)
			self.__games = []
			while True:
				row = cur.fetchone()
				if row == None:
					break
				g = Game(row['game_id'], self.getDb(), self, False, row)
				self.__gameDict[int(row['game_id'])] = g
				self.__games.append(g)
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
	
	def getGamesWithAchievements(self):
		self.connect()
		games = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `achievement_api_id` > 0 AND (SELECT COUNT(*) FROM `achievements_badges` WHERE `game_id` = `achievement_api_id`) > 0 ORDER BY UPPER(`name`)' % self.getId()
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			games.append(Game(row['game_id'], self.getDb(), self))
		self.disconnect()
		return games
		
	def getGamesWithAchievementIds(self):
		self.connect()
		games = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `achievement_api_id` > 0 AND (SELECT COUNT(*) FROM `achievements_badges` WHERE `game_id` = `achievement_api_id`) > 0 ORDER BY UPPER(`name`)' % self.getId()
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			games.append(row['game_id'])
		self.disconnect()
		return games

	def getExtensions(self):
		return self.__extensions
	
	def getFavourites(self, limit=0, count=0):
		self.connect()
		favourites = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `favourite` = 1 ORDER BY UPPER(`name`)' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			favourites.append(Game(row['game_id'], self.getDb(), self))
		self.disconnect()
		return favourites
		
	def getFavouriteIds(self, limit=0, count=0):
		self.connect()
		favourites = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `favourite` = 1 ORDER BY UPPER(`name`)' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			favourites.append(row['game_id'])
		self.disconnect()
		return favourites
		
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
	
	def getMostPlayedGames(self, limit=0, count=0):
		self.connect()
		mostPlayed = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `play_count` > 0 ORDER BY `play_count` DESC' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			mostPlayed.append(Game(row['game_id'], self.getDb(), self))
		self.disconnect()
		return mostPlayed
		
	def getMostPlayedGameIds(self, limit=0, count=0):
		self.connect()
		mostPlayed = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `play_count` > 0 ORDER BY `play_count` DESC' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			mostPlayed.append(row['game_id'])
		self.disconnect()
		return mostPlayed
	
	def getRecentlyAddedGames(self, limit=0, count=0):
		self.connect()
		recentlyAdded = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d ORDER BY `added`, UPPER(`name`)' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		query += ';'
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			recentlyAdded.append(Game(row['game_id'], self.getDb(), self))
		self.disconnect()
		return recentlyAdded
		
	def getRecentlyAddedGameIds(self, limit=0, count=0):
		self.connect()
		recentlyAdded = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d ORDER BY `added`, UPPER(`name`)' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		query += ';'
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			recentlyAdded.append(row['game_id'])
		self.disconnect()
		return recentlyAdded
	
	def getRecentlyPlayedGames(self, limit=0, count=0):
		self.connect()
		recentlyPlayed = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `last_played` > -1 ORDER BY `last_played`' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		query += ';'
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			recentlyPlayed.append(Game(row['game_id'], self.getDb(), self))
		self.disconnect()
		return recentlyPlayed
		
	def getRecentlyPlayedGameIds(self, limit=0, count=0):
		self.connect()
		recentlyPlayed = []
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d AND `last_played` > -1 ORDER BY `last_played`' % self.getId()
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		query += ';'
		cur = self.doQuery(query)
		while True:
			row = cur.fetchone()
			if row == None:
				break
			recentlyPlayed.append(row['game_id'])
		self.disconnect()
		return recentlyPlayed

	def getRomDir(self):
		return self.__romDir
	
	def getTheGamesDbApiId(self):
		return self.getProperty('thegamesdb_api_id')
		
	def ignoreRom(self, rom):
		return rom in self.__ignoreRoms
	
	def refresh(self):
		super(Console, self).refresh()
		self.__gameTotal = None
		self.__games = None
		
	def searchForGames(self, regexpStr):
		#regexpStr = regexpStr.replace('.', '\.')
		games = []
		self.connect()
		cur = self.doQuery('SELECT `game_id`, `name` FROM `games` WHERE `console_id` = %d AND `name` REGEXP "%s" ORDER BY UPPER(`name`)' % (self.getId(), regexpStr))
		while True:
			row = cur.fetchone()
			if row == None:
				break
			games.append((row['game_id'], row['name']))
		self.disconnect()
		return games
	
	def setAchievementApiId(self, apiId):
		self.setProperty('achievement_api_id', apiId)

class Game(Record):

	def __init__(self, gameId, db, console, loadData=True, row=None):
		super(Game, self).__init__(db, 'games', ['thegamesdb_id', 'exists', 'console_id', 'name', 'cover_art', 'game_path', 'overview', 'released', 'last_played', 'favourite', 'play_count', 'size', 'rasum', 'achievement_api_id'], 'game_id', int(gameId), True, loadData, row)
		self.__console = console

	def getAchievementApiId(self):
		return self.getProperty('achievement_api_id')

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
	
	def getPlayCount(self):
		return self.getProperty('play_count')

	def getReleased(self, fmt=None):
		timestamp = self.getProperty('released')
		if fmt == None:
			return timestamp
		return datetime.fromtimestamp(timestamp).strftime(fmt)

	def getSize(self, humanReadable=False):
		if not humanReadable:
			return self.getProperty('size')
		size = self.getProperty('size')
		if size < 1024:
			return "%diB"
		if size < 1048576:
			return "%.1fKiB" % (size / 1024.0)
		if size < 1073741824:
			return "%.1fMiB" % (size / 1048576.0)
		return "%.1fGiB" % (size / 1073741824.0)
	
	def hasAchievements(self):
		apiId = self.getAchievementApiId()
		if apiId <= 0:
			return False
		self.connect()
		cur = self.doQuery('SELECT COUNT(*) AS `total` FROM `achievements_games` WHERE `game_id` = %d;' % apiId)
		row = cur.fetchone()
		rtn = False
		if row != None:
			return int(row['total']) > 0
		self.disconnect()
		return rtn

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
