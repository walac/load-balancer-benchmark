#!/bin/bash -vex

yum group install -y "Development Tools"

yum install -y \
    python3-jinja2 \
    python3-pyyaml \
    bc \
    tmux \
    dwarves \
    openssl \
    openssl-devel
