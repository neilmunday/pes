# BerryBoot

This guide will tell you how to create a an image file that you can use with [BerryBoot](http://www.berryterminal.com/doku.php/berryboot) from the standard PES images.

## Overview

[BerryBoot](http://www.berryterminal.com/doku.php/berryboot) is very neat boot loader for the Raspberry Pi that allows you to install multiple operating systems onto your Raspberry Pi. The operating systems can be installed via the Internet or from USB storage. BerryBoot images use the SquashFS format and are therefore a lot smaller than the equivalent SD card images available for PES.

To convert a PES image into a BerryBoot image you will need to perform the following steps:

1. Remove the mounting of the root file system from */etc/fstab*.
2. Edit */home/pi/.bash_pes* to prevent the creation of the */data* FAT32 partition.
3. Remove the */home/pi/pes* symbolic link.
4. Install BerryBoot to your SD card.
5. Install the PES BerryBoot image.

## Requirements

To perform the conversion you will need the following:

* Access to a PC running Linux or a Linux virtual machine with root privileges.
* A copy of a PES image.
* A SD card
* A USB storage device

## Fix-Up PES Image

### Mount Image

Run the following commands as the root user or via `sudo` to mount the image so that we can edit it:

```
gunzip pes-2.2-BETA-2017-05-21-rpi2-3.img.gz
losetup /dev/loop0 pes-2.2-BETA-2017-05-21-rpi2-3.img
partprobe /dev/loop0
mount /dev/loop0 /mnt
```

### Modify /etc/fstab

Remove the mounting of the root file system from */etc/fstab*:

```
sudo sed -i 's/^\/dev\/mmcblk/#\0/g' /mnt/etc/fstab
```

### Update /home/pi/.bash_pes

We now need to update */home/pi/.bash_pes* in the image so that the */data* partition is not created. This is because each BerryBoot operating system can only have one partition.

Therefore **remove** the following lines from */mnt/home/pi/.bash_pes* and save the file:

```
if [ ! -d /data/pes ]; then
	echo "Setting up /data partition - this will use all available space on your SD card!"
	sudo /opt/sbin/make_rom_partition.py -v -d /dev/mmcblk0
	sudo systemctl restart smbd.service
fi
```

### Remove /home/pi/pes symblic link

```
rm /mnt/home/pi/pes
```

## Create image

**Note:** At this point the PES image should still be mounted.

From your home directory for example, run the following command:

```
mksquashfs /mnt pes-2.2-BETA-2017-05-21-rpi2-3-berryboot.img256 -comp lzo -e lib/modules
```

You can umount the PES image:

```
umount /mnt
```

Now copy the PES BerryBoot image to your USB storage device.

## Install BerryBoot

Download the latest version of BerryBoot and write it to your SD card.

***Note:*** It is assumed that you have already mounted your SD card at `/mnt` in this example:

```
wget http://downloads.sourceforge.net/project/berryboot/berryboot-20170527-pi0-pi1-pi2-pi3.zip
mkdir berryboot
cd berryboot
7z e ../berryboot-20170527-pi0-pi1-pi2-pi3.zip
cp -r ./* /mnt/
umount /mnt
```

Now insert your SD card, a keyboard, mouse and USB storage device into your Raspberry Pi and turn it on.

Follow the onscreen instructions to [install BerryBoot](http://www.berryterminal.com/doku.php/berryboot).

## Install PES BerryBoot Image

Once you get to the BerryBoot menu editor screen proceed as follows:

1. Hold down the left mouse button on the *Add OS* menu button and select *Install from USB stick*
2. Select the PES BerryBoot image, e.g. pes-2.2-BETA-2017-05-21-rpi2-3-berryboot.img256
3. Once installed select *Edit Config* and go to the *config.txt* and change the GPU memory to 384.

Now you can click *Exit* to reboot your Rapsberry Pi. Once rebooted you should now see the PES BerryBoot image as an OS that you can boot.

Your installation is now complete.

## Further Reading

* http://www.berryterminal.com/doku.php/berryboot/adding_custom_distributions
