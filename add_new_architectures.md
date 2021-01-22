# Add support for a new architecture

It is quite easy to extend the scripts to support new architectures.

This file provides an example of what it is necessary to do in this case. We'll suppose to add support for ARM TrustZone.

## Note before starting

The scripts use massively `asyncio` framework, which is a powerful tool to perform asynchronous operations (like opening a file, connecting to a remote host, executing a subprocess..).

All the common methods that you need to implement are asynchronous (defined with the `async` keyword), but it is not mandatory to actually use asynchronous operations (so, you can implement those methods as normal ones).

However, it is _highly recommended_ to use as much concurrency as possible, to speed up significantly the deployment process.

## Implement Module class

Add a python file called `trustzone.py` in `modules` folder, defining a new class called `TrustZoneModule`, which extends the base class `Module` (defined in `base.py`). Also, import the module in the `__init__.py`, so that the Module will be in the scope of `modules` .



The following abstract methods need to be implemented:

- `deploy(self)`

  - This method should eventually call the `deploy` method of its node

- `call(self, entry, arg=None)`

  - This method should eventually call the `call` method of its node
  - `entry`: entrypoint name
  - `arg`: optional argument, which must be a byte array

- `get_id(self)`

  - returns the ID of the module

- `get_input_id(self, input)`

  - returns the input ID

- `get_output_id(self, output)`

  - returns the output ID

- `get_entry_id(self, entry)`

  - returns the entrypoint ID

- `get_key(self)`

  - returns the module's Master Key

- `get_supported_encryption()` - _static method_

  - should return a list of `connection.Encryption` elements, describing which encryption algorithms are supported by the module

- `get_supported_node_type()` - _static method_

  - should return the node class supported by the module



All modules have also some common attributes, which are:

- `name`: module name. Specified in the input JSON file
- `node`: node the module belongs to. It is a `Node` object. Node's name is specified in the input JSON file.



For all the other methods/attributes, the developer can choose his own implementation.

## Implement Node class

Add a python file called `trustzone.py` in `nodes` folder, defining a new class called `TrustZoneNode`, which extends the base class `Node` (defined in `base.py`).  Also, import the module in the `__init__.py`, so that the Module will be in the scope of `node` .



The following abstract methods need to be implemented:

- `deploy(self, module)`
  - Ideally, in this method we send the binary of `module` to the node
- `connect(self, from_module, from_output, to_module, to_input)`
  - Send to the Event Manager of the node a new connection between modules
  - `from_module` and `to_module` are objects of the `Module` class
  - `from_output` and `to_input` are strings (not ids)
- `set_key(self, module, io_name, encryption, key, conn_io)`
  - Set the key for a connection. A message to `module` has to be sent through the Event Manager
  - `io_name`: name of the input/output
  - `encryption`: encryption algorithm ID (see below)
  - `key`: connection key
  - `conn_io`: specifies if `io_name` is an output or an input. See `connection.ConnectionIO`

- `call(self, module, entry, arg=None)`
  - `module`: `Module` object
  - `entry`: entrypoint name
  - `arg`: optional argument, which is a byte array



All nodes have also some common attributes, which are:

- `name`: node name. Specified in the input JSON file
- `ip_address`: address of the node, which is either a `IPv4Address` or a `IPv6Address` (see [ipaddress](https://docs.python.org/3/library/ipaddress.html) library). Specified in the input JSON file
- `reactive_port`: port the Event Manager listens to events from. Specified in the input JSON file
- `deploy_port`: port the Module Loader listens from. Specified in the input JSON file



For all the other methods/attributes, the developer can choose his own implementation.

## Add new encryption types

In `connection.py` we can add new encryption algorithms in the `Encryption` enum class. If you need to add a new algorithm, modify this class accordingly.

Note that two modules can be connected using a specific encryption **only** if both of them support it. If, for example, you want to connect a SGX module with a TrustZone module using an encryption algorithm X, you have to:

- Implement that encryption algorithm in the modules code
  - For SGX/Native modules, just update the [`reactive_crypto`](https://github.com/gianlu33/rust-sgx-libs/tree/master/reactive_crypto) library
- Update the method `get_supported_encryption` of `SGXModule` and `TrustZoneModule`.

## Update config.py

Last thing we have to do is update `config.py` to correctly read/write a module or node from/to a JSON file.

### Import Node and Module classes

Simple as that.

### Load node and module from the input JSON file

You have to update `_node_load_funcs` and `_module_load_funcs` dicts

- The key is the name of the architecture (as it appears on the input JSON)
- The value is an handler, which will be called to load a Node / Module

Example:

```python
_module_load_funcs = {
    # other architectures..
    'trustzone': _load_trustzone_module
}

def _load_trustzone_module(mod_dict, config):
    name = mod_dict['name']
    node = config.get_node(mod_dict['node'])
    # other attributes..

    return TrustZoneModule(name, node, ...)
```

### Dump to output JSON file

You need a dumper for your Node and Module classes. Example:

```python
@_dump.register(TrustZoneModule)
def _(module):
	return {
        "type": "trustzone",
        "name": module.name,
        # other attributes..
    }

@_dump.register(TrustZoneNode)
def _(node):
	return {
        "type": "trustzone",
        "name": node.name,
        # other attributes..
    }
```

## Import external Python modules

If you need to import an external python module you are completely allowed to do it, but for specific modules (e.g. a TrustZone code generator) it is recommended to import the module **only** _inside_ the functions that use it.

In this way, if we don't use a specific architecture we are not forced to install its modules, and the scripts will work without it as well.

E.g. If i don't use Sancus modules in my system, i don't need to install Sancus compiler and its python library to run the scripts.
