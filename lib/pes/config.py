import ConfigParser
import logging
import os
from pes import *

class PESConfig(object):

	def __init__(self, configFile):
		logging.debug("PESConfig.__init__: using %s" % configFile)

		self.__configFile = configFile
		self.__configParser = ConfigParser.ConfigParser()
		self.__configParser.read(self.__configFile)

		userHome = os.path.expanduser('~')

		# sanity checks
		sections = ['settings', 'commands', 'colours', 'font', 'layout']
		for s in sections:
			if not self.__configParser.has_section(s):
				raise Exception("Section %s missing from %s" % (s, self.__configFile))

		# pes settings
		self.cecEnabled = self.__configParser.getboolean('settings', 'hdmi-cec')
		self.romsDir = self.__configParser.get('settings', 'romsDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.coverartDir = self.__configParser.get('settings', 'coverartDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.badgeDir = self.__configParser.get('settings', 'badgeDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.biosDir = self.__configParser.get('settings', 'biosDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.kodiDir = self.__configParser.get('settings', 'kodiDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.screenSaverTimeout = self.__configParser.getint('settings', 'screenSaverTimeout')
		self.desiredResolution = (self.__configParser.getint('settings', 'desiredScreenWidth'), self.__configParser.getint('settings', 'desiredScreenHeight'))

		# colour settings
		self.backgroundColour = self.__processColour(self.__configParser.get("colours", "background").split(','))
		self.menuBackgroundColour = self.__processColour(self.__configParser.get("colours", "menuBackground").split(','))
		self.headerBackgroundColour = self.__processColour(self.__configParser.get("colours", "headerBackground").split(','))
		self.lineColour = self.__processColour(self.__configParser.get("colours", "line").split(','))
		self.menuTextColour = self.__processColour(self.__configParser.get("colours", "menuText").split(','))
		self.menuSelectedTextColour = self.__processColour(self.__configParser.get("colours", "menuSelectedText").split(','))
		self.textColour = self.__processColour(self.__configParser.get("colours", "text").split(','))
		self.lightBackgroundColour = self.__processColour(self.__configParser.get("colours", "lightBackground").split(','))

		# font settings
		self.fontFile = self.__configParser.get("font", "fontFile").replace('%%BASE%%', baseDir)
		self.fontSizes = {}
		self.fontSizes['splash'] = self.__configParser.getint("font", "splashSize")
		self.fontSizes['title'] = self.__configParser.getint("font", "titleSize")
		self.fontSizes['body'] = self.__configParser.getint("font", "bodySize")
		self.fontSizes['smallBody'] = self.__configParser.getint("font", "smallBodySize")
		self.fontSizes['header'] = self.__configParser.getint("font", "headerSize")
		self.fontSizes['menu'] = self.__configParser.getint("font", "menuSize")

		for f, s in self.fontSizes.iteritems():
			if s < 1:
				raise ValueError("Font size %d for \"%s\" is too small!", (s, f))

		# coverart settings
		self.coverartSize = self.__configParser.getfloat("settings", "coverartSize")
		self.coverartCacheLen = self.__configParser.getint("settings", "coverartCacheLen")

		# icon settings
		self.iconCacheLen = self.__configParser.getint("settings", "iconCacheLen")

		# layout
		self.headerHeight = self.__configParser.getint("layout", "headerHeight")
		self.menuWidth = self.__configParser.getint("layout", "menuWidth")

		# command settings
		self.shutdownCommand = self.__configParser.get("commands", "shutdown")
		self.rebootCommand = self.__configParser.get("commands", "reboot")
		self.listTimezonesCommand = self.__configParser.get("commands", "listTimezones")
		self.setTimezoneCommand = self.__configParser.get("commands", "setTimezone")
		self.getTimezoneCommand = self.__configParser.get("commands", "getTimezone")
		if self.__configParser.has_option("commands", "kodi"):
			self.kodiCommand = self.__configParser.get("commands", "kodi")
		else:
			logging.warning("PESConfig.init: Kodi command not found, disabling Kodi menu item")
			self.kodiCommand = None

		# RetroAchievements settings
		if self.__configParser.has_section("RetroAchievements"):
			self.retroAchievementsUserName = self.__configParser.get("RetroAchievements", "username")
			self.retroAchievementsPassword = self.__configParser.get("RetroAchievements", "password")
			self.retroAchievementsApiKey = self.__configParser.get("RetroAchievements", "apiKey")
			if self.__configParser.has_option("RetroAchievements", "hardcore"):
				self.retroAchievementsHardcore = self.__configParser.getboolean("RetroAchievements", "hardcore")
			else:
				self.retroAchievementsHardcore = False

			if len(self.retroAchievementsUserName) == 0 or len(self.retroAchievementsPassword) == 0 or len(self.retroAchievementsApiKey) == 0:
				self.retroAchievementsUserName = None
				self.retroAchievementsPassword = None
				self.retroAchievementsApiKey = None
		else:
			self.retroAchievementsUserName = None
			self.retroAchievementsPassword = None
			self.retroAchievementsApiKey = None

		logging.debug("PESConfig.__init__: initialised ok!")

	@staticmethod
	def __processColour(colour):
		if len(colour) != 3:
			raise ValueError("processColour: colour array does not contain 3 elements!")
		rtn = []
		for c in colour:
			try:
				rtn.append(int(c))
			except ValueError as e:
				raise ValueError("processColour: %s is not an integer for colour: %s!" % (c, colour))
		return rtn

	def save(self):
		logging.info("Saving PES config to %s" % self.__configFile)
		with open(self.__configFile, 'wb') as f:
			self.__configParser.write(f)

	def set(self, section, option, value):
		self.__configParser.set(section, option, value)
