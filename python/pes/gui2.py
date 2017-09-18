import datetime
import logging
import os
import sys

from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QLabel, QWidget, QVBoxLayout, QFrame, QPushButton
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, QFile, QIODevice, QObject, QEvent
from PyQt5.QtWebChannel import *

import sdl2
import sdl2.ext
import sdl2.joystick

import pes
from pes.data import Settings
from pes.common import checkDir, checkFile, getIpAddress, pesExit
import pes.gamecontroller

class PESWindow2(QMainWindow):
	
	def __init__(self, app, settings, fullscreen=False):
		super(PESWindow2, self).__init__()
		self.__app = app
		self.__running = False
		self.__settings = settings
		self.__player1Controller = None
		
		if sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER) != 0:
			pesExit("failed to initialise SDL2!", True)
		logging.debug("SDL2 joystick and gamecontroller APIs initialised")
			
		# load joystick database
		logging.debug("loading SDL2 control pad mappings from: %s" % pes.userGameControllerFile)
		mappingsLoaded = sdl2.SDL_GameControllerAddMappingsFromFile(pes.userGameControllerFile.encode())
		if mappingsLoaded == -1:
			pesExit("failed to load SDL2 control pad mappings from: %s" % pes.userGameControllerFile)
		logging.debug("loaded %d control pad mappings" % mappingsLoaded)
		
		#mainGrid = QGridLayout()
		
		w = QWidget()
		w.setStyleSheet("background-color: rgb(30, 30, 30); color: rgb(233, 233, 233); font-size: 14pt;")
		
		vBoxLayout = QVBoxLayout()
		w.setLayout(vBoxLayout)
		
		headerBoxLayout = QHBoxLayout()
		timeLabel = QLabel(datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y"), w)
		headerBoxLayout.addWidget(QLabel("Pi Entertainment System", w))
		headerBoxLayout.addStretch(1)
		headerBoxLayout.addWidget(timeLabel)
		
		#frame = QFrame()
		#frame.setLayout(headerBoxLayout)
		#frame.setStyleSheet("QFrame {border-bottom: 2px solid rgb(204, 123, 25)}")
		
		buttonNames = [ "Mega Drive", "NES", "SNES", "ZX Spectrum", "Power Off", "Exit"]
		
		
		menuBoxLayout = QVBoxLayout()
		menuBoxLayout.addStretch(1)
		for s in buttonNames:
			menuBoxLayout.addWidget(QPushButton(s, w))
		menuBoxLayout.addStretch(1)
		
		mainBoxLayout = QHBoxLayout()
		mainBoxLayout.addLayout(menuBoxLayout)
		mainBoxLayout.addStretch(1)
		
		vBoxLayout.addLayout(headerBoxLayout)
		vBoxLayout.addLayout(mainBoxLayout)
		#vBoxLayout.addWidget(frame)
		#vBoxLayout.addStretch(1)
		
		
		self.setCentralWidget(w)
		
		if fullscreen:
			self.showFullScreen()
		else:
			self.setGeometry(0, 0, 1024, 768)
			self.show()
	
	def close(self):
		logging.info("exiting PES")
		logging.debug("stopping event loop")
		self.__running = False
		logging.debug("shutting down SDL2")
		sdl2.SDL_Quit()
		logging.debug("closing")
		super(PESWindow2, self).close()
		
	def closeEvent(self, event):
		logging.debug("PESWindow: closeEvent")
		self.__running = False
		super(PESWindow2, self).closeEvent(event)
		
	def controllerConnected(self):
		return self.__player1Controller != None
	
	def event(self, event):
		if event.type() == QEvent.KeyRelease:
			if event.key() == Qt.Key_Escape:
				logging.debug("QMainWindow.event: escape key pressed")
				self.__running = False
				self.close()
				return True
		return super(PESWindow2, self).event(event)
	
	def __handleExit(self):
		self.close()
	
	def run(self):
		self.__running = True
		while self.__running:
			# process SDL events
			events = sdl2.ext.get_events()
			for event in events:
				if event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
					if sdl2.SDL_IsGameController(event.cdevice.which):
						logging.debug("control pad: \"%s\" connected" % event.cdevice.which)
						if self.__player1Controller == None:
							self.__player1Controller = sdl2.SDL_GameControllerOpen(event.cdevice.which)
				elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
					if event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
						logging.debug("player 1: up")
						#self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Up, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
						logging.debug("player 1: down")
						#self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Down, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_A:
						logging.debug("player 1: A")
						#self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Return, Qt.NoModifier))
					elif event.cbutton.button == sdl2.SDL_CONTROLLER_BUTTON_B:
						logging.debug("player 1: B")
						#self.__app.postEvent(self.__webview.focusProxy(), QKeyEvent(QEvent.KeyRelease, Qt.Key_Backspace, Qt.NoModifier))
			
			self.__app.processEvents()
			
	
