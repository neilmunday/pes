#
#    This file is part of the Pi Entertainment System (PES).
#
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
import subprocess
import sys

from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, QFile, QIODevice, QObject, QEvent, QThread
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtWebChannel import QWebChannel

import time

import sdl2
import sdl2.ext
import sdl2.joystick

import pes
from pes.data import Console, ConsoleRecord, Settings
from pes.common import checkDir, checkFile, getIpAddress, mkdir, pesExit
import pes.gamecontroller

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
	# swap from big endian to little endian and covert to an int
	vendorId = int(vendorId.decode('hex')[::-1].encode('hex'), 16)
	productId = int(productId.decode('hex')[::-1].encode('hex'), 16)
	return (vendorId, productId)

def runCommand(command):
	process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	stdout, stderr = process.communicate()
	return (process.returncode, stdout.decode(), stderr.decode())

class PESWindow(QMainWindow):
	
	def __init__(self, app, settings, fullscreen=False):
		super(PESWindow, self).__init__()
		self.__app = app
		self.__running = False
		self.settings = settings
		self.__player1Controller = None
		self.__player1ControllerIndex = None
		self.__controlPadTotal = 0
		self.__dpadAsAxis = False
		self.keyboardLayouts = []
		self.keyboardLayout = ""
		self.timezones = []
		self.timezone = ""
		self.consoles = []
		
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
		
		self.__loadingThread = LoadingThread(self)
		
		self.__page = WebPage()
		self.__webview = WebView() 
		self.__webview.setPage(self.__page)
		self.__channel = QWebChannel(self.__page)
		self.__page.setWebChannel(self.__channel)
		self.__handler = CallHandler(self)
		self.__channel.registerObject('handler', self.__handler)
		self.__channel.registerObject('loadingThread', self.__loadingThread)
		self.__handler.exitSignal.connect(self.__handleExit)
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
		logging.debug("stopping event loop")
		self.__running = False
		logging.debug("shutting down SDL2")
		sdl2.SDL_Quit()
		logging.debug("closing")
		super(PESWindow, self).close()
		
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
		# load time zones
		#process = subprocess.Popen(self.__window.listTimezoneCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		#stdout, stderr = process.communicate()
		#if process.returncode != 0:
			#logging.error("LoadingThread.run: could not get time zones")
			#logging.error(stderr)
		#else:
			#timezones = stdout.decode().split("\n")[:-1]
			#timezoneTotal = len(timezones)
			#i = 0
			#for l in timezones:
				#i += 1
				#logging.debug("LoadingThread.run: found time zone %s" % l)
				#self.__window.timezones.append(l)
				#self.__progress = (i / timezoneTotal) * 100
				#self.progressSignal.emit(self.__progress, "Loading timezone: %s" % l)
		
		## get current timezone
		#process = subprocess.Popen(self.__window.getTimezoneCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		#stdout, stderr = process.communicate()
		#if process.returncode != 0:
			#logging.error("LoadingThread.run: could not get current time zone!")
			#logging.error(stderr)
		#else:
			#self.__window.timezone = stdout[:-1].decode()
			#logging.debug("LoadingThread.run: current timezone is: %s" % self.__window.timezone)
		
		#for i in range(0, 11):
		#	time.sleep(0.1)
		#	self.__progress = 10 * i
		#	self.progressSignal.emit(self.__progress, "%d%%" % self.__progress)
		#	logging.debug("LoadingThread.run: progress -> %d" % self.__progress)
		
		logging.debug("LoadingThread.run: opening database using %s" % pes.userDb)
		db = QSqlDatabase.addDatabase("QSQLITE")
		db.setDatabaseName(pes.userDb)
		db.open()
		
		query = QSqlQuery()
		query.exec_("CREATE TABLE IF NOT EXISTS `console` (`console_id` INTEGER PRIMARY KEY, `gamesdb_id` INT, `retroachievement_id` INT, `name` TEXT);")
		query.exec_("CREATE INDEX IF NOT EXISTS \"console_index\" on consoles (console_id ASC);")
		query.exec_("CREATE TABLE IF NOT EXISTS `games_catalogue` (`short_name` TEXT, `full_name` TEXT);")
		query.exec_("CREATE INDEX IF NOT EXISTS \"games_catalogue_index\" on games_catalogue (short_name ASC);")
		db.commit()
		
		# populate games catalogue (if needed)
		query.exec_("SELECT COUNT(*) AS `total` FROM `games_catalogue`")
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
				self.progress = 50 * (i / sectionTotal)
				self.progressSignal.emit(self.__progress, "Populating games catalogue: %s" % fullName)
			if len(insertValues) > 0:
				query.exec_('INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES %s;' % ','.join(insertValues))
				db.commit()
				
		# load consoles
		consoleParser = configparser.RawConfigParser()
		consoleParser.read(pes.userConsolesConfigFile)
		consoleNames = consoleParser.sections()
		consoleTotal = len(consoleNames)
		consoleNames.sort()
		
		i = 0
		for c in consoleNames:
			try:
				consolePath = os.path.join(self.__window.settings.get("settings", "romsDir"), c)
				mkdir(consolePath)
				#console = Console(db, c)
				#db, name, gamesDbId, retroAchievementId, image, emulator, extensions, ignoreRoms, command, noCoverArt
				
				if consoleParser.has_option(c, "ignore_roms"):
					ignoreRoms = consoleParser.get(c, "ignore_roms").split(",")
				else:
					ignoreRoms = []
					
				retroAchievementId = 0
				if consoleParser.has_option(c, "achievement_id"):
					retroAchievementId = consoleParser.getint(c, "achievement_id")
				
				console = Console(
					db,
					c,
					consoleParser.getint(c, "thegamesdb_id"),
					retroAchievementId,
					consoleParser.get(c, "image"),
					consoleParser.get(c, "emulator"),
					consoleParser.get(c, "extensions"),
					ignoreRoms,
					consoleParser.get(c, "command"),
					consoleParser.get(c, "nocoverart")
				)
				self.__window.consoles.append(console)
			except configparser.NoOptionError as e:
				logging.error("LoadingThread.run: error parsing config file %s: %s" % (pes.userConsolesConfigFile, e.message))
				self.__window.close()
				return
			except ValueError as e:
				logging.error("LoadingThread.run: error parsing config file %s: %s" % (pes.userConsolesConfigFile, e.message))
				self.__window.close()
				return
		
		db.close()
		
		self.__progress = 100
		self.finishedSignal.emit()

class CallHandler(QObject):
	
	exitSignal = pyqtSignal()
	joysticksConnectedSignal = pyqtSignal(int)
	
	def __init__(self, window):
		super(CallHandler, self).__init__()
		self.__window = window
		self.__keyboardLayout = None
		self.__keyboardLayouts = None
		self.__timezones = None
		self.__timezone = None
	
	@pyqtSlot(result=bool)
	def controllerConnected(self):
		return self.__window.controllerConnected()
	
	@pyqtSlot()
	def channelReady(self):
		self.__window.channelReady()
	
	@pyqtSlot(result=list)
	def getConsoles(self):
		consoles = []
		for c in self.__window.consoles:
			consoles.append(c.getName())
		return consoles
	
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
	
	@pyqtSlot(result=str)
	def getTimezone(self):
		if self.__timezone == None:
			rtn, stdout, stderr = runCommand(self.__window.getTimezoneCommand)
			if rtn != 0:
				logging.error("Handler.getTimezone: could not get current timezone!")
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
				logging.error("Handler.getTimezones: could not get timezones")
				logging.error(stderr)
			else:
				self.__timezones = stdout.split("\n")[:-1]
				logging.debug("Handler.getTimezones: found %d timezones" % len(self.__timezones))
		return self.__timezones
	
	@pyqtSlot()
	def exit(self):
		logging.debug("CallHandler: exit")
		self.exitSignal.emit()
		
	@pyqtSlot(str)
	def getIpAddress(self):
		return getIpAddress()
	
	def emitJoysticksConnected(self, n):
		self.joysticksConnectedSignal.emit(n)
		
	@pyqtSlot(str, str, result=list)
	def saveSettings(self, timezone, keyboardLayout):
		rtn, stdout, stderr = runCommand("%s %s" % (self.__window.setTimezoneCommand, timezone))
		if rtn != 0:
			logging.error("Handler.getTimezones: could not set timezones")
			logging.error(stderr)
			return [False, stderr]
		return [True]
	
	@pyqtSlot(str, str)
	def test(self, a, b):
		print("call received: %s, %s" % (a, b))

class WebPage(QWebEnginePage):
	
	def javaScriptConsoleMessage(self, level, msg, linenumber, source_id):
		if level == 0:
			logging.debug("JS console: %s %d: %s" % (source_id, linenumber, msg))
		elif level == 1:
			logging.Warning("JS console: %s %d: %s" % (source_id, linenumber, msg))
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
