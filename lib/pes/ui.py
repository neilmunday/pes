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

from ctypes import c_int, c_uint32, byref
import logging
import sdl2
import sdl2.sdlimage
import sdl2.joystick
import sdl2.video
import sdl2.render
import sdl2.sdlgfx
import sdl2.sdlttf

def createText(renderer, font, txt, colour, wrap=0):
	if wrap > 0:
		surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font, txt, colour, wrap)
	else:
		surface = sdl2.sdlttf.TTF_RenderText_Blended(font, txt, colour)
	texture = sdl2.SDL_CreateTextureFromSurface(renderer, surface)
	sdl2.SDL_FreeSurface(surface)
	return texture

def getFontHeight(font):
	return sdl2.sdlttf.TTF_FontHeight(font)

def getTextureDimensions(texture):
	flags = c_uint32()
	access = c_int()
	w = c_int()
	h = c_int()
	ret = sdl2.SDL_QueryTexture(texture, byref(flags), byref(access), byref(w), byref(h))
	return (w.value, h.value)

def renderLines(renderer, font, lines, colour, x, y, wrap):
	w = 0
	totalHeight = 0
	for l in lines:
		(w, h) = renderText(renderer, font, l, colour, x, y, wrap)
		y += h
		totalHeight += h
	return (w, totalHeight)

def renderText(renderer, font, txt, colour, x, y, wrap=0, width=0):
	texture = createText(renderer, font, txt, colour, wrap)
	(w, h) = getTextureDimensions(texture)
	if width > 0 and w > width:
		dotTexture = createText(renderer, font, '...', colour)
		(tw, th) = getTextureDimensions(dotTexture)
		sdl2.SDL_RenderCopy(renderer, texture, sdl2.SDL_Rect(0, 0, width - tw, h), sdl2.SDL_Rect(x, y, width - tw, h))
		sdl2.SDL_RenderCopy(renderer, dotTexture, None, sdl2.SDL_Rect(x + (width - tw), y, tw, th))
		sdl2.SDL_DestroyTexture(texture)
		sdl2.SDL_DestroyTexture(dotTexture)
	else:
		sdl2.SDL_RenderCopy(renderer, texture, None, sdl2.SDL_Rect(x, y, w, h))
		sdl2.SDL_DestroyTexture(texture)
	return (w, h)

def getScaleImageDimensions(texture, bx, by):
	"""
	Original author: Frank Raiser (crashchaos@gmx.net)
	URL: http://www.pygame.org/pcr/transform_scale
	Modified by Neil Munday
	"""
	ix, iy = getTextureDimensions(texture)
	if ix > iy:
		# fit to width
		scale_factor = bx/float(ix)
		sy = scale_factor * iy
		if sy > by:
			scale_factor = by/float(iy)
			sx = scale_factor * ix
			sy = by
		else:
			sx = bx
	else:
		# fit to height
		scale_factor = by/float(iy)
        	sx = scale_factor * ix
		if sx > bx:
			scale_factor = bx/float(ix)
			sx = bx
			sy = scale_factor * iy
		else:
			sy = by
	return (int(sx),int(sy))

class UIObject(object):
	
	def __init__(self, renderer, x, y, width, height):
		self.renderer = renderer
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.visible = True
	
	def destroy(self):
		pass
	
	def draw(self):
		pass
	
	def setAlpha(self, alpha):
		if alpha < 0 or alpha > 255:
			raise ValueError("Invalid alpha value!")
		self.alpha = alpha
	
	def setCoords(self, x, y):
		self.x = x
		self.y = y
		
	def setSize(self, w, h):
		self.width = w
		self.height = h
		
	def setVisible(self, visible):
		self.visible = visible
		
class Label(UIObject):
	
	def __init__(self, renderer, x, y, text, font, colour, wrap=0, fixedWidth=0):
		self.__truncate = False
		txtWidth = c_int()
		txtHeight = c_int()
		sdl2.sdlttf.TTF_SizeText(font, text, txtWidth, txtHeight)
		if fixedWidth > 0:
			if txtWidth.value > width:
				self.__truncate = True
		else:
			width = txtWidth.value
		super(Label, self).__init__(renderer, x, y, width, txtHeight.value)
		self.__font = font
		self.__colour = colour
		self.__wrap = wrap
		self.__texture = None
		self.__text = text
		self.__fixedWidth = fixedWidth
		
	def draw(self):
		if self.visible:
			if self.__texture == None:
				if self.__wrap > 0:
					surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.__wrap)
				else:
					surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
				self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
				sdl2.SDL_FreeSurface(surface)
				(w, h) = getTextureDimensions(self.__texture)
				self.w = w
				self.h = h
				
			sdl2.SDL_RenderCopy(self.renderer, self.__texture, None, sdl2.SDL_Rect(self.x, self.y, self.w, self.h))
			
	def destroy(self):
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None
			
	def setAlpha(self, alpha):
		super(Label, self).setAlpha(alpha)
		sdl2.SDL_SetTextureAlphaMod(self.__texture, alpha)
			
	def setText(self, text):
		if text == self.__text:
			return
		if self.__texture != None:
			sdl2.SDL_DestroyTexture(self.__texture)
		
		self.__text = text
		txtWidth = c_int()
		txtHeight = c_int()
		sdl2.sdlttf.TTF_SizeText(self.__font, self.__text, txtWidth, txtHeight)
		
		if self.__wrap > 0:
			surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.__wrap)
		else:
			surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
		self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
		sdl2.SDL_FreeSurface(surface)
		(w, h) = getTextureDimensions(self.__texture)
		self.w = w
		self.h = h

class ProgressBar(UIObject):
	
	def __init__(self, renderer, x, y, width, height, colour, backgroundColour):
		super(ProgressBar, self).__init__(renderer, x, y, width, height)
		self.__progress = 0.0 # percent complete
		self.__colour = colour
		self.__backgroundColour = backgroundColour
		logging.debug("ProgressBar.init: initialised")
	
	def draw(self):
		if self.visible:
			margin = 3
			w = int(self.width * (self.__progress / 100.0))
			sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__backgroundColour.r, self.__backgroundColour.g, self.__backgroundColour.b, 255)
			sdl2.sdlgfx.boxRGBA(self.renderer, self.x + margin, self.y + margin, self.x + w - margin, self.y + self.height - margin, self.__colour.r, self.__colour.g, self.__colour.b, 255)
	
	def setProgress(self, p):
		if p > 100:
			raise ValueError("%d is greater than 100" % p)
		if p < 0:
			raise ValueError("%d is less than 0" % p)
		self.__progress = p
		
class Thumbnail(UIObject):
	
	__cache = {} # shared texture cache
	
	def __init__(self, renderer, x, y, width, height, game, font, txtColour):
		self.__font = font
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__thumbWidth = width
		self.__thumbHeight = height
		height += 1 + self.__fontHeight # allow space for label
		super(Thumbnail, self).__init__(renderer, x, y, width, height)
		self.__txtColour = txtColour
		self.__game = game
		self.__coverart = game.getCoverArt()
		if self.__coverart == None:
			self.__coverart = game.getConsole().getNoCoverArtImg()
		self.__coverartTexture = None
		logging.debug("Thumbnail.init: initialised for %s" % game.getName())
		
	def draw(self):
		if self.visible:
			if self.__coverartTexture == None:
				gameId = self.__game.getId()
				if gameId in self.__cache:
					self.__coverartTexture = self.__cache[gameId]
				else:
					logging.debug("Thumbnail.draw: loading texture for %s" % self.__game.getName())
					self.__coverartTexture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, self.__coverart)
					self.__cache[gameId] = self.__coverartTexture
					#logging.debug("Thumbnail.draw: drawing at (%d, %d) dimensions (%d, %d)" % (self.x, self.y, self.__thumbWidth, self.__thumbHeight))
			sdl2.SDL_RenderCopy(self.renderer, self.__coverartTexture, None, sdl2.SDL_Rect(self.x, self.y, self.__thumbWidth, self.__thumbHeight))
			# render text underneath
			renderText(self.renderer, self.__font, self.__game.getName(), self.__txtColour, self.x, self.y + self.__thumbHeight + 1, 0, self.width)
		
	@staticmethod
	def destroyTextures():
		logging.debug("Thumbnail.destroyTextures: purging %d textures..." % len(Thumbnail.__cache))
		keys = []
		for key, value in Thumbnail.__cache.iteritems():
			sdl2.SDL_DestroyTexture(value)
			keys.append(key)
		for k in keys:
			del Thumbnail.__cache[k]