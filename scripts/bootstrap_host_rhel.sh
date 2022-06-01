#!/bin/bash -vex

dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm

yum group install -y "Development Tools"

yum install -y \
    python3-jinja2 \
    python3-pyyaml \
    bc \
    tmux \
    dwarves \
    openssl \
    openssl-devel \
    conserver-client
