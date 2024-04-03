#!/bin/bash -ex

root_dir=$1
build_dir=$2

pushd $root_dir/drv
make -C $build_dir M=$root_dir/drv
popd
scp $root_dir/scripts/lb_bench.py $SSH_USER@$MACHINE:/usr/bin
scp $root_dir/drv/lb_profiler.ko $SSH_USER@$MACHINE:/root
