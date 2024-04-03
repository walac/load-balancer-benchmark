#!/bin/bash -ex

kernel_version=$1
target_image=$2
grub_menu=$3

ssh $SSH_USER@$MACHINE /usr/bin/dracut -f /boot/initramfs-$kernel_version.img $kernel_version

ssh $SSH_USER@$MACHINE /usr/sbin/grubby \
    --add-kernel=$target_image \
    --copy-default \
    --title=$grub_menu \
    --initrd=/boot/initramfs-$kernel_version.img
