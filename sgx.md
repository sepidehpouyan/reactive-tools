# Reactive tools for SGX

## Modules

See [`rust-sgx-gen`](https://github.com/gianlu33/rust-sgx-gen/tree/master) documentation and our [examples](examples) to learn how to create a SGX (or No-SGX) module.

## Nodes

An [Event Manager](https://github.com/gianlu33/rust-sgx-apps/tree/master) must be running on each node.

- We can have multiple event managers (and nodes) on the same machine, but pay attention to the specified ports!
  - The modules will use a port based on the one assigned to the Event Manager
  - E.g. if the EM listens to port 5000, SM1 will listen to port 5001, SM2 to 5002, etc..
  - As a consequence, you need to assign ports to Event Managers on the same machine with a certain interval (e.g. 5000, 6000, etc.)

## Limitations

At the moment, SGX modules can be only deployed in `debug` mode.

## Remote Attestation

Remote Attestation (RA) is the process where the deployer can verify that a remote module is correctly loaded inside a node and not tampered with. During the process, data can also be exchanged, such as a symmetric key for future communication.

**Links**

- [Intel official website](https://software.intel.com/content/www/us/en/develop/topics/software-guard-extensions/attestation-services.html)
- [Intel sample code](https://software.intel.com/content/www/us/en/develop/articles/code-sample-intel-software-guard-extensions-remote-attestation-end-to-end-example.html)

- [The Rust framework we used](https://github.com/ndokmai/rust-sgx-remote-attestation)

### Reactive-tools

The RA process is automatically handled by the framework.

The deployer just needs to specify, for each module in the JSON input file, the following information:

**`vendor_key`**

- Path (**absolute!**) to the vendor's private key. It is used to sign the SGX module
- The private key can be generated using `openssl` 
  - e.g. `openssl genrsa -3 3072 > my_key.pem`
- See https://edp.fortanix.com/docs/tasks/deployment/ for more information

**`ra_settings`**

- A configuration JSON file used by `ra_sp` in order to retrieve the configuration about  [SGX EPID](https://api.portal.trustedservices.intel.com/EPID-attestation).
  - See [here](https://github.com/ndokmai/rust-sgx-remote-attestation#how-to-build-and-run) for more information
- Just update the [template](settings_template.json) provided in this repository by changing the following fields:
  - `spid`
  - `primary_subscription_key`
  - `secondary_subscription_key`
    - these fields are retrieved in your Intel's account after you subscribe for a _Product DEV Intel® Software Guard Extensions Attestation Service (Linkable) subscription_
  - `ias_root_cert_pem_path`
    - Path (**absolute!**) to Intel's Root Certificate
    - it can be downloaded from [this link](https://certificates.trustedservices.intel.com/Intel_SGX_Attestation_RootCA.pem). 