# reactive-tools

Deployment tools for the [Authentic Execution framework](https://github.com/gianlu33/authentic-execution)

## Support

Currently, the following architectures are supported:

- Sancus
- SGX
- Native (no TEE support, run natively)

[Extending support for new architectures](add_new_architectures.md)

[Tutorial: develop an Authentic Execution application](https://github.com/gianlu33/authentic-execution/blob/master/docs/tutorial-develop-apps.md)

### Limitations

- Currently, SGX modules can only be deployed in debug mode

## Dependencies & installation

- [Full list of dependencies](https://github.com/gianlu33/authentic-execution/blob/master/docs/install-from-sources.md)

```bash
# Install reactive-tools - you must be at the root of this repository
pip install .
```

## Run reactive-tools with Docker

The [gianlu33/reactive-tools](https://hub.docker.com/repository/docker/gianlu33/reactive-tools) Docker images provide a simple and fast way to run reactive-tools from any Linux OS. We provide different tags, according to the developer needs:

- `latest` contains all the dependencies for all the architectures supported
- `sgx` contains the dependencies to deploy only SGX and native modules
- `native` contains dependencies to deploy only native modules
- `sancus` contains dependencies to deploy only Sancus modules

When running the Docker image, ideally you should mount a volume that includes the workspace of the application to be deployed, containing all the source files and the deployment descriptor.

```bash
# run reactive-tools image
### <volume>: volume we want to mount (ideally, contains the workspace of our app)
### <tag>: tag of the image we want to run between {latest,sgx,sancus,native}
make run VOLUME=<volume> TAG=<tag>
```

## Run

All of the following commands can be run with either the `--verbose` or `--debug` flags, for debugging purposes. For a full description of the arguments, run `reactive-tools -h`.

### Build

```bash
# Build the application. Might be useful to check that all the modules compile before the actual deployment
### <workspace>: root directory of the application to deploy. Default: "."
### <config>: name of the input deployment descriptor, should be inside <workspace>
reactive-tools build --workspace <workspace> <config>
```

### Deploy
```bash
# Deploy the application
### <workspace>: root directory of the application to deploy. Default: "."
### <config>: name of the deployment descriptor, should be inside <workspace>
### <result>: path to the output deployment descriptor that will be generated (optional)
reactive-tools deploy --workspace <workspace> <config> --result <result>
```

### Call
```bash
# Call a specific entry point of a deployed application
### <config>: deployment descriptor. MUST be the output of a previous deploy command
### <module_name>: name of the module we want to call
### <entry_point>: either the name or the ID of th entry point we want to call
### <arg>: byte array in hexadecimal format, e.g., "deadbeef" (OPTIONAL)
reactive-tools call --config <config> --module <module_name> --entry <entry_point> --arg <arg>
```

### Output
```bash
# Trigger the output of a _direct_ connection
### <config>: deployment descriptor. MUST be the output of a previous deploy command
### <connection>: either the name or the ID of the connection
### <arg>: byte array in hexadecimal format, e.g., "deadbeef" (OPTIONAL)
reactive-tools output --config <config> --connection <connection> --arg <arg>
```

### Request
```bash
# Trigger the request of a _direct_ connection
### <config>: deployment descriptor. MUST be the output of a previous deploy command
### <connection>: either the name or the ID of the connection
### <arg>: byte array in hexadecimal format, e.g., "deadbeef" (OPTIONAL)
reactive-tools request --config <config> --connection <connection> --arg <arg>
```
