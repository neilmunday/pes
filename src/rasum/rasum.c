/*
    This file is part of the Pi Entertainment System (PES).

    PES provides an interactive GUI for games console emulators
    and is designed to work on the Raspberry Pi.

    Copyright (C) 2020 Neil Munday (neil@mundayweb.com)

    PES is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PES is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PES.  If not, see <http://www.gnu.org/licenses/>.

    Description:

    This program takes a ROM and calculates its RetroAchivements.org hash value.

    Use the -t option to specify the ROM type (nes, snes, genesis or generic).
    If not specified, then "generic" is assumed.

    Acknowledgements:

    This program relies heavily on the methods used by https://github.com/libretro/RetroArch/blob/master/cheevos.c
*/

#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <openssl/md5.h>

#define CHEEVOS_6MB   (6 * 1024 * 1024)
#define CHEEVOS_8MB   (8 * 1024 * 1024)

typedef unsigned char uint8_t;

static unsigned next_power_of_2(unsigned n){
   n--;
   n |= n >> 1;
   n |= n >> 2;
   n |= n >> 4;
   n |= n >> 8;
   n |= n >> 16;
   return n + 1;
}

int gameHash(FILE *ptr, MD5_CTX *context){
	uint8_t buffer[4096];
	int read = 0;
	int size = 0;

	while(1){
		read = fread(buffer, sizeof(uint8_t), 4096, ptr);
		size += read;

		MD5_Update(context, buffer, read);

		if (read < 4096){
			break;
		}
	}
	return size;
}

void padHash(int fill, MD5_CTX *context){
	uint8_t buffer[4096];
	memset((void*)buffer, 0, sizeof(buffer));
	while (fill > 0){
		int len = sizeof(buffer);
		if (len > fill){
			len = fill;
		}
		MD5_Update(context, (void*)buffer, len);
		fill -= len;
	}
}

void genesisHash(FILE *ptr, MD5_CTX *context){
	int size = gameHash(ptr, context);
	padHash(CHEEVOS_6MB - size, context);
}

void snesHash(FILE *ptr, MD5_CTX *context){
	int size = gameHash(ptr, context);
	padHash(CHEEVOS_8MB - size, context);
}

void nesHash(FILE *ptr, MD5_CTX *context){
	struct {
		uint8_t id[4];
		uint8_t rom_size;
		uint8_t vrom_size;
		uint8_t rom_type;
		uint8_t rom_type2;
		uint8_t reserve[8];
	} header;
	int romSize;
	int read = fread((void*)&header, sizeof(header), 1, ptr);
	if (read == 0){
			fprintf(stderr, "Could not read ROM!");
			exit(1);
	}
	if (header.id[0] != 'N' || header.id[1] != 'E' || header.id[2] != 'S' || header.id[3] != 0x1a){
			fprintf(stderr, "This is not a valid NES ROM!\n");
			exit(1);
	}
	if (header.rom_size){
		romSize = next_power_of_2(header.rom_size);
	}
	else{
		romSize = 256;
	}
	unsigned bytes;
	int i, mapper_no;
	int not_power2[] =
	{
		53, 198, 228
	};
	int round = 1;
	uint8_t * data = (uint8_t *) malloc(romSize << 14);
	if (!data){
		fprintf(stderr, "malloc failed for NES ROM\n");
		exit(1);
	}
	memset(data, 0xFF, romSize << 14);
	mapper_no = (header.rom_type >> 4);
	mapper_no |= (header.rom_type2 & 0xF0);
	for (i = 0; i != sizeof(not_power2) / sizeof(not_power2[0]); ++i){
		if (not_power2[i] == mapper_no) {
			round = 0;
			break;
		}
	}
	if (header.rom_type & 4){
		fseek(ptr, SEEK_SET, sizeof(header));
	}

	bytes = (round == 1) ? romSize : header.rom_size;
	read = fread((void*)data, 0x4000, bytes, ptr);

	if (read <= 0){
		fprintf(stderr, "Read failed for NES ROM!\n");
		exit(1);
	}

	MD5_Update(context, (void*) data, romSize << 14);
}

int main(int argc, char **argv){
	int c;
	char *romFile = NULL;
	char *romType = "generic";

	while ((c = getopt (argc, argv, "ht:")) != -1){
		switch(c){
			case 't':
				romType = optarg;
				break;
			case 'h':
				printf("rasum [-t nes|snes|genesis|generic] ROM_PATH\n\nUse the -t option to specify the ROM type (nes, snes, genesis or generic).\nIf not specified, then \"generic\" is assumed.\n");
				return 0;
			case '?':
				if (optopt == 't'){
					fprintf(stderr, "Option -%c requires a ROM type (generic, nes, snes or genesis).\n", optopt);
				}
				else if (isprint(optopt)){
					fprintf(stderr, "Unknown option -%c'\n", optopt);
				}
				else{
					fprintf(stderr, "Unknown option character '\\%x'.\n", optopt);
				}
				return 1;
			default:
				abort();
		}
	}

	if (optind == argc){
		fprintf(stderr, "Rom file path not specified!\n");
		return 1;
	}

	romFile = argv[optind];

	FILE *ptr;

	ptr = fopen(romFile, "rb");
	if (!ptr)
	{
		fprintf(stderr, "Unable to open file: %s\n", romFile);
		return 1;
	}

	MD5_CTX context;
	MD5_Init(&context);

	if (strcmp(romType, "nes") == 0){
		nesHash(ptr, &context);
	}
	else if (strcmp(romType, "snes") == 0){
		snesHash(ptr, &context);
	}
	else if (strcmp(romType, "genesis") == 0){
		genesisHash(ptr, &context);
	}
	else if (strcmp(romType, "generic") == 0){
		gameHash(ptr, &context);
	}
	else{
		fprintf(stderr, "Unsupported ROM type: \"%s\"\n", romType);
		return 1;
	}

	unsigned char digest[16];
	MD5_Final(digest, &context);
	char *out = (char*)malloc(33);
	for (int n = 0; n < 16; ++n) {
		snprintf(&(out[n*2]), 16*2, "%02x", (unsigned int)digest[n]);
	}
	printf("%s\n", out);
	return 0;
}
