#!/bin/bash -vex

yum install -y \
    python3-pyyaml \
    python3-bcc \
    rteval \
    tuned-profiles-realtime

echo isolated_cores= >> /etc/tuned/realtime-variables.conf

systemctl start tuned
tuned-adm profile realtime
