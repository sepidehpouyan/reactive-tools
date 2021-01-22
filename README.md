# reactive-tools

Tools for Authentic Execution work. [Website](https://people.cs.kuleuven.be/~jantobias.muehlberg/stm17/)

## Support

Currently, the following architectures are supported:

- Sancus
- Intel SGX
- Normal computers ("No-SGX", for testing purposes)

### Extending support for new architectures

See [here](add_new_architectures.md)

## Requirements

### Target devices

**Sancus**

- [Reactive application](https://github.com/fritzalder/sancus-riot/tree/reactive-app/sancus-testbed/reactive)
  - Event Manager & Module Loader running on top of RIOT OS port for Sancus

**Intel SGX**

- [Rust](https://www.rust-lang.org/tools/install) - to run the event manager
- [Fortanix EDP](https://edp.fortanix.com/docs/installation/guide/) - to run SGX enclaves
- [Event Manager](https://github.com/gianlu33/rust-sgx-apps)

**Native**

- [Rust](https://www.rust-lang.org/tools/install) - to run the event manager
- [Event Manager](https://github.com/gianlu33/rust-sgx-apps)

### Deployer

**Note**: you only need to install the dependencies of the architectures you are interested in.

- e.g. if your system only works with Sancus devices, you don't need Fortanix EDP

**Sancus**

- [Sancus compiler](https://distrinet.cs.kuleuven.be/software/sancus/install.php)
  - You also need to add to add the python library to `PYTHONPATH`
    - `export PYTHONPATH=$PYTHONPATH:/usr/local/share/sancus-compiler/python/lib/`

**Intel SGX/Native**

- Rust & Fortanix EDP
- [`rust-sgx-gen`](https://github.com/gianlu33/rust-sgx-gen/) - code generation tool

- [Utility apps](https://github.com/gianlu33/rust-sgx-apps) - `aes_encryptor`, `ra_client` and `ra_sp`
  - needed for connection key encryption and remote attestation
  - Simply run the `install_deployer.sh` script in the `apps` folder
- See [here](sgx.md) for more details

## Run

Install `reactive-tools` by running `pip install .` from the root folder.

### Deploy an Authentic Execution network

**Inputs**

- Code for each module
- JSON file describing the configuration of the system
- see [examples](examples)

**Command**

Run `reactive-tools deploy -h` for more information

**Output**

- If everything goes well, your modules will be automatically loaded inside the nodes you specified, and connections will be established!
- If you specified an output file (`--result <file>`), the final configuration will be saved in a JSON format (which includes all information you may need such as keys, binaries, etc)

### Call an entrypoint

**Inputs**

- Result JSON of the `deploy` command
- Module and entry name
- Optional argument (hex byte array)

**Command**

Run `reactive-tools call -h` for more information

**Output**

- If everything goes well, the entrypoint is correctly called
