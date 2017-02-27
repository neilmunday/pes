import ConfigParser
import logging
import os
from pes import *

class PESConfig(object):
	
	def __init__(self, configFile):
		logging.debug("PESConfig.__init__: using %s" % configFile)
		
		configParser = ConfigParser.ConfigParser()
		configParser.read(configFile)
		
		userHome = os.path.expanduser('~')
		
		# sanity checks
		sections = ['settings', 'commands', 'colours', 'font', 'layout']
		for s in sections:
			if not configParser.has_section(s):
				raise Exception("Section %s missing from %s" % (s, configFile))
			
		# pes settings
		self.cecEnabled = configParser.getboolean('settings', 'hdmi-cec')
		self.romsDir = configParser.get('settings', 'romsDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.coverartDir = configParser.get('settings', 'coverartDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.badgeDir = configParser.get('settings', 'badgeDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.biosDir = configParser.get('settings', 'biosDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
		self.screenSaverTimeout = configParser.getint('settings', 'screenSaverTimeout')
			
		# colour settings
		self.backgroundColour = self.__processColour(configParser.get("colours", "background").split(','))
		self.menuBackgroundColour = self.__processColour(configParser.get("colours", "menuBackground").split(','))
		self.headerBackgroundColour = self.__processColour(configParser.get("colours", "headerBackground").split(','))
		self.lineColour = self.__processColour(configParser.get("colours", "line").split(','))
		self.menuTextColour = self.__processColour(configParser.get("colours", "menuText").split(','))
		self.menuSelectedTextColour = self.__processColour(configParser.get("colours", "menuSelectedText").split(','))
		self.textColour = self.__processColour(configParser.get("colours", "text").split(','))
		self.lightBackgroundColour = self.__processColour(configParser.get("colours", "lightBackground").split(','))
		
		# font settings
		self.fontFile = configParser.get("font", "fontFile").replace('%%BASE%%', baseDir)
		self.fontSizes = {}
		self.fontSizes['splash'] = configParser.getint("font", "splashSize")
		self.fontSizes['title'] = configParser.getint("font", "titleSize")
		self.fontSizes['body'] = configParser.getint("font", "bodySize")
		self.fontSizes['smallBody'] = configParser.getint("font", "smallBodySize")
		self.fontSizes['header'] = configParser.getint("font", "headerSize")
		self.fontSizes['menu'] = configParser.getint("font", "menuSize")
		
		for f, s in self.fontSizes.iteritems():
			if s < 1:
				raise ValueError("Font size %d for \"%s\" is too small!", (s, f))
		
		# coverart settings
		self.coverartSize = configParser.getfloat("settings", "coverartSize")
		self.coverartCacheLen = configParser.getint("settings", "coverartCacheLen")
		
		# icon settings
		self.iconCacheLen = configParser.getint("settings", "iconCacheLen")
		
		# layout
		self.headerHeight = configParser.getint("layout", "headerHeight")
		self.menuWidth = configParser.getint("layout", "menuWidth")
		
		# command settings
		self.shutdownCommand = configParser.get("commands", "shutdown")
		self.rebootCommand = configParser.get("commands", "reboot")
		self.listTimezonesCommand = configParser.get("commands", "listTimezones")
		self.setTimezoneCommand = configParser.get("commands", "setTimezone")
		self.getTimezoneCommand = configParser.get("commands", "getTimezone")
		if configParser.has_option("commands", "kodi"):
			self.kodiCommand = configParser.get("commands", "kodi")
		else:
			logging.warning("PESConfig.init: Kodi command not found, disabling Kodi menu item")
			self.kodiCommand = None
		
		# RetroAchievements settings
		if configParser.has_section("RetroAchievements"):
			self.retroAchievementsUserName = configParser.get("RetroAchievements", "username")
			self.retroAchievementsPassword = configParser.get("RetroAchievements", "password")
			self.retroAchievementsApiKey = configParser.get("RetroAchievements", "apiKey")
			
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
			except ValueError, e:
				raise ValueError("processColour: %s is not an integer for colour: %s!" % (c, colour))
		return rtn
