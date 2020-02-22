#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2019 Neil Munday (neil@mundayweb.com)
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

def connect():
	s = "sqlite:///%s" % pes.userDb
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

class GameCatalogue(Base):
	__tablename__ = "game_catalogue"

	shortName = Column(String, primary_key=True)
	name = Column(String)

class RetroAchievementGame(Base):
	__tablename__ = "retroachievement_game"
	id = Column(Integer, primary_key=True)
	rasum = Column(String, index=True)
	name = Column(String)
	consoleId = Column(Integer, ForeignKey('console.id'))

	console = relationship("Console", back_populates="retrogames")

Console.games = relationship("Game", order_by=Game.id, back_populates="console")
Console.retrogames = relationship("RetroAchievementGame", order_by=RetroAchievementGame.id, back_populates="console")
