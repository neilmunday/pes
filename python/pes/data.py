#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2017 Neil Munday (neil@mundayweb.com)
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

from PyQt5.QtSql import QSqlDatabase, QSqlQuery

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

	def __getWritableFields(self):
		l = []
		for f in self.__fields:
			if f != self.__keyField:
				l.append(f)
		return l

	@staticmethod
	def convertValue(v):
		isNumeric = False
		try:
			float(v)
			isNumeric = True
		except ValueError:
			pass
		if not isNumeric:
			return "'%s'" % v.replace("'", "''")
		return str(v)

	def _doQuery(self, q, bindings=None):
		logging.debug("Record._doQuery: %s" % q)
		dbOpen = self.__db.isOpen()
		#logging.debug("Record._doQuery: conn name: %s" % self.__db.connectionName())
		if not dbOpen:
			logging.debug("Record._doQuery: database is closed, opening...")
			if not self.__db.open():
				raise IOError("Record._doQuery: could not open database")
		query = QSqlQuery(self.__db)
		if bindings != None:
			query.prepare(q)
			for field, value in bindings.items():
				query.bindValue(":%s" % field, value)
			if not query.exec_():
				logging.error("Record._doQuery: Error \"%s\" encountered whilst executing:\n%s" % (query.lastError().text(), q))
		else:
			if not query.exec_(q):
				logging.error("Record._doQuery: Error \"%s\" encountered whilst executing:\n%s" % (query.lastError().text(), q))
		if not dbOpen:
			logging.debug("Record._doQuery: closing database")
			self.__db.close()
		return query

	def getId(self):
		return self.__properties[self.__keyField]

	def _getProperty(self, field):
		return self.__properties[field]

	def isNew(self):
		return self.__isNew

	def refresh(self):
		if self.__properties[self.__keyField] != None:
			query = self._doQuery("SELECT %s FROM `%s` WHERE `%s` = %d;" % (','.join("`%s`" % f for f in self.__fields), self.__table, self.__keyField, self.__properties[self.__keyField]))
			if not query.first():
				self.__isNew = True
				self.__dirtyFields = self.__getWritableFields()
			else:
				for f in self.__fields:
					self.__properties[f] = query.record().indexOf(f)
				self.__isNew = False
				self.__dirtyFields = []
		else:
			self.__isNew = True

	def save(self):
		q = ''
		if self.__isNew:
			logging.debug("Record.save: saving new %s record" % self.__table)
			i = 0
			writableFields = None
			if self.__autoIncrement:
				writableFields = self.__getWritableFields()
			else:
				writableFields = self.__fields
			total = len(writableFields)
			q = 'INSERT INTO `%s` (' % self.__table
			endQuery = ''
			for f in writableFields:
				if not f in self.__properties:
					self.__properties[f] = "NULL"
				q += '`%s`' % f
				endQuery += self.convertValue(self.__properties[f])
				if i < total - 1:
					q += ','
					endQuery += ','
				i += 1

			q += ') VALUES (%s);' % endQuery
		else:
			logging.debug("Record.save: updating %s record %d" % (self.__table, self.__properties[self.__keyField]))
			i = 0
			total = len(self.__dirtyFields)
			q = 'UPDATE `%s` SET ' % self.__table
			for f in self.__dirtyFields:
				q += '`%s` = %s' % (f, self.convertValue(self.__properties[f]))
				if i < total - 1:
					q += ','
				i += 1
			q += ' WHERE `%s` = %d;' % (self.__keyField, self.__properties[self.__keyField])

		query = self._doQuery(q)
		self.__db.commit()

		if self.__isNew:
			self.__isNew = False
			self.__properties[self.__keyField] = query.lastInsertId()
		self.__dirtyFields = []

	def _setProperty(self, field, value):
		self.__properties[field] = value
		if not field in self.__dirtyFields:
			self.__dirtyFields.append(field)

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
				"retroachievement_id",
				"achievement_total",
				"score_total",
				"exists"
			],
			"game_id",
			keyValue,
			True,
			row
		)

	def setAchievementTotal(self, total):
		self._setProperty("achievement_total", int(total))

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

	def setLastPlayed(self, timestamp):
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
		self._setProperty("retroachievement_id", achievementId)

	def setScoreTotal(self, score):
		self._setProperty("score_total", int(score))

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

class Console(object):

	def __init__(self, db, name, gamesDbId, retroAchievementId, image, emulator, romDir, extensions, ignoreRoms, command, noCoverArt, covertArtDir):
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
			return self.__configparser.get(section, prop).replace("%%USERDIR%%", pes.userDir)
		logging.error("Settings.getValue: unsupported type \"%s\"" % propType)

	def set(self, section, prop, value):
		self.__configparser.set(section, prop, str(value))
