#!/bin/bash -ex

duration=$1
output_dir=$2

ssh ${SSH_USER}@${MACHINE} insmod /root/lb_profiler.ko
ssh ${SSH_USER}@${MACHINE} lb_bench.py -d $duration -o $output_dir
