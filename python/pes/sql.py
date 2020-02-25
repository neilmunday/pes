#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2020 Neil Munday (neil@mundayweb.com)
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
import pes

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

Base = declarative_base()

def connect(db=pes.userDb):
	s = "sqlite:///%s" % db
	logging.debug("pes.sql.connect: connecting to: %s" % s)
	return create_engine(s)

def createAll(engine):
	Base.metadata.create_all(engine)

class Console(Base):
	__tablename__ = "console"

	id = Column(Integer, primary_key=True)
	name = Column(String)
	gamesDbId = Column(Integer, index=True) # FBA and MAMA use the same ID
	retroId = Column(Integer, index=True) # Mega Drive & Gensis use same ID

	def __repr__(self):
		return "<Console id=%s name=%s gamesDbId=%s retroId=%s>" % (self.id, self.name, self.gamesDbId, self.retroId)

class Game(Base):
	__tablename__ = "game"

	id = Column(Integer, primary_key=True)
	name = Column(String)
	releaseDate = Column(Date)
	rasum = Column(String)
	gamesDbId = Column(Integer, index=True)
	retroId = Column(Integer, ForeignKey('retroachievement_game.id'), index=True)
	description = Column(String)
	path = Column(String)
	consoleId = Column(Integer, ForeignKey('console.id'))

	console = relationship("Console", back_populates="games")

class MameGame(Base):
	__tablename__ = "mame_game"

	shortName = Column(String, primary_key=True)
	name = Column(String)

class RetroAchievementGame(Base):
	__tablename__ = "retroachievement_game"
	id = Column(Integer, primary_key=True)
	rasum = Column(String, index=True)
	name = Column(String)
	consoleId = Column(Integer, ForeignKey('console.id'))

	console = relationship("Console", back_populates="retrogames")

	def __repr__(self):
		return "<RetroAchievementGame id=%d rasum=%s name=%s consoleId=%d>" % (self.id , self.rasum, self.name, self.consoleId)

Console.games = relationship("Game", order_by=Game.id, back_populates="console")
Console.retrogames = relationship("RetroAchievementGame", order_by=RetroAchievementGame.id, back_populates="console")
