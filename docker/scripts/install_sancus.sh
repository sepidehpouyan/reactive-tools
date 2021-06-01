#!/bin/bash

set -eux

function make_repo() {
  cd $1
  mkdir build
  cd build
  cmake .. -DSECURITY=$2 -DMASTER_KEY=$3
  make
  make install
  cd ..
  cd ..
}

apt-get update && apt-get install -y make git lsb-release screen unzip

export DEBIAN_FRONTEND=noninteractive

git clone https://github.com/sancus-tee/sancus-main.git
cd sancus-main
make install_deps
make install SANCUS_SECURITY=$1 SANCUS_KEY=$2

# patch sancus-support and sancus-compiler
# TODO remove this as soon as these patches are merged into main repo
cd ..
git clone https://github.com/gianlu33/sancus-compiler.git
git clone https://github.com/gianlu33/sancus-support.git

make_repo "sancus-compiler" $1 $2
make_repo "sancus-support" $1 $2
