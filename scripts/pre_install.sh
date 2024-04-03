#!/bin/bash -xe

localversion=$1

ssh $SSH_USER@$MACHINE "rm -rf \
    /boot/*$localversion* \
    /boot/loader/entries/*$localversion* \
    /lib/modules/*$localversion* rteval-* \
    "
