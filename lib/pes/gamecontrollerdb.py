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

import os
import logging
import pes
import re

class GameControllerDb(object):
	
	def __init__(self, db):
		# does the db exist?
		if not os.path.exists(db):
			raise IOError("File %s does not exist")
		self.__db = db
		self.__entries = {}
		self.__guidRe = re.compile("^[0-9a-z]+,")
		logging.debug("GameControllerDb.init: created for database %s" % self.__db)

	def add(self, jsMap):
		if not self.__guidRe.match(jsMap):
			logging.error("GameControllerDb.add: invalid mapping supplied: %s" % jsMap)
			return False
		
		guid, name, dic = self.__processMap(jsMap)
		if not "platform" in dic:
			dic["platform"] = "Linux"
		if guid in self.__entries:
			logging.debug("GameControllerDb.add: replacing entry %s" % guid)
		else:
			logging.debug("GameControllerDb.add: adding new entry for %s" % guid)
		self.__entries[guid] = (name, dic)
		return True

	def load(self):
		with open(self.__db, "r") as f:
			for line in f:
				if self.__guidRe.match(line):
					guid, name, dic = self.__processMap(line)
					self.__entries[guid] = (name, dic)
		logging.debug("GameControllerDb.load: loaded %d entries ok" % len(self.__entries))
		return True
	
	@staticmethod
	def __processMap(jsMap):
		fields = jsMap.split(",")
		dic = {}
		for field in fields[2:]:
			values = field.split(":")
			if len(values) == 2:
				dic[values[0]] = values[1]
		return (fields[0], fields[1], dic)
	
	def save(self):
		with open(self.__db, "w") as f:
			f.write("#\n# THIS FILE WAS AUTOMATICALLY GENERATED BY PES\n#\n")
			for e in self.__entries:
				name, dic = self.__entries[e]
				if "platform" in dic and dic["platform"] == "Linux":
					l = [e, name]
					for k, v in dic.iteritems():
						l.append("%s:%s" % (k, v))
					f.write(",".join(l))
					f.write("\n")
		logging.debug("GameControllerDb.save: save entries to file ok")
