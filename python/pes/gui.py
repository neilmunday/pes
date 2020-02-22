import datetime
import logging
import os
import sys

import sdl2
import sdl2.ext
import sdl2.joystick

from PyQt5.QtGui import QGuiApplication, QKeyEvent
from PyQt5.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, QFile, QIODevice, QObject, QEvent, QThread, QVariant, QTimer

import sqlalchemy.orm

import pes
import pes.sql
from pes.common import checkDir, checkFile, initConfig, mkdir, ConsoleSettings

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

class BackEnd(QObject):

	closeSignal = pyqtSignal()
	controlPadButtonPress = pyqtSignal(int, arguments=['button'])
	homeButtonPress = pyqtSignal()
	populateDbProgress = pyqtSignal(int, arguments=['progress'])

	def __init__(self, parent=None):
		super(BackEnd, self).__init__(parent)
		self.__populateDb = False
		logging.debug("Backend.__init__: connecting to database: %s" % pes.userDb)
		engine = pes.sql.connect()
		session = sqlalchemy.orm.sessionmaker(bind=engine)()
		pes.sql.createAll(engine)
		logging.info("Backend.__init__: loading console definitions from: %s" % pes.userConsolesConfigFile)
		consoleSettings = ConsoleSettings(pes.userConsolesConfigFile)

		for c in consoleSettings.getSections():
			logging.debug("Backend.__init__: processing: %s" % c)
			options = consoleSettings.getOptions(c)
			if "achievement_id" in options:
				console = pes.sql.Console(name=c, gamesDbId=options["thegamesdb_id"], retroId=options["achievement_id"])
			else:
				console = pes.sql.Console(name=c, gamesDbId=options["thegamesdb_id"])
			session.add(console)

		session.commit()

	@pyqtSlot()
	def close(self):
		self.closeSignal.emit()

	def emitHomeButtonPress(self):
		self.homeButtonPress.emit()

	def emitControlPadButtonPress(self, button):
		self.controlPadButtonPress.emit(button)

	@pyqtSlot()
	def populateDb(self):
		logging.debug("Backend: beginning population of PES database")

	@pyqtSlot(result=bool)
	def getPopulateDb(self):
		return self.__populateDb

	@pyqtSlot(result=str)
	def getTime(self):
		return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

	def setPopulateDb(self, populateDb):
		self.__populateDb = populateDb

class PESGuiApplication(QGuiApplication):

	def __init__(self, argv, populateDb):
		super(PESGuiApplication, self).__init__(argv)
		self.__populateDb = populateDb
		self.__running = True
		self.__player1Controller = None
		self.__player1ControllerIndex = None
		self.__controlPadTotal = 0
		self.__engine = None
		self.__backend = BackEnd()
		self.__backend.setPopulateDb(self.__populateDb)
		self.__backend.closeSignal.connect(self.close)
		self.__engine = QQmlApplicationEngine()
		self.__engine.rootContext().setContextProperty("backend", self.__backend)
		logging.debug("loading QML from: %s" % pes.qmlMain)
		self.__engine.load(pes.qmlMain)

	def close(self):
		logging.debug("closing")
		self.__running = False
		sdl2.SDL_Quit()
		self.exit()

	def run(self):
		joystickTick = sdl2.timer.SDL_GetTicks()

		while self.__running:
			events = sdl2.ext.get_events()
			for event in events:
				print("processing event")
				if event.type == sdl2.SDL_CONTROLLERBUTTONUP:
					if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
						logging.debug("player 1: up")
						self.sendEvent(self.focusWindow(), QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
						logging.debug("player 1: down")
						self.sendEvent(self.focusWindow(), QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
						logging.debug("player 1: left")
						self.sendEvent(self.focusWindow(), QKeyEvent(QEvent.KeyPress, Qt.Key_Left, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
						logging.debug("player 1: right")
						self.sendEvent(self.focusWindow(), QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_A:
						logging.debug("player 1: A")
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_B:
						logging.debug("player 1: B")
						self.sendEvent(self.focusWindow(), QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_GUIDE:
						logging.debug("player 1: Guide")
						#self.sendEvent(self.focusWindow(), QKeyEvent(QEvent.KeyPress, Qt.Key_Home, Qt.NoModifier))
						self.__backend.emitHomeButtonPress()

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
									self.__updateControlPad(self.__player1ControllerIndex)
									close = False
							if close:
								sdl2.SDL_GameControllerClose(c)
				else:
					self.__player1Controller = None
					self.__player1ControllerIndex = None
				if self.__controlPadTotal != controlPadTotal:
					self.__controlPadTotal = controlPadTotal
					#self.__handler.emitJoysticksConnected(self.__controlPadTotal)
				joystickTick = tick

			self.processEvents()

	def __updateControlPad(self, jsIndex):
		if jsIndex == self.__player1ControllerIndex:
			# hack for instances where a dpad is an axis
			bind = sdl2.SDL_GameControllerGetBindForButton(self.__player1Controller, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP)
			if bind:
				if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
					self.__dpadAsAxis = True
					logging.debug("PESWindow.updateControlPad: enabling dpad as axis hack")
				else:
					self.__dpadAsAxis = False
