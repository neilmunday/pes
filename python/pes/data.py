#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2018 Neil Munday (neil@mundayweb.com)
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

import configparser
import logging
import os
import pes
import time
import sys

from PyQt5.QtSql import QSqlDatabase, QSqlQuery

def doQuery(db, q, bindings=None):
	logging.debug("doQuery: %s" % q)
	dbOpen = db.isOpen()
	#logging.debug("Record._doQuery: conn name: %s" % self.__db.connectionName())
	if not dbOpen:
		logging.debug("doQuery: database is closed, opening...")
		if not db.open():
			raise IOError("doQuery: could not open database")
	query = QSqlQuery(db)
	if bindings != None:
		query.prepare(q)
		for field, value in bindings.items():
			query.bindValue(":%s" % field, value)
		if not query.exec_():
			raise Exception("doQuery: Error \"%s\" encountered whilst executing:\n%s" % (query.lastError().text(), q))
	else:
		if not query.exec_(q):
			raise Exception("doQuery: Error \"%s\" encountered whilst executing:\n%s" % (query.lastError().text(), q))
	if not dbOpen:
		logging.debug("doQuery: closing database")
		db.close()
	return query

class BatchQuery(object):

	_BATCH_INTERVAL = 100

	def __init__(self, db):
		self._db = db
		self.__queries = []

	def addQuery(self, query):
		self.__queries.append(query)
		if len(self.__queries) > self._BATCH_INTERVAL:
			self.execute()

	def execute(self):
		logging.debug("BatchQuery.execute: executing queries")
		doQuery(self._db, "%s" % ';'.join(self.__queries))
		self._db.commit()
		self.__queries = []

	def finish(self):
		if len(self.__queries) > 0:
			logging.debug("BatchQuery: finishing...")
			self.execute()

class BatchInsertQuery(object):

	_BATCH_INTERVAL = 100

	def __init__(self, db, table=None, fieldNames=None):
		logging.debug("BatchInsertQuery.__init__: object created")
		self.__db = db
		self.__values = []
		self.__query = None
		self.__table = table
		if fieldNames == None:
			self.__fieldNames = []
		else:
			self.__fieldNames = fieldNames
		if self.__table != None and len(self.__fieldNames) > 0:
			self.__fieldNames.sort()
			self.__query = "INSERT INTO `%s` (%s) VALUES " % (self.__table, ",".join("`%s`" % i for i in self.__fieldNames))

	def add(self, properties):
		values = []
		for f in self.__fieldNames:
			if isinstance(properties[f], str):
				values.append("'%s'" % properties[f].replace("'", "''"))
			else:
				values.append(properties[f])
		self.__values.append("(%s)" % ",".join(str(x) for x in values))
		if len(self.__values) > self._BATCH_INTERVAL:
			self.execute()

	def addRecord(self, record):
		logging.debug("BatchInsertQuery.addRecord: record added, %d cached" % len(self.__values))
		if self.__query == None:
			if record.isAutoIncrement():
				for f in record.getWritableFields():
					self.__fieldNames.append(f)
			else:
				for f in record.getFields():
					self.__fieldNames.append(f)
			self.__fieldNames.sort()
			self.__query = "INSERT INTO `%s` (%s) VALUES " % (record.getTableName(), ",".join("`%s`" % i for i in self.__fieldNames))
		self.add(record.toDic())

	def execute(self):
		logging.debug("BatchInsertQuery.execute: executing query")
		doQuery(self.__db, "%s %s;" % (self.__query, ",".join(self.__values)))
		self.__db.commit()
		self.__values = []

	def finish(self):
		if len(self.__values) > 0:
			logging.debug("BatchInsertQuery: finishing...")
			self.execute()

class BatchUpdateQuery(BatchQuery):

	def __init__(self, db):
		super(BatchUpdateQuery, self).__init__(db)
		logging.debug("BatchUpdateQuery.__init__: object created")

class Record(object):

	def __init__(self, db, table, fields, keyField, keyValue, autoIncrement=True, record=None):
		self.__db = db
		self.__table = table
		self.__fields = fields
		self.__keyField = keyField
		self.__keyValue = keyValue
		self.__properties = {}
		self.__properties[self.__keyField] = keyValue
		self.__isDirty = False
		self.__isNew = False
		self.__dirtyFields = []
		self.__autoIncrement = autoIncrement

		if record == None:
			self.refresh()
		else:
			for i in range(0, record.count()):
				self.__properties[record.fieldName(i)] = record.value(i)

	def getWritableFields(self):
		l = []
		for f in self.__fields:
			if f != self.__keyField:
				l.append(f)
		return l

	def _doQuery(self, q, bindings=None):
		return doQuery(self.__db, q, bindings)

	def _getDb(self):
		return self.__db

	def getId(self):
		return self.__properties[self.__keyField]

	def _getProperty(self, field):
		return self.__properties[field]

	def getFields(self):
		return self.__fields

	def getTableName(self):
		return self.__table

	def isAutoIncrement(self):
		return self.__autoIncrement

	def isDirty(self):
		return len(self.__dirtyFields) > 0

	def isNew(self):
		return self.__isNew

	def refresh(self):
		if self.__properties[self.__keyField] != None:
			query = self._doQuery("SELECT %s FROM `%s` WHERE `%s` = %d;" % (','.join("`%s`" % f for f in self.__fields), self.__table, self.__keyField, self.__properties[self.__keyField]))
			if not query.first():
				self.__isNew = True
				self.__dirtyFields = self.getWritableFields()
			else:
				for f in self.__fields:
					self.__properties[f] = query.value(query.record().indexOf(f))
				self.__isNew = False
				self.__dirtyFields = []
				logging.debug("Record.refresh: properties dictionary set to %s" % self.__properties)
		else:
			self.__isNew = True

	def save(self, commit=True):
		q = ''
		if self.__isNew:
			logging.debug("Record.save: saving new %s record" % self.__table)
			i = 0
			writableFields = None
			if self.__autoIncrement:
				writableFields = self.getWritableFields()
			else:
				writableFields = self.__fields
			total = len(writableFields)
			q = 'INSERT INTO `%s` (' % self.__table
			endQuery = ''
			for f in writableFields:
				if not f in self.__properties:
					self.__properties[f] = "NULL"
				q += '`%s`' % f
				endQuery += ':%s' % f
				if i < total - 1:
					q += ','
					endQuery += ','
				i += 1

			q += ') VALUES (%s);' % endQuery
		else:
			i = 0
			total = len(self.__dirtyFields)
			if total == 0:
				logging.debug("Record.save: no need to update %s record %d" % (self.__table, self.__properties[self.__keyField]))
				return False
			logging.debug("Record.save: updating %s record %d" % (self.__table, self.__properties[self.__keyField]))
			q = 'UPDATE `%s` SET ' % self.__table
			for f in self.__dirtyFields:
				q += '`%s` = :%s' % (f, f)
				if i < total - 1:
					q += ','
				i += 1
			q += ' WHERE `%s` = %d;' % (self.__keyField, self.__properties[self.__keyField])

		query = self._doQuery(q, self.__properties)
		if commit:
			self.__db.commit()

		if self.__isNew:
			self.__isNew = False
			self.__properties[self.__keyField] = query.lastInsertId()
		self.__dirtyFields = []
		return True

	def _setProperty(self, field, value):
		if field in self.__properties and self.__properties[field] == value:
			return
		self.__properties[field] = value
		if not field in self.__dirtyFields:
			self.__dirtyFields.append(field)

	def toDic(self):
		return self.__properties.copy()

class ConsoleRecord(Record):

	def __init__(self, db, keyValue, row=None):
		super(ConsoleRecord, self).__init__(db, "console", ["console_id", "gamesdb_id", "gamesdb_name", "retroachievement_id", "name"], "console_id", keyValue, True, row)

	def getGamesDbId(self):
		return int(self._getProperty("gamesdb_id"))

	def getGameTotal(self):
		query = self._doQuery("SELECT COUNT(*) FROM `game` WHERE `console_id` = %d;" % self.getId())
		query.first()
		return int(query.value(0))

	def getGamesDbName(self):
		return self._getProperty("gamesdb_name")

	def getLastPlayed(self, limit=10):
		query = self._doQuery("SELECT * FROM `game` WHERE `console_id` = %d AND `last_played` != 0 ORDER BY `last_played` DESC LIMIT %d" % (self.getId(), limit))
		games = []
		db = self._getDb()
		while query.next():
			record = query.record()
			games.append(GameRecord(db, record.value("game_id"), record))
		return games

	def getLatestAdditions(self, limit=10):
		query = self._doQuery("SELECT * FROM `game` WHERE `console_id` = %d ORDER BY `added` DESC LIMIT %d" % (self.getId(), limit))
		games = []
		db = self._getDb()
		while query.next():
			record = query.record()
			games.append(GameRecord(db, record.value("game_id"), record))
		return games

	def getName(self):
		return self._getProperty("name")

	def getRetroAchievementId(self):
		return self._getProperty("retroachievement_id")

	def setGamesDbId(self, i):
		self._setProperty("gamesdb_id", int(i))

	def setGamesDbName(self, s):
		self._setProperty("gamesdb_name", s)

	def setName(self, name):
		self._setProperty("name", name)

	def setRetroAchievementId(self, i):
		self._setProperty("retroachievement_id", int(i))

class GameRecord(Record):

	def __init__(self, db, keyValue, row=None):
		super(GameRecord, self).__init__(
			db,
			"game",
			[
				"game_id",
				"console_id",
				"game_match_id",
				"name",
				"coverart",
				"path",
				"overview",
				"released",
				"last_played",
				"added",
				"play_count",
				"size",
				"rasum",
				"retroachievement_game_id",
				"exists"
			],
			"game_id",
			keyValue,
			True,
			row
		)

	def getAchievementTotal(self):
		return int(self._getProperty("achievement_total"))

	def getAdded(self):
		return int(self._getProperty("added"))

	def getConsoleId(self):
		return int(self._getProperty("console_id"))

	def getGameMatchId(self):
		return int(self._getProperty("game_match_id"))

	def getName(self):
		return self._getProperty("name")

	def getPath(self):
		return self._getProperty("path")

	def getPlayCount(self):
		return self._getProperty("play_count")

	def getOverview(self):
		return self._getProperty("overview")

	def getReleased(self):
		return int(self._getProperty("released"))

	def getRasum(self):
		return self._getProperty("rasum")

	def getRetroAchievementId(self):
		return int(self._getProperty("retroachievement_game_id"))

	def getSize(self):
		return int(self._getProperty("size"))

	def incrementPlayCount(self):
		self.setPlayCount(self.getPlayCount() + 1)

	def setAdded(self, timestamp):
		self._setProperty("added", int(timestamp))

	def setConsoleId(self, consoleId):
		self._setProperty("console_id", int(consoleId))

	def setCoverArt(self, path):
		self._setProperty("coverart", path)

	def setExists(self, exists):
		if exists:
			self._setProperty("exists", 1)
		else:
			self._setProperty("exists", 0)

	def setLastPlayed(self, timestamp=None):
		if timestamp == None:
			timestamp = time.time()
		self._setProperty("last_played", int(timestamp))

	def setMatchId(self, matchId):
		self._setProperty("game_match_id", int(matchId))

	def setName(self, name):
		self._setProperty("name", name)

	def setOverview(self, overview):
		self._setProperty("overview", overview)

	def setPath(self, path):
		self._setProperty("path", path)

	def setPlayCount(self, count):
		self._setProperty("play_count", int(count))

	def setRasum(self, rasum):
		self._setProperty("rasum", rasum)

	def setReleased(self, timestamp):
		self._setProperty("released", int(timestamp))

	def setRetroAchievementId(self, achievementId):
		self._setProperty("retroachievement_game_id", achievementId)

	def setSize(self, size):
		self._setProperty("size", int(size))

class GameMatchRecord(Record):

	def __init__(self, db, keyValue, row=None):
		super(GameMatchRecord, self).__init__(db, "game_match", ["game_match_id", "game_id", "game_title_id"], "game_match_id", keyValue, True, row)

	def getGameId(self):
		return self._getProperty("game_id")

	def getTitleId(self):
		return self._getProperty("game_title_id")

	def setGameId(self, gameId):
		self._setProperty("game_id", int(gameId))

	def setTitleId(self, titleId):
		self._setProperty("game_title_id", int(titleId))

class GameTitleRecord(Record):

	def __init__(self, db, keyValue, row=None):
		super(GameTitleRecord, self).__init__(db, "game_title", ["game_title_id", "gamesdb_id", "console_id", "title"], "game_title_id", keyValue, True, row)

	def getConsoleId(self):
		return self._getProperty("console_id")

	def getGamesDbId(self):
		return self._getProperty("gamesdb_id")

	def getTitle(self):
		return self._getProperty("title")

	def setConsoleId(self, consoleId):
		self._setProperty("console_id", int(consoleId))

	def setGamesDbId(self, gamesDbId):
		self._setProperty("gamesdb_id", int(gamesDbId))

	def setTitle(self, title):
		self._setProperty("title", title)

class RetroAchievementBadgeRecord(Record):

	def __init__(self, db, keyValue, row=None):
		super(RetroAchievementBadgeRecord, self).__init__(db, "retroachievement_badge", ["badge_id", "title", "retroachievement_game_id", "description", "points", "badge_path", "badge_path_locked"], "badge_id", keyValue, False, row)

	def getDescription(self):
		return self._getProperty("description")

	def getGameId(self):
		return self._getProperty("retroachievement_game_id")

	def getLockedPath(self):
		return self._getProperty("badge_path")

	def getPath(self):
		return self._getProperty("badge_path_locked")

	def getPoints(self):
		return self._getProperty("points")

	def getTitle(self):
		return self._getProperty("title")

	def setDescription(self, txt):
		self._setProperty("description", txt)

	def setGameId(self, i):
		self._setProperty("retroachievement_game_id", int(i))

	def setLockedPath(self, path):
		self._setProperty("badge_path_locked", path)

	def setPath(self, path):
		self._setProperty("badge_path", path)

	def setPoints(self, p):
		self._setProperty("points", int(p))

	def setTitle(self, t):
		self._setProperty("title", t)

class RetroAchievementUserRecord(Record):

	def __init__(self, db, keyValue, row=None):
		super(RetroAchievementUserRecord, self).__init__(db, "retroachievement_user", ["user_id", "username", "total_points", "total_truepoints", "rank", "updated"], "user_id", keyValue, False, row)

	def getName(self):
		return self._getProperty("username")

	def getRank(self):
		return self._getProperty("rank")

	def getTotalPoints(self):
		return int(self._getProperty("total_points"))

	def getTotalTruePoints(self):
		return int(self._getProperty("total_truepoints"))

	def getUpdated(self):
		return int(self._getProperty("updated"))

	def hasEarnedBadge(self, badgeId):
		query = self._doQuery("SELECT COUNT(*) AS `total` FROM `retroachievement_earned` WHERE `user_id` = :user_id AND `badge_id` = :badge_id AND `date_earned` > 0;", {"user_id": self.getId(), "badge_id": badgeId})
		query.first()
		return int(query.value(0))

	def hasEarnedHardcoreBadge(self, badgeId):
		query = self._doQuery("SELECT COUNT(*) AS `total` FROM `retroachievement_earned` WHERE `user_id` = :user_id AND `badge_id` = :badge_id AND `date_earned_hardcore` > 0;", {"user_id": self.getId(), "badge_id": badgeId})
		query.first()
		return int(query.value(0))

	def save(self, commit=True):
		if self.isNew():
			logging.debug("RetroAchievementUserRecord.save: new record")
			self.setUpdated(time.time())
			super(RetroAchievementUserRecord, self).save(commit)
			return
		if not self.isDirty():
			logging.debug("RetroAchievementUserRecord.save: no need to save")
			return
		logging.debug("RetroAchievementUserRecord.save: existing record")
		self.setUpdated(time.time())
		super(RetroAchievementUserRecord, self).save(commit)

	def setName(self, name):
		self._setProperty("username", name)

	def setRank(self, rank):
		self._setProperty("rank", int(rank))

	def setTotalPoints(self, p):
		self._setProperty("total_points", int(p))

	def setTotalTruePoints(self, p):
		self._setProperty("total_truepoints", int(p))

	def setUpdated(self, ts):
		self._setProperty("updated", int(ts))

class RetroAchievementGameRecord(Record):

	def __init__(self, db, keyValue, row=None):
		super(RetroAchievementGameRecord, self).__init__(db, "retroachievement_game", ["retroachievement_game_id", "achievement_total", "score_total"], "retroachievement_game_id", keyValue, False, row)

	def getAchievementTotal(self):
		return int(self._getProperty("achievement_total"))

	def getScoreTotal(self):
		return int(self._getProperty("score_total"))

	def setAchievementTotal(self, t):
		self._setProperty("achievement_total", int(t))

	def setScoreTotal(self, t):
		self._setProperty("score_total", int(t))

class Console(object):

	def __init__(self, db, name, gamesDbId, retroAchievementId, image, emulator, romDir, extensions, ignoreRoms, command, noCoverArt, covertArtDir, requiredFiles):
		self.__image = image
		self.__emulator = emulator
		self.__romDir = romDir
		self.__extensions = extensions
		self.__ignoreRoms = ignoreRoms
		self.__command = command
		self.__noCoverArt = noCoverArt
		self.__covertArtDir = covertArtDir
		self.__consoleRecord = None
		self.__db = db
		self.__requiredFiles = requiredFiles

		query = QSqlQuery()
		query.exec_("SELECT `console_id`, `gamesdb_id`, `gamesdb_name`, `retroachievement_id`, `name` FROM `console` WHERE `name` = \"%s\";" % name)
		if query.first():
			logging.debug("Console.__init__: loading existing record: %d" % query.value(0))
			self.__consoleRecord = ConsoleRecord(self.__db, query.value(0), query.record())
		else:
			# new record
			logging.debug("Console.__init__: creating new console record for \"%s\"" % name)
			self.__consoleRecord = ConsoleRecord(self.__db, None)
			self.__consoleRecord.setName(name)
			self.__consoleRecord.setGamesDbId(gamesDbId)
			self.__consoleRecord.setRetroAchievementId(retroAchievementId)
			self.save()

	def getCoverArtDir(self):
		return self.__covertArtDir

	def getEmulator(self):
		return self.__emulator

	def getId(self):
		return self.__consoleRecord.getId()

	def getImage(self):
		return self.__image

	def getName(self):
		return self.__consoleRecord.getName()

	def getNoCoverArt(self):
		return self.__noCoverArt

	def getGamesDbId(self):
		return self.__consoleRecord.getGamesDbId()

	def getGamesDbName(self):
		return self.__consoleRecord.getGamesDbName()

	def getGameTotal(self):
		return self.__consoleRecord.getGameTotal()

	def getExtensions(self):
		return self.__extensions

	def getIgnoreRomList(self):
		return self.__ignoreRoms

	def getLastPlayed(self, limit=10):
		return self.__consoleRecord.getLastPlayed(limit)

	def getLatestAdditions(self, limit=10):
		return self.__consoleRecord.getLatestAdditions(limit)

	def getLaunchString(self, game):
		return self.__command.replace('%%GAME%%', "\"%s\"" % game.getPath()).replace('%%USERCONFDIR%%', pes.userConfDir)

	def getRequiredFiles(self):
		return self.__requiredFiles

	def getRetroAchievementId(self):
		return self.__consoleRecord.getRetroAchievementId()

	def getRomDir(self):
		return self.__romDir

	def ignoreRom(self, rom):
		return rom in self.__ignoreRoms

	def save(self):
		self.__consoleRecord.save()

	def setGamesDbName(self, s):
		self.__consoleRecord.setGamesDbName(s)

class Settings(object):

	def __init__(self):
		# open user's settings
		self.__configparser = configparser.RawConfigParser()
		self.__configparser.read(pes.userPesConfigFile)

	def get(self, section, prop, propType="string"):
		if not self.__configparser.has_section(section):
			logging.warning("No section \"%s\" in \"%s\"" % (section, pes.userPesConfigFile))
			return None
		if not self.__configparser.has_option(section, prop):
			logging.warning("No property \"[%s]:%s\" in \"%s\"" % (section, prop, pes.userPesConfigFile))
			return None
		if propType == "string":
			value = self.__configparser.get(section, prop)
			if value == None or len(value) == 0:
				return None
			return value.replace("%%USERDIR%%", pes.userDir)
		logging.error("Settings.getValue: unsupported type \"%s\"" % propType)

	def set(self, section, prop, value):
		self.__configparser.set(section, prop, str(value))
