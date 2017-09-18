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
			return '"%s"' % v
		return str(v)
	
	def isNew(self):
		return self.__isNew
			
	def refresh(self):
		if self.__properties[self.__keyField] != None:
			query = QSqlQuery()
			query.exec_("SELECT %s FROM `%s` WHERE `%s` = %d;" % (','.join("`%s`" % f for f in self.__fields), self.__table, self.__keyField, self.__properties[self.__keyField]))
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
			i = 0
			total = len(self.__dirtyFields)
			q = 'UPDATE `%s` SET ' % self.__table
			for f in self.__dirtyFields:
				q += '`%s` = %s' % (f, self.convertValue(self.__properties[f]))
				if i < total - 1:
					q += ','
				i += 1
			q += ' WHERE `%s` = %d;' % (self.__keyField, self.__properties[self.__keyField])

		query = QSqlQuery()
		query.exec_(q)

		if self.__isNew:
			self.__isNew = False
			self.__properties[self.__keyField] = query.lastInsertId()
		self.__dirtyFields = []
			
	def setProperty(self, field, value):
		self.__properties[field] = value
		if not field in self.__dirtyFields:
			self.__dirtyFields.append(field)
		
class ConsoleRecord(Record):
	
	def __init__(self, db, keyValue, row=None):
		super(ConsoleRecord, self).__init__(db, "console", ["console_id", "gamesdb_id", "retroachievement_id", "name"], "console_id", keyValue, True, row)
		
	def setGamesDbId(self, i):
		self.setProperty("gamesdb_id", int(i))

	def setName(self, name):
		self.setProperty("name", name)
		
	def setRetroAchievementId(self, i):
		self.setProperty("retroachievement_id", int(i))

class Console(object):
	
	def __init__(self, db, name, gamesDbId, retroAchievementId, image, emulator, extensions, ignoreRoms, command, noCoverArt):
		self.__image = image
		self.__emulator = emulator
		self.__extensions = extensions
		self.__ignoreRoms = ignoreRoms
		self.__command = command
		self.__noCoverArt = noCoverArt
		self.__consoleRecord = None
		self.__db = db
		
		query = QSqlQuery()
		query.exec_("SELECT `console_id`, `gamesdb_id`, `retroachievement_id`, `name` FROM `console` WHERE `name` = \"%s\";" % name)
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
			self.__consoleRecord.save()
			self.__db.commit()
			
	def getName(self):
		return self.__consoleRecord.getName()
		

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
