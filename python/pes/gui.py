#
#    This file is part of the Pi Entertainment System (PES).
#
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

import codecs
import configparser
import logging
import multiprocessing
import os
import queue
import re
import shlex
import subprocess
import sys

from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import QApplication, QDesktopWidget, QMainWindow
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, QFile, QIODevice, QObject, QEvent, QThread, QVariant
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtWebChannel import QWebChannel

import time

import sdl2
import sdl2.ext
import sdl2.joystick

import pes
from pes.data import doQuery, Console, ConsoleRecord, GameRecord, Settings
from pes.common import checkDir, checkFile, getIpAddress, mkdir, pesExit
from pes.retroachievement import BadgeScanWorkerThread
from pes.romscan import RomScanThread
import pes.gamecontroller

def getLitteEndianFromHex(x):
	return int("%s%s" % (x[2:4], x[0:2]), 16)

# workaround for http://bugs.python.org/issue22273
# thanks to https://github.com/GreatFruitOmsk/py-sdl2/commit/e9b13cb5a13b0f5265626d02b0941771e0d1d564
def getJoystickGUIDString(guid):
	s = ''
	for g in guid.data:
		s += "{:x}".format(g >> 4)
		s += "{:x}".format(g & 0x0F)
	return s

def getJoystickDeviceInfoFromGUID(guid):
	vendorId = guid[8:12]
	productId = guid[16:20]
	print("%s\n%s" % (vendorId, productId))
	# swap from big endian to little endian and covert to an int
	vendorId = getLitteEndianFromHex(vendorId)
	productId = getLitteEndianFromHex(productId)
	return (vendorId, productId)

def getMupen64PlusConfigAxisValue(controller, axis, positive=True, both=False):
	bind = sdl2.SDL_GameControllerGetBindForAxis(controller, axis)
	if bind:
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
			if both:
				return "axis(%d-,%d+)" % (bind.value.axis, bind.value.axis)
			if positive:
				return "axis(%d+)" % bind.value.axis
			return "axis(%d-)" % bind.value.axis
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
			return "button(%d)" % bind.value.button
	return "\"\""

def getMupen64PlusConfigButtonValue(controller, button, coreEvent=False):
	bind = sdl2.SDL_GameControllerGetBindForButton(controller, button)
	if bind:
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
			if coreEvent:
				return "B%d" % bind.value.button
			return "button(%d)" % bind.value.button
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_HAT:
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
				return "hat(%d Up)" % bind.value.hat.hat
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
				return "hat(%d Down)" % bind.value.hat.hat
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
				return "hat(%d Left)" % bind.value.hat.hat
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
				return "hat(%d Right)" % bind.value.hat.hat
	return "\"\""

def getRetroArchConfigAxisValue(param, controller, axis, both=False):
	bind = sdl2.SDL_GameControllerGetBindForAxis(controller, axis)
	if bind:
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
			if both:
					return "%s_plus_axis = \"+%d\"\n%s_minus_axis = \"-%d\"\n" % (param, bind.value.axis, param, bind.value.axis)
			return "%s_axis = \"+%d\"\n" % (param, bind.value.axis)
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
			return "%s_btn = \"%d\"\n" % (param, bind.value.button)

	if both:
		return "%s_plus_axis = \"nul\"\n%s_minus_axis = \"nul\"\n" % (param, param)
	return "%s = \"nul\"\n" % param

def getRetroArchConfigButtonValue(param, controller, button):
	bind = sdl2.SDL_GameControllerGetBindForButton(controller, button)
	if bind:
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
			return "%s_btn = \"%d\"\n" % (param, bind.value.button)
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP or button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
				return "%s_axis = \"-%d\"\n" % (param, bind.value.axis)
			return "%s_axis = \"+%d\"\n" % (param, bind.value.axis)
		if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_HAT:
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
				return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "up")
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
				return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "down")
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
				return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "left")
			if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
				return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "right")
	return "%s = \"nul\"\n" % param

def runCommand(command):
	if command.find("|"):
		process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	else:
		process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	return (process.returncode, stdout.decode(), stderr.decode())

class PESWindow(QMainWindow):

	def __init__(self, app, settings, fullscreen=False, retroUser=None):
		super(PESWindow, self).__init__()
		self.__app = app
		self.__running = False
		self.settings = settings
		self.retroUser = retroUser
		self.__player1Controller = None
		self.__player1ControllerIndex = None
		self.__controlPadTotal = 0
		self.__dpadAsAxis = False
		self.keyboardLayouts = []
		self.keyboardLayout = ""
		self.timezones = []
		self.timezone = ""
		self.consoles = []
		self.consoleMap = {}
		self.consoleIdMap = {}

		self.setWindowTitle("PES")

		if sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER) != 0:
			pesExit("failed to initialise SDL2!", True)
		logging.debug("SDL2 joystick and gamecontroller APIs initialised")

		# load joystick database
		logging.debug("loading SDL2 control pad mappings from: %s" % pes.userGameControllerFile)
		mappingsLoaded = sdl2.SDL_GameControllerAddMappingsFromFile(pes.userGameControllerFile.encode())
		if mappingsLoaded == -1:
			pesExit("failed to load SDL2 control pad mappings from: %s" % pes.userGameControllerFile)
		logging.debug("loaded %d control pad mappings" % mappingsLoaded)

		self.listKeyboardLayoutsCommand = settings.get("commands", "listKeyboards")
		if self.listKeyboardLayoutsCommand == None:
			pesExit("listKeyboards setting is missing in %s" % pes.userPesConfigFile)
		self.getKeyboardLayoutCommand = settings.get("commands", "getKeyboard")
		if self.getKeyboardLayoutCommand == None:
			pesExit("getKeyboard setting is missing in %s" % pes.userPesConfigFile)
		self.setKeyboardLayoutCommand = settings.get("commands", "setKeyboard")
		if self.setKeyboardLayoutCommand == None:
			pesExit("setKeyboard setting is missing in %s" % pes.userPesConfigFile)

		self.listTimezoneCommand = settings.get("commands", "listTimezones")
		if self.listTimezoneCommand == None:
			pesExit("listTimezones setting missing in %s" % pes.userPesConfigFile)

		self.getTimezoneCommand = settings.get("commands", "getTimezone")
		if self.getTimezoneCommand == None:
			pesExit("getTimezone setting missing in %s" % pes.userPesConfigFile)

		self.setTimezoneCommand = settings.get("commands", "setTimezone")
		if self.setTimezoneCommand == None:
			pesExit("setTimezone setting missing in %s" % pes.userPesConfigFile)

		self.__theme = settings.get("settings", "theme")
		if self.__theme == None:
			# use classic
			self.__theme = "classic"
		self.__themeDir = os.path.join(pes.themeDir, self.__theme)
		checkDir(self.__themeDir)

		mainPage = os.path.join(self.__themeDir, "html", "main.html")
		checkFile(mainPage)

		self.db = QSqlDatabase.addDatabase("QSQLITE")
		self.db.setDatabaseName(pes.userDb)
		self.db.open()

		if self.retroUser:
			self.retroUser.enableDbSync(self.db)

		self.__loadingThread = LoadingThread(self)
		self.__romScanMonitorThread = RomScanMonitorThread(self.db, self.settings.get("settings", "romScraper"))
		self.__badgeScanMonitorThread = BadgeScanMonitorThread(self.db, self.retroUser, self.settings.get("settings", "badgeDir"))

		self.__page = WebPage()
		self.__webview = WebView()
		self.__webview.setPage(self.__page)
		self.__channel = QWebChannel(self.__page)
		self.__page.setWebChannel(self.__channel)
		self.__handler = CallHandler(self)
		self.__channel.registerObject('handler', self.__handler)
		self.__channel.registerObject('loadingThread', self.__loadingThread)
		self.__channel.registerObject('romScanMonitorThread', self.__romScanMonitorThread)
		self.__channel.registerObject('badgeScanMonitorThread', self.__badgeScanMonitorThread)
		self.__handler.exitSignal.connect(self.__handleExit)
		self.__loadingThread.finishedSignal.connect(self.__loadingFinished)
		self.setCentralWidget(self.__webview)
		self.__webview.load(QUrl("file://%s" % mainPage))

		if fullscreen:
			self.showFullScreen()
		else:
			self.setGeometry(0, 0, 1024, 768)
			self.show()

	def channelReady(self):
		self.__loadingThread.start()

	def close(self):
		logging.info("exiting PES")
		if self.__romScanMonitorThread.isRunning():
			logging.debug("stopping rom scan thread")
			self.__romScanMonitorThread.stop()
		if self.__badgeScanMonitorThread.isRunning():
			logging.debug("stopping badge scan thread")
			self.__badgeScanMonitorThread.stop()
		logging.debug("stopping event loop")
		self.__running = False
		logging.debug("shutting down SDL2")
		sdl2.SDL_Quit()
		logging.debug("closing db")
		self.db.close()
		logging.debug("closing")
		super(PESWindow, self).close()

	def closeAndRun(self, command):
		logging.debug("PESWindow.closeAndRun: about to write to: %s" % pes.scriptFile)
		logging.debug("PESWindow.closeAndRun: command: %s" % command)
		execLog = os.path.join(pes.userLogDir, "exec.log")
		with open(pes.scriptFile, 'w') as f:
			f.write("echo running %s\n" % command)
			f.write("echo see %s for console output\n" % execLog)
			f.write("%s &> %s\n" % (command, execLog))
			f.write("exec %s %s\n" % (os.path.join(pes.baseDir, 'bin', 'pes') , ' '.join(sys.argv[1:])))
		self.close()

	def closeEvent(self, event):
		logging.debug("PESWindow: closeEvent")
		self.__running = False
		super(PESWindow, self).closeEvent(event)

	def controllerConnected(self):
		return self.__player1Controller != None

	def event(self, event):
		if event.type() == QEvent.KeyRelease:
			if event.key() == Qt.Key_Escape:
				logging.debug("QMainWindow.event: escape key pressed")
				self.__page.runJavaScript("commandLineExit();")
		return super(PESWindow, self).event(event)

	def getPlayer1Controller(self):
		return self.__player1Controller

	def getPlayer1ControllerIndex(self):
		return self.__player1ControllerIndex

	def __handleExit(self):
		self.close()

	def run(self):
		self.__running = True

		# look for any connected joysticks
		#joystickTotal = sdl2.joystick.SDL_NumJoysticks()
		#logging.debug("PESWindow.run: found %d joysticks" % joystickTotal)
		#for i in range(joystickTotal):
			#if sdl2.SDL_IsGameController(i):
				#close = True
				#c = sdl2.SDL_GameControllerOpen(i)
				#if sdl2.SDL_GameControllerGetAttached(c):
					#self.__player1Controller = sdl2.SDL_GameControllerOpen(i)
					#self.__player1ControllerId = i
					#logging.debug("PESWindow.run: opened joystick %s at index %d" % (sdl2.SDL_GameControllerNameForIndex(i).decode(), i))
				#if close:
					#sdl2.SDL_GameControllerClose(c)

		joystickTick = sdl2.timer.SDL_GetTicks()

		while self.__running:
			# process SDL events
			events = sdl2.ext.get_events()
			for event in events:
				if event.type == sdl2.SDL_CONTROLLERBUTTONUP:
					if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
						logging.debug("player 1: up")
						self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Up, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
						logging.debug("player 1: down")
						self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Down, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
						logging.debug("player 1: left")
						self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Left, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
						logging.debug("player 1: right")
						self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Right, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_A:
						logging.debug("player 1: A")
						self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Return, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_B:
						logging.debug("player 1: B")
						self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Backspace, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_GUIDE:
						logging.debug("player 1: Guide")
						self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Home, Qt.NoModifier))

			if sdl2.timer.SDL_GetTicks() - joystickTick > 1000:
				tick = sdl2.timer.SDL_GetTicks()
				joystickTotal = sdl2.joystick.SDL_NumJoysticks()
				controlPadTotal = 0
				if joystickTotal > 0:
					for i in range(joystickTotal):
						if sdl2.SDL_IsGameController(i):
							close = True
							c = sdl2.SDL_GameControllerOpen(i)
							if sdl2.SDL_GameControllerGetAttached(c):
								controlPadTotal += 1
								#logging.debug("PESWindow.run: %s is attached at %d" % (sdl2.SDL_GameControllerNameForIndex(i).decode(), i))
								if self.__player1Controller == None:
									logging.debug("PESApp.run: switching player 1 to control pad #%d: %s (%s)" % (i, sdl2.SDL_GameControllerNameForIndex(i).decode(), getJoystickGUIDString(sdl2.SDL_JoystickGetDeviceGUID(i))))
									self.__player1ControllerIndex = i
									self.__player1Controller = c
									self.updateControlPad(self.__player1ControllerIndex)
									close = False
							if close:
								sdl2.SDL_GameControllerClose(c)
				else:
					self.__player1Controller = None
					self.__player1ControllerIndex = None
				if self.__controlPadTotal != controlPadTotal:
					self.__controlPadTotal = controlPadTotal
					self.__handler.emitJoysticksConnected(self.__controlPadTotal)
				joystickTick = tick

			self.__app.processEvents()

	def __loadingFinished(self):
		logging.debug("PESWindow.__loadingFinished: setting console map on rom scan monitor thread")
		self.__romScanMonitorThread.setConsoleMap(self.consoleMap)

	def updateControlPad(self, jsIndex):
		if jsIndex == self.__player1ControllerIndex:
			# hack for instances where a dpad is an axis
			bind = sdl2.SDL_GameControllerGetBindForButton(self.__player1Controller, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP)
			if bind:
				if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
					self.__dpadAsAxis = True
					logging.debug("PESWindow.updateControlPad: enabling dpad as axis hack")
				else:
					self.__dpadAsAxis = False

class LoadingThread(QThread):

	progressSignal = pyqtSignal(int, str)
	finishedSignal = pyqtSignal()

	def __init__(self, window):
		super(LoadingThread, self).__init__(None)
		self.__window = window
		self.__progress = 0

	def run(self):
		logging.debug("LoadingThread.run: opening database using %s" % pes.userDb)

		#query = QSqlQuery()
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `console` ( \
			`console_id` INTEGER PRIMARY KEY, \
			`gamesdb_id` INTEGER, \
			`gamesdb_name` TEXT, \
			`retroachievement_id` INTEGER, \
			`name` TEXT \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"console_index\" on `console` (`console_id` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `games_catalogue` ( \
			`short_name` TEXT, \
			`full_name` TEXT \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"games_catalogue_index\" on `games_catalogue` (`short_name` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `game_title` ( \
			`game_title_id` INTEGER PRIMARY KEY, \
			`gamesdb_id` INTEGER, \
			`console_id` INTEGER, \
			`title` TEXT \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"game_title_index\" on `game_title` (`game_title_id` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `game` ( \
			`game_id` INTEGER PRIMARY KEY, \
			`console_id` INTEGER, \
			`game_match_id` INTEGER, \
			`name` TEXT, \
			`coverart` TEXT, \
			`path` TEXT, \
			`overview` TEXT, \
			`released` INTEGER, \
			`last_played` INTEGER, \
			`added` INTEGER, \
			`play_count` INTEGER, \
			`size` INTEGER, \
			`rasum` TEXT, \
			`retroachievement_game_id` INTEGER, \
			`exists` INTEGER \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"game_index\" on `game` (`game_id` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `game_match` ( \
			`game_match_id` INTEGER PRIMARY KEY, \
			`game_title_id` INTEGER, \
			`game_id` INTEGER \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"game_match_index\" on `game_match` (`game_match_id` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `retroachievement_user` (\
			`user_id` INTEGER PRIMARY KEY, \
			`username` TEXT, \
			`total_points` INTEGER, \
			`total_truepoints` INTEGER, \
			`rank` INTEGER, \
			`updated` INTEGER \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"retroachievement_user_index\" on `retroachievement_user` (`user_id` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `retroachievement_badge` (\
			`badge_id` INTEGER PRIMARY KEY, \
			`title` TEXT, \
			`retroachievement_game_id` INTEGER, \
			`description` TEXT, \
			`points` INTEGER, \
			`badge_path` TEXT, \
			`badge_path_locked` TEXT \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"retroachievement_badge_index\" on `retroachievement_badge` (`badge_id` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `retroachievement_game` (\
			`retroachievement_game_id`,\
			`achievement_total` INTEGER, \
			`score_total` INTEGER \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"retroachievement_game_index\" on `retroachievement_game` (`retroachievement_game_id` ASC);")
		doQuery(self.__window.db, "\
		CREATE TABLE IF NOT EXISTS `retroachievement_earned` (\
			`user_id` INTEGER, \
			`badge_id` INTEGER, \
			`date_earned` INTEGER, \
			`date_earned_hardcore` INTEGER, \
			PRIMARY KEY (user_id, badge_id) \
		);")
		doQuery(self.__window.db, "CREATE INDEX IF NOT EXISTS \"retroachievement_earned_index\" on `retroachievement_earned` (`user_id` ASC, `badge_id` ASC);")
		self.__window.db.commit()

		# populate games catalogue (if needed)
		query = doQuery(self.__window.db, "SELECT COUNT(*) AS `total` FROM `games_catalogue`")
		query.first()
		if query.value(0) == 0:
			logging.debug("LoadingThread.run: populating games catalogue...")
			self.progressSignal.emit(self.__progress, "Populating games catalogue")
			catalogueConfigParser = configparser.RawConfigParser()
			catalogueConfigParser.read(pes.userGamesCatalogueFile, encoding="latin-1")
			sections = catalogueConfigParser.sections()
			sectionTotal = float(len(sections))

			i = 0.0
			insertValues = []
			for section in sections:
				if catalogueConfigParser.has_option(section, 'full_name'):
					fullName = catalogueConfigParser.get(section, 'full_name')
					insertValues.append('("%s", "%s")' % (section, fullName))
				else:
					logging.error("PESLoadingThread.run: games catalogue section \"%s\" has no \"full_name\" option!" % section)
				i += 1.0
				self.__progress = 50 * (i / sectionTotal)
				self.progressSignal.emit(self.__progress, "Populating games catalogue: %s" % fullName)
			if len(insertValues) > 0:
				doQuery(self.__window.db, 'INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES %s;' % ','.join(insertValues))
				self.__window.db.commit()
		else:
			self.__progress = 50
			self.progressSignal.emit(self.__progress, "Games catalogue ok")

		# load consoles
		consoleParser = configparser.RawConfigParser()
		consoleParser.read(pes.userConsolesConfigFile)
		consoleNames = consoleParser.sections()
		consoleTotal = len(consoleNames)
		consoleNames.sort()

		i = 0
		for c in consoleNames:
			try:
				romDir = os.path.join(self.__window.settings.get("settings", "romsDir"), c)
				# make ROMs dir for console
				mkdir(romDir)
				# make cover art dir for console
				coverArtDir = os.path.join(self.__window.settings.get("settings", "coverartDir"), c)
				mkdir(coverArtDir)

				if consoleParser.has_option(c, "ignore_roms"):
					ignoreRoms = consoleParser.get(c, "ignore_roms").split(",")
				else:
					ignoreRoms = []

				retroAchievementId = 0
				if consoleParser.has_option(c, "achievement_id"):
					retroAchievementId = consoleParser.getint(c, "achievement_id")

				requiredFiles = []
				if consoleParser.has_option(c, "require"):
					for f in consoleParser.get(c, "require").split(","):
						requiredFiles.append(f.strip().replace("%%USERBIOSDIR%%", pes.userBiosDir))

				console = Console(
					self.__window.db,
					c,
					consoleParser.getint(c, "thegamesdb_id"),
					retroAchievementId,
					consoleParser.get(c, "image").replace("%%BASE%%", pes.baseDir),
					consoleParser.get(c, "emulator"),
					romDir,
					consoleParser.get(c, "extensions").split(),
					ignoreRoms,
					consoleParser.get(c, "command").replace("%%BASE%%", pes.baseDir),
					consoleParser.get(c, "nocoverart").replace("%%BASE%%", pes.baseDir),
					coverArtDir,
					requiredFiles
				)
				self.__window.consoles.append(console)
				self.__window.consoleMap[c] = console
				self.__window.consoleIdMap[console.getId()] = console
				self.__progress = 50 * (i / consoleTotal)
				self.progressSignal.emit(self.__progress, "Loaded console: %s" % c)
				i += 1
			except configparser.NoOptionError as e:
				logging.error("LoadingThread.run: error parsing config file %s: %s" % (pes.userConsolesConfigFile, e.message))
				self.__window.close()
				return
			except ValueError as e:
				logging.error("LoadingThread.run: error parsing config file %s: %s" % (pes.userConsolesConfigFile, e.message))
				self.__window.close()
				return

		if self.__window.retroUser:
			self.__progress = 95
			self.progressSignal.emit(self.__progress, "Logging into RetroAchievements.org")
			if not self.__window.retroUser.login():
				self.progressSignal.emit(self.__progress, "Failed to log into RetroAchievements.org!")

		self.__progress = 100
		self.finishedSignal.emit()

class BadgeScanMonitorThread(QThread):

	finishedSignal = pyqtSignal(int, int, int, int, int) # scanned, added, updated, achievements, time taken
	romProcessedSignal = pyqtSignal(int, int, int) # progress (%), unprocessed, time remaining
	badgeProcessedSignal = pyqtSignal(str, str) # name, path
	romsFoundSignal = pyqtSignal(int) # badges found

	def __init__(self, db, retroUser, badgeDir):
		super(BadgeScanMonitorThread, self).__init__(None)
		self.__db = db
		self.__retroUser = retroUser
		self.__badgeDir = badgeDir
		self.__scanThread = None
		self.__running = False
		self.__romTotal = 0
		self.__romsRemaining = 0
		self.__startTime = 0
		self.__threadTotal = multiprocessing.cpu_count() * 2
		self.__threads = []

	def __badgesFoundEvent(self, badgeTotal):
		self.badgesFoundSignal.emit(badgeTotal)

	def __badgeProcessedEvent(self, name, path):
		self.badgeProcessedSignal.emit(name, path)

	def __scanFinishedEvent(self):
		self.__running = False

	def isRunning(self):
		return self.__running

	def __romProcessedEvent(self):
		self.__romsRemaining -= 1
		eta = ((time.time() - self.__startTime) / (self.__romTotal - self.__romsRemaining)) * self.__romTotal
		timeRemaining = eta - (time.time() - self.__startTime)
		self.romProcessedSignal.emit((float(self.__romTotal - self.__romsRemaining) / float(self.__romTotal)) * 100.0, self.__romsRemaining, timeRemaining)

	def run(self):
		logging.debug("BadgeScanMonitorThread.run: starting")
		self.__startTime = time.time()
		processQueue = queue.Queue()

		query = doQuery(self.__db, "SELECT DISTINCT(`retroachievement_game_id`) FROM `game` WHERE `retroachievement_game_id` > 0;")
		self.__romTotal = 0
		while query.next():
			record = query.record()
			processQueue.put(record.value(0))
			self.__romTotal += 1
		logging.debug("BadgeScanMonitorThread.run: found %d games to process" % self.__romTotal)
		self.__romsRemaining = self.__romTotal
		self.romsFoundSignal.emit(self.__romTotal)
		self.__threads = []

		for i in range(0, self.__threadTotal):
			t = BadgeScanWorkerThread(i, self.__db, self.__retroUser, processQueue, self.__badgeDir)
			t.romProcessedSignal.connect(self.__romProcessedEvent)
			t.badgeProcessedSignal.connect(self.__badgeProcessedEvent)
			self.__threads.append(t)
			t.start()

		for t in self.__threads:
			t.wait()

		timeTaken = time.time() - self.__startTime

		added = 0
		updated = 0
		earned = 0

		for t in self.__threads:
			added += t.getAdded()
			updated += t.getUpdated()
			earned += t.getEarned()

		logging.info("BadgeScanMonitorThread: added %d and updated %d badges in %ds" % (added, updated, timeTaken))

		self.romProcessedSignal.emit(100, 0, 0)
		self.finishedSignal.emit(self.__romTotal, added, updated, earned, timeTaken)

		logging.debug("BadgeScanMonitorThread.run: finished")

	@pyqtSlot()
	def startThread(self):
		logging.debug("BadgeScanMonitorThread.startThread: starting thread")
		self.start()

	@pyqtSlot()
	def stop(self):
		for t in self.__threads:
			logging.debug("BadgeScanMonitorThread.stop: stopping thread %d" % t.getId())
			t.stop()

class RomScanMonitorThread(QThread):

	finishedSignal = pyqtSignal(int, int, int, int) # scanned, added, updated, time taken
	progressSignal = pyqtSignal(int, int, int, str, str) # progress (%), unprocessed, time remaining, name, covert art path
	romsFoundSignal = pyqtSignal(int) # roms found

	def __init__(self, db, romScraper):
		super(RomScanMonitorThread, self).__init__(None)
		self.__romScraper = romScraper
		self.__consoleMap = {}
		self.__db = db
		self.__scanThread = None
		self.__running = False

	def __romsFoundEvent(self, romTotal):
		self.romsFoundSignal.emit(romTotal)

	def __scanFinishedEvent(self):
		self.__running = False

	def isRunning(self):
		return self.__running

	def run(self):
		logging.debug("RomScanMonitorThread.run: starting")
		self.__running = True
		self.__scanThread.start()

		romName = ""
		coverArtPath = "0"

		while self.__running:
			lastRom = self.__scanThread.getLastRom()
			if lastRom:
				romName = lastRom[0]
				coverArtPath = lastRom[1]
			self.progressSignal.emit(self.__scanThread.getProgress(), self.__scanThread.getUnprocessed(), self.__scanThread.getTimeRemaining(), romName, coverArtPath)
			time.sleep(0.1)

		self.progressSignal.emit(100, 0, 0, "", "0")

		logging.debug("RomScanMonitorThread.run: finished")
		self.finishedSignal.emit(self.__scanThread.getRomTotal(), self.__scanThread.getAdded(), self.__scanThread.getUpdated(), self.__scanThread.getTimeTaken())
		#self.__running = False

	def setConsoleMap(self, consoleMap):
		self.__consoleMap = consoleMap

	@pyqtSlot(list)
	def startThread(self, consoleNames):
		logging.debug("RomScanMonitorThread.startThread: starting thread")
		if self.__scanThread != None:
			self.__scanThread.romsFoundSignal.disconnect()
			self.__scanThread.finishedSignal.disconnect()
		self.__scanThread = RomScanThread(self.__db, consoleNames, self.__consoleMap, self.__romScraper)
		self.__scanThread.romsFoundSignal.connect(self.__romsFoundEvent)
		self.__scanThread.finishedSignal.connect(self.__scanFinishedEvent)
		self.start()

	def setScraper(self, scraper):
		if scraper not in pes.romScrapers:
			raise Exception("Unknown ROM scraper: \"%s\"" % scraper)
		self.__romScraper = scraper

	@pyqtSlot()
	def stop(self):
		if self.__scanThread:
			self.__scanThread.stop()


class CallHandler(QObject):

	exitSignal = pyqtSignal()
	joysticksConnectedSignal = pyqtSignal(int)
	retroAchievementsLoggedInSignal = pyqtSignal()

	def __init__(self, window):
		super(CallHandler, self).__init__()
		self.__window = window
		self.__keyboardLayout = None
		self.__keyboardLayouts = None
		self.__timezones = None
		self.__timezone = None
		if self.__window.retroUser:
			self.__window.retroUser.loggedInSignal.connect(self.__retroUserLoggedIn)

	@pyqtSlot(result=bool)
	def controllerConnected(self):
		return self.__window.controllerConnected()

	@pyqtSlot()
	def channelReady(self):
		self.__window.channelReady()

	@pyqtSlot()
	def exit(self):
		logging.debug("CallHandler: exit")
		self.exitSignal.emit()

	def emitJoysticksConnected(self, n):
		self.joysticksConnectedSignal.emit(n)

	@pyqtSlot(result=list)
	def getConsoles(self):
		consoles = []
		for c in self.__window.consoles:
			consoles.append({"gameTotal": c.getGameTotal(), "name": c.getName(), "id": c.getId(), "image": c.getImage()})
		return consoles

	@pyqtSlot(str)
	def getIpAddress(self):
		return getIpAddress()

	@pyqtSlot(result=str)
	def getKeyboardLayout(self):
		rtn, stdout, stderr = runCommand(self.__window.getKeyboardLayoutCommand)
		if rtn != 0:
			logging.error("Handler.getKeyboardLayout: could not get current keyboard layout!")
			logging.error(stderr)
		else:
			self.__keyboardLayout = stdout[:-1].strip()
			logging.debug("Handler.getKeyboardLayout: current keyboard layout is: %s" % self.__keyboardLayout)
		return self.__keyboardLayout

	@pyqtSlot(result=list)
	def getKeyboardLayouts(self):
		if self.__keyboardLayouts == None:
			rtn, stdout, stderr = runCommand(self.__window.listKeyboardLayoutsCommand)
			if rtn != 0:
				logging.error("Handler.getKeyboardLayouts: could not get keyboard layouts")
				logging.error(stderr)
			else:
				self.__keyboardLayouts = stdout.split("\n")[:-1]
				logging.debug("Handler.getKeyboardLayouts: found %d keyboard layouts" % len(self.__keyboardLayouts))
		return self.__keyboardLayouts

	@pyqtSlot(int, int, result=list)
	def getLastPlayed(self, limit=10, consoleId=None):
		logging.debug("Handler.getLastPlayed: called")
		games = []
		if consoleId:
			for g in self.__window.consoleIdMap[consoleId].getLastPlayed(limit):
				games.append(g.toDic())
			return games
		query = doQuery(self.__window.db, "SELECT * FROM `game` WHERE `last_played` != 0 ORDER BY `last_played` DESC LIMIT %d;" % limit)
		games = []
		while query.next():
			record = query.record()
			g = GameRecord(self.__window.db, record.value("game_id"), record)
			games.append(g.toDic())
		return games

	@pyqtSlot(int, int, result=list)
	def getLatestAdditions(self, limit=10, consoleId=None):
		logging.debug("Handler.getLatestAdditions: called")
		games = []
		if consoleId:
			for g in self.__window.consoleIdMap[consoleId].getLatestAdditions(limit):
				games.append(g.toDic())
			return games
		query = doQuery(self.__window.db, "SELECT * FROM `game` ORDER BY `added` DESC LIMIT %d;" % limit)
		games = []
		while query.next():
			record = query.record()
			g = GameRecord(self.__window.db, record.value("game_id"), record)
			games.append(g.toDic())
		return games

	@pyqtSlot(result=QVariant)
	def getVersionInfo(self):
		return {"number": pes.VERSION_NUMBER, "date": pes.VERSION_DATE}

	@pyqtSlot(result=str)
	def getTimezone(self):
		if self.__timezone == None:
			rtn, stdout, stderr = runCommand(self.__window.getTimezoneCommand)
			if rtn != 0:
				logging.error("Handler.getTimezone: could not get current timezone from: %s" % self.__window.getTimezoneCommand)
				logging.error("stdout:")
				logging.error(stdout)
				logging.error("stderr:")
				logging.error(stderr)
			else:
				self.__timezone = stdout[:-1]
				logging.debug("Handler.getTimezone: current timezone is: %s" % self.__timezone)
		return self.__timezone

	@pyqtSlot(result=list)
	def getTimezones(self):
		if self.__timezones == None:
			rtn, stdout, stderr = runCommand(self.__window.listTimezoneCommand)
			if rtn != 0:
				logging.error("Handler.getTimezones: could not get timezones from: %s" % self.__window.listTimezoneCommand)
				logging.error("stdout:")
				logging.error(stdout)
				logging.error("stderr:")
				logging.error(stderr)
			else:
				self.__timezones = stdout.split("\n")[:-1]
				logging.debug("Handler.getTimezones: found %d timezones" % len(self.__timezones))
		return self.__timezones

	@pyqtSlot(int, result=QVariant)
	def play(self, gameId):
		logging.debug("Handler.play: game ID %d" % gameId)
		game = GameRecord(self.__window.db, gameId)
		console = self.__window.consoleIdMap[game.getConsoleId()]
		for f in console.getRequiredFiles():
			if not os.path.exists(f):
				logging.warning("Handler.play: %s is required" % f)
				return {"success": False, "msg": "%s is required to play %s" % (f, game.getName())}
		emulator = console.getEmulator()
		logging.debug("Handler.play: using \"%s\" emulator" % emulator)
		joystickTotal = sdl2.joystick.SDL_NumJoysticks()
		logging.debug("Handler.play: %d joystick(s) found" % joystickTotal)
		if emulator == "RetroArch":
			# note: RetroArch uses a SNES control pad button layout, SDL2 uses XBOX 360 layout!
			# check joystick configs
			if joystickTotal > 0:
				for i in range(joystickTotal):
					if sdl2.SDL_IsGameController(i):
						c = sdl2.SDL_GameControllerOpen(i)
						if sdl2.SDL_GameControllerGetAttached(c):
							# get joystick name
							j = sdl2.SDL_GameControllerGetJoystick(c)
							jsName = sdl2.SDL_JoystickName(j).decode()
							jsConfig = os.path.join(pes.userRetroArchJoysticksConfDir, "%s.cfg" % jsName)
							logging.debug("Handler.play: joystick config file: %s" % jsConfig)
							vendorId, productId = getJoystickDeviceInfoFromGUID(getJoystickGUIDString(sdl2.SDL_JoystickGetDeviceGUID(i)))
							with open(jsConfig, 'w') as f:
								# control pad id etc.
								f.write("input_device = \"%s\"\n" % jsName)
								f.write("input_vendor_id = \"%s\"\n" % vendorId)
								f.write("input_product_id = \"%s\"\n" % productId)
								# buttons
								f.write(getRetroArchConfigButtonValue("input_a", c, sdl2.SDL_CONTROLLER_BUTTON_B))
								f.write(getRetroArchConfigButtonValue("input_b", c, sdl2.SDL_CONTROLLER_BUTTON_A))
								f.write(getRetroArchConfigButtonValue("input_x", c, sdl2.SDL_CONTROLLER_BUTTON_Y))
								f.write(getRetroArchConfigButtonValue("input_y", c, sdl2.SDL_CONTROLLER_BUTTON_X))
								f.write(getRetroArchConfigButtonValue("input_start", c, sdl2.SDL_CONTROLLER_BUTTON_START))
								f.write(getRetroArchConfigButtonValue("input_select", c, sdl2.SDL_CONTROLLER_BUTTON_BACK))
								# shoulder buttons
								f.write(getRetroArchConfigButtonValue("input_l", c, sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER))
								f.write(getRetroArchConfigButtonValue("input_r", c, sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER))
								f.write(getRetroArchConfigAxisValue("input_l2", c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT))
								f.write(getRetroArchConfigAxisValue("input_r2", c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT))
								# L3/R3 buttons
								f.write(getRetroArchConfigButtonValue("input_l3", c, sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK))
								f.write(getRetroArchConfigButtonValue("input_r3", c, sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK))
								# d-pad buttons
								f.write(getRetroArchConfigButtonValue("input_up", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP))
								f.write(getRetroArchConfigButtonValue("input_down", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN))
								f.write(getRetroArchConfigButtonValue("input_left", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT))
								f.write(getRetroArchConfigButtonValue("input_right", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT))
								# axis
								f.write(getRetroArchConfigAxisValue("input_l_x", c, sdl2.SDL_CONTROLLER_AXIS_LEFTX, True))
								f.write(getRetroArchConfigAxisValue("input_l_y", c, sdl2.SDL_CONTROLLER_AXIS_LEFTY, True))
								f.write(getRetroArchConfigAxisValue("input_r_x", c, sdl2.SDL_CONTROLLER_AXIS_RIGHTX, True))
								f.write(getRetroArchConfigAxisValue("input_r_y", c, sdl2.SDL_CONTROLLER_AXIS_RIGHTY, True))
								# hot key buttons
								bind = sdl2.SDL_GameControllerGetBindForButton(c, sdl2.SDL_CONTROLLER_BUTTON_GUIDE)
								if bind:
									f.write(getRetroArchConfigButtonValue("input_enable_hotkey", c, sdl2.SDL_CONTROLLER_BUTTON_GUIDE))
								else:
									f.write(getRetroArchConfigButtonValue("input_enable_hotkey", c, sdl2.SDL_CONTROLLER_BUTTON_BACK))
								f.write(getRetroArchConfigButtonValue("input_exit_emulator", c, sdl2.SDL_CONTROLLER_BUTTON_START))
								f.write(getRetroArchConfigButtonValue("input_save_state", c, sdl2.SDL_CONTROLLER_BUTTON_A))
								f.write(getRetroArchConfigButtonValue("input_load_state", c, sdl2.SDL_CONTROLLER_BUTTON_B))
								f.write("input_pause_toggle = \"nul\"\n")
						sdl2.SDL_GameControllerClose(c)
			# @TODO: create cheevos file if the user has RetroAchievements credentials
		elif emulator == "Mupen64Plus":
			if joystickTotal > 0:
				if not os.path.exists(pes.userMupen64PlusConfFile):
					return { "success": False, "msg": "Could not open %s" % pes.userMupen64PlusConfFile }
				player1Controller = self.__window.getPlayer1Controller()
				player1ControllerIndex = self.__window.getPlayer1ControllerIndex()
				configParser = configparser.SafeConfigParser()
				configParser.optionxform = str # make options case sensitive
				configParser.read(pes.userMupen64PlusConfFile)
				bind = sdl2.SDL_GameControllerGetBindForButton(player1Controller, sdl2.SDL_CONTROLLER_BUTTON_GUIDE)
				if bind:
					hotkey = getMupen64PlusConfigButtonValue(player1Controller, sdl2.SDL_CONTROLLER_BUTTON_GUIDE, True)
				else:
					hotkey = getMupen64PlusConfigButtonValue(player1Controller, sdl2.SDL_CONTROLLER_BUTTON_BACK, True)
				if configParser.has_section('CoreEvents'):
					configParser.set('CoreEvents', 'Joy Mapping Stop', 'J%d%s/%s' % (player1ControllerIndex, hotkey, getMupen64PlusConfigButtonValue(player1Controller, sdl2.SDL_CONTROLLER_BUTTON_START, True)))
					configParser.set('CoreEvents', 'Joy Mapping Save State', 'J%d%s/%s' % (player1ControllerIndex, hotkey, getMupen64PlusConfigButtonValue(player1Controller, sdl2.SDL_CONTROLLER_BUTTON_A, True)))
					configParser.set('CoreEvents', 'Joy Mapping Load State', 'J%d%s/%s' % (player1ControllerIndex, hotkey, getMupen64PlusConfigButtonValue(player1Controller, sdl2.SDL_CONTROLLER_BUTTON_B, True)))
				else:
					logging.error("Handler.play: could not find \"CoreEvents\" section in %s" % pes.userMupen64PlusConfFile)
					return { "success": False, "msg": "Could not find \"CoreEvents\" section in %s" % pes.userMupen64PlusConfFile}

				# loop through each joystick that is connected and save to button config file
				# note: max of 4 control pads for this emulator
				joystickTotal = sdl2.joystick.SDL_NumJoysticks()
				if joystickTotal > 0:
					counter = 1
					for i in range(joystickTotal):
						if sdl2.SDL_IsGameController(i):
							c = sdl2.SDL_GameControllerOpen(i)
							if sdl2.SDL_GameControllerGetAttached(c):
								j = sdl2.SDL_GameControllerGetJoystick(c)
								jsName = sdl2.SDL_JoystickName(j)
								logging.debug("PESApp.playGame: generating Mupen64Plus config for joystick %d: %s" % (i, jsName))
								section = 'Input-SDL-Control%d' % (i + 1)
								if configParser.has_section(section):
									configParser.set(section, 'device', "%d" % i)
									configParser.set(section, 'name', '"%s"' % jsName)
									configParser.set(section, 'plugged', 'True')
									configParser.set(section, 'mouse', 'False')
									configParser.set(section, 'mode', '0') # this must be set to 0 for the following values to take effect
									configParser.set(section, 'DPad R', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT))
									configParser.set(section, 'DPad L', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT))
									configParser.set(section, 'DPad D', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN))
									configParser.set(section, 'DPad U', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP))
									configParser.set(section, 'Start', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_START))
									configParser.set(section, 'Z Trig', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER))
									configParser.set(section, 'B Button', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_B))
									configParser.set(section, 'A Button', getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_A))
									configParser.set(section, 'C Button R', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTX, positive=True))
									configParser.set(section, 'C Button L', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTX, positive=False))
									configParser.set(section, 'C Button D', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTY, positive=True))
									configParser.set(section, 'C Button U', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTY, positive=False))
									configParser.set(section, 'L Trig', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT))
									configParser.set(section, 'R Trig', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT))
									configParser.set(section, 'X Axis', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_LEFTX, both=True))
									configParser.set(section, 'Y Axis', getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_LEFTY, both=True))
							sdl2.SDL_GameControllerClose(c)
						counter += 1
						if counter == 4:
							break

				logging.debug("Handler.play: writing Mupen64Plus config to %s" % pes.userMupen64PlusConfFile)
				with open(pes.userMupen64PlusConfFile, 'w') as f:
					configParser.write(f)

				widthRe = re.compile("((window|framebuffer)[ ]+width[ ]*)=[ ]*[0-9]+")
				heightRe = re.compile("((window|framebuffer)[ ]+height[ ]*)=[ ]*[0-9]+")
				dimensions = QDesktopWidget().screenGeometry()
				# now update gles2n64.conf file to use current resolution
				output = ""
				with open(pes.userGles2n64ConfFile, 'r') as f:
					for line in f:
						result = re.sub(widthRe, r"\1=%d" % dimensions.width(), line)
						if result != line:
							output += result
						else:
							result = re.sub(heightRe, r"\1=%d" % dimensions.height(), line)
							if result != line:
								output += result
							else:
								output += line
				logging.debug("Handler.play: writing gles2n64 config to %s" % pes.userGles2n64ConfFile)
				with open(pes.userGles2n64ConfFile, 'w') as f:
					f.write(output)
		elif emulator == "vice":
			# @TODO: write Vice config
			pass
		else:
			return {"success": False, msg: "Unsupported emulator \"%s\"" % emulator}

		game.incrementPlayCount()
		game.setLastPlayed()
		game.save()
		command = console.getLaunchString(game)
		self.__window.closeAndRun(command)
		return {"success": True}

	def __retroUserLoggedIn(self):
		self.retroAchievementsLoggedInSignal.emit()

	@pyqtSlot(str, str, result=QVariant)
	def saveSettings(self, timezone, keyboardLayout):
		rtn, stdout, stderr = runCommand("%s %s" % (self.__window.setTimezoneCommand, timezone))
		if rtn != 0:
			logging.error("Handler.saveSettings: could not set timezone to %s" % timezone)
			logging.error(stderr)
			return {"success": False, "msg": "Could not set timezone to %s" % timezone}
		rtn, stdout, stderr = runCommand("%s %s" % (self.__window.setKeyboardLayoutCommand, keyboardLayout))
		if rtn != 0:
			logging.error("Handler.saveSettings: could not set keyboard layout to %s" % keyboardLayout)
			logging.stderr(stderr)
			return {"success": False, "msg": "Could not set keyboard layout to %s" % keyboardLayout}
		return {"success": True}

class WebPage(QWebEnginePage):

	def javaScriptConsoleMessage(self, level, msg, linenumber, source_id):
		if level == 0:
			logging.debug("JS console: %s %d: %s" % (source_id, linenumber, msg))
		elif level == 1:
			logging.warning("JS console: %s %d: %s" % (source_id, linenumber, msg))
		else:
			logging.error("JS console: %s %d: %s" % (source_id, linenumber, msg))

	def loadFinished(self, ok):
		if ok:
			logging.debug("WebPage.loadFinished: loaded")

class WebView(QWebEngineView):

	def __init__(self):
		super(WebView, self).__init__()
		self.loadFinished.connect(self.__loadFinished)
		self.setFocusPolicy(Qt.StrongFocus)

	def __loadFinished(self, result):
		logging.debug("WebView: finished loading: %s" % self.__page.url().toString())

	def setPage(self, page):
		self.__page = page
		super(WebView, self).setPage(page)
