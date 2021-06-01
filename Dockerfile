FROM ubuntu:18.04

WORKDIR /usr/src/install

## Python ##
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl python3.6 python3-distutils git make \
    && echo -e '#!/bin/bash\npython3.6 "$@"' > /usr/bin/python && chmod +x /usr/bin/python \
    && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py

## Rust ##
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

COPY docker/scripts/install_rust.sh .
RUN ./install_rust.sh

## EDP ##
COPY docker/scripts/install_edp.sh .
RUN ./install_edp.sh

ARG DUMMY1=0

## Sancus ##
ENV PYTHONPATH=\$PYTHONPATH:/usr/local/share/sancus-compiler/python/lib/
ARG SANCUS_SECURITY=128
ARG SANCUS_KEY=deadbeefcafebabec0defeeddefec8ed

COPY docker/scripts/install_sancus.sh .
RUN ./install_sancus.sh $SANCUS_SECURITY $SANCUS_KEY

## SGX attestation stuff ##
COPY docker/sgx-attester /bin/sgx-attester
RUN apt-get update && apt-get install -y --no-install-recommends clang gcc-multilib

ARG DUMMY=0

## reactive-tools, finally ##
COPY . .
RUN pip install . && rm -rf /usr/src/install

WORKDIR /usr/src/app
