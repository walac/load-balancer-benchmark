#!/bin/bash -vex
#
# Install and configure the machine in which we run the benchmark
#

yum install -y \
    python3-pyyaml \
    python3-bcc \
    rteval \
    tuned-profiles-realtime \
    python3-pip

pip3 install sortedcontainers

echo isolated_cores= >> /etc/tuned/realtime-variables.conf

systemctl start tuned
tuned-adm profile realtime

mkdir /root/json
