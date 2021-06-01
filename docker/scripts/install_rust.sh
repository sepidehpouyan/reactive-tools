#!/bin/bash

set -eux

apt-get update && apt-get install -y --no-install-recommends ca-certificates gcc libc6-dev wget

url="https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init"
wget "$url"
chmod +x rustup-init
./rustup-init -y --no-modify-path --default-toolchain nightly
chmod -R a+w $RUSTUP_HOME $CARGO_HOME
apt-get remove -y --auto-remove wget
rm -rf /var/lib/apt/lists/*
