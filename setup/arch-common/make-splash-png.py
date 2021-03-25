#!/usr/bin/env python2

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014-2021 Neil Munday (neil@mundayweb.com)
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

import argparse
import ConfigParser
import os
import PIL
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import sys

sys.path.append(os.path.abspath('%s/../../lib' % os.path.dirname(os.path.realpath(__file__))))

from pes import *
from pes.config import PESConfig
from pes.util import checkFile

def errorExit(msg):
	print msg
	sys.exit(1)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Creates a "splash screen" image for PES in PNG format.', add_help=True)
	parser.add_argument('-o', '--output-file', help='Name of the file to write to', type=str, dest='output')
	args = parser.parse_args()

	if not args.output:
		errorExit("Output file not specified!")

	if os.path.exists(args.output):
		errorExit("%s already exists!" % args.output)

	logoPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'archlinux-logo.png')
	if not os.path.exists(logoPath):
		errorExit("Could not find: %s" % logoPath)

	pesConfFile = os.path.join(confDir, 'pes', 'pes.ini')
	checkFile(pesConfFile)

	try:
		pesConfig = PESConfig(userPesConfigFile)
	except ConfigParser.NoOptionError, e:
		errorExit(e.message)
	except ValueError, e:
		errorExit(e.message)

	width = 1920
	height = 1080
	gap = 100
	text = "Pi Entertainment System %s" % VERSION_NUMBER

	font = ImageFont.truetype(pesConfig.fontFile, pesConfig.fontSizes['splash'])
	img = Image.new("RGBA", (width, height), (pesConfig.backgroundColour[0], pesConfig.backgroundColour[1], pesConfig.backgroundColour[2]))

	archLogo = Image.open(logoPath, 'r')
	archLogoWidth, archLogoHeight = archLogo.size

	draw = ImageDraw.Draw(img)
	textWidth, textHeight = draw.textsize(text, font=font)
	textCoords = ((width - textWidth) / 2, (height - (textHeight + archLogoHeight + gap)) / 2)

	draw.text(textCoords, text, (pesConfig.textColour[0], pesConfig.textColour[1], pesConfig.textColour[2]), font=font)
	draw = ImageDraw.Draw(img)

	offset = ((width - archLogoWidth) / 2, textCoords[1] + textHeight + gap)
	img.paste(archLogo, offset, archLogo)

	try:
		img.save(args.output)
	except Exception as e:
		errorExit("Unable to save %s: %s" % (args.output, e.message))

	sys.exit(0)
