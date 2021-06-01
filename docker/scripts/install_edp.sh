#!/bin/bash

set -eux

# add target
rustup default nightly
rustup target add x86_64-fortanix-unknown-sgx --toolchain nightly

# Install utilities
apt-get update && apt-get install -y --no-install-recommends pkg-config libssl-dev protobuf-compiler
cargo install fortanix-sgx-tools sgxs-tools

# Configure Cargo integration with EDP
mkdir -p $HOME/.cargo
echo -e '[target.x86_64-fortanix-unknown-sgx]\nrunner = "ftxsgx-runner-cargo"' >> $HOME/.cargo/config
