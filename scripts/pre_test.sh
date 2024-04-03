#!/bin/bash -ex

target_image=$1
nr_cpus=$2

ssh $SSH_USER@$MACHINE grubby --update-kernel=$target_image --args=nr_cpus=$nr_cpus
