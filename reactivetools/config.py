import json
import binascii
import ipaddress
from pathlib import Path
import os
import asyncio
import functools
import types
import logging

from .nodes import SancusNode, SGXNode, NativeNode
from .modules import SancusModule, SGXModule, NativeModule, Module
from .connection import Connection
from .crypto import Encryption
from .periodic_event import PeriodicEvent
from . import tools


class Error(Exception):
    pass


class Config:
    def __init__(self, file_name):
        self.path = Path(file_name).resolve()
        self.nodes = []
        self.modules = []
        self.connections = []

    def get_dir(self):
        return self.path.parent

    def get_node(self, name):
        for n in self.nodes:
            if n.name == name:
                return n

        raise Error('No node with name {}'.format(name))

    def get_module(self, name):
        for m in self.modules:
            if m.name == name:
                return m

        raise Error('No module with name {}'.format(name))


    def get_connection_by_id(self, id):
        for c in self.connections:
            if c.id == id:
                return c

        raise Error('No connection with ID {}'.format(id))


    def get_connection_by_name(self, name):
        for c in self.connections:
            if c.name == name:
                return c

        raise Error('No connection with name {}'.format(name))


    async def install_async(self):
        await self.deploy_priority_modules()

        futures = map(Connection.establish, self.connections)
        await asyncio.gather(*futures)

        # this is needed if we don't have any connections, to ensure that
        # the modules are actually deployed
        await self.deploy_modules_ordered_async()

        futures = map(PeriodicEvent.register, self.periodic_events)
        await asyncio.gather(*futures)

    def install(self):
        asyncio.get_event_loop().run_until_complete(self.install_async())

    async def deploy_modules_ordered_async(self):
        for module in self.modules:
            await module.deploy()
            await module.get_key() # trigger remote attestation for some modules (e.g. SGX)

    def deploy_modules_ordered(self):
        asyncio.get_event_loop().run_until_complete(
                                self.deploy_modules_ordered_async())


    async def build_async(self):
        futures = [module.build() for module in self.modules]
        await asyncio.gather(*futures)


    def build(self):
        asyncio.get_event_loop().run_until_complete(self.build_async())


    async def cleanup_async(self):
        await SGXModule.kill_ra_sp()
         # Add other instructions here if needed


    def cleanup(self):
        asyncio.get_event_loop().run_until_complete(self.cleanup_async())


    async def deploy_priority_modules(self):
        priority_modules = [sm for sm in self.modules if sm.priority is not None]
        priority_modules.sort(key=lambda sm : sm.priority)

        logging.debug("Priority modules: {}".format([sm.name for sm in priority_modules]))
        for module in priority_modules:
            await module.deploy()


def load(file_name, deploy=True):
    with open(file_name, 'r') as f:
        contents = json.load(f)

    config = Config(file_name)

    config.nodes = _load_list(contents['nodes'], _load_node)
    config.modules = _load_list(contents['modules'],
                                lambda m: _load_module(m, config))

    if 'connections' in contents:
        config.connections = _load_list(contents['connections'],
                                        lambda c: _load_connection(c, config, deploy))
    else:
        config.connections = []

    if 'periodic-events' in contents:
        config.periodic_events = _load_list(contents['periodic-events'],
                                        lambda e: _load_periodic_event(e, config))
    else:
        config.periodic_events = []

    return config


def _load_list(l, load_func=lambda e: e):
    if l is None:
        return []
    else:
        return [load_func(e) for e in l]


def _load_node(node_dict):
    return _node_load_funcs[node_dict['type']](node_dict)


def _load_sancus_node(node_dict):
    name = node_dict['name']
    vendor_id = _parse_vendor_id(node_dict['vendor_id'])
    vendor_key = _parse_sancus_key(node_dict['vendor_key'])
    ip_address = ipaddress.ip_address(node_dict['ip_address'])
    reactive_port = node_dict['reactive_port']
    deploy_port = node_dict.get('deploy_port', reactive_port)

    return SancusNode(name, vendor_id, vendor_key,
                      ip_address, reactive_port, deploy_port)


def _load_sgx_node(node_dict):
    name = node_dict['name']
    ip_address = ipaddress.ip_address(node_dict['ip_address'])
    reactive_port = node_dict['reactive_port']
    deploy_port = node_dict.get('deploy_port', reactive_port)

    return SGXNode(name, ip_address, reactive_port, deploy_port)


def _load_native_node(node_dict):
    name = node_dict['name']
    ip_address = ipaddress.ip_address(node_dict['ip_address'])
    reactive_port = node_dict['reactive_port']
    deploy_port = node_dict.get('deploy_port', reactive_port)

    return NativeNode(name, ip_address, reactive_port, deploy_port)


def _load_module(mod_dict, config):
    return _module_load_funcs[mod_dict['type']](mod_dict, config)


def _load_sancus_module(mod_dict, config):
    name = mod_dict['name']
    node = config.get_node(mod_dict['node'])
    priority = mod_dict.get('priority')
    deployed = mod_dict.get('deployed')
    files = _load_list(mod_dict['files'],
                       lambda f: _load_module_file(f, config))
    cflags = _load_list(mod_dict.get('cflags'))
    ldflags = _load_list(mod_dict.get('ldflags'))
    binary = mod_dict.get('binary')
    id = mod_dict.get('id')
    symtab = mod_dict.get('symtab')
    key = _parse_sancus_key(mod_dict.get('key'))
    return SancusModule(name, node, priority, deployed, files, cflags, ldflags,
                        binary, id, symtab, key)


def _load_sgx_module(mod_dict, config):
    name = mod_dict['name']
    node = config.get_node(mod_dict['node'])
    priority = mod_dict.get('priority')
    deployed = mod_dict.get('deployed')
    vendor_key = mod_dict['vendor_key']
    settings = mod_dict['ra_settings']
    features = mod_dict.get('features')
    id = mod_dict.get('id')
    binary = mod_dict.get('binary')
    key = _parse_key(mod_dict.get('key'))
    sgxs = mod_dict.get('sgxs')
    signature = mod_dict.get('signature')
    data = mod_dict.get('data')

    return SGXModule(name, node, priority, deployed, vendor_key, settings,
                    features, id, binary, key, sgxs, signature, data)


def _load_native_module(mod_dict, config):
    name = mod_dict['name']
    node = config.get_node(mod_dict['node'])
    priority = mod_dict.get('priority')
    deployed = mod_dict.get('deployed')
    features = mod_dict.get('features')
    id = mod_dict.get('id')
    binary = mod_dict.get('binary')
    key = _parse_key(mod_dict.get('key'))
    data = mod_dict.get('data')

    return NativeModule(name, node, priority, deployed, features, id, binary, key,
                                data)


def _load_connection(conn_dict, config, deploy):
    evaluate_rules(connection_rules(conn_dict, deploy))

    direct = conn_dict.get('direct')
    from_module = config.get_module(conn_dict['from_module']) if is_present(conn_dict, 'from_module') else None
    from_output = conn_dict.get('from_output')
    from_request = conn_dict.get('from_request')
    to_module = config.get_module(conn_dict['to_module'])
    to_input = conn_dict.get('to_input')
    to_handler = conn_dict.get('to_handler')
    encryption = Encryption.from_str(conn_dict['encryption'])
    key = _parse_key(conn_dict.get('key'))
    nonce = conn_dict.get('nonce')
    id = conn_dict.get('id')
    name = conn_dict.get('name')

    if deploy:
        id = Connection.get_connection_id() # incremental ID
        key = _generate_key(from_module, to_module, encryption) # auto-generated key
        nonce = 0 # only used for direct connections

    if from_module is not None:
        from_module.connections += 1
    to_module.connections += 1

    if name is None:
        name = "conn{}".format(id)

    return Connection(name, from_module, from_output, from_request, to_module,
        to_input, to_handler, encryption, key, id, nonce, direct)


def _load_periodic_event(events_dict, config):
    module = config.get_module(events_dict['module'])
    entry = events_dict['entry']
    frequency = _parse_frequency(events_dict['frequency'])

    return PeriodicEvent(module, entry, frequency)


def _generate_key(module1, module2, encryption):
    if (module1 is not None and encryption not in module1.get_supported_encryption()) \
        or encryption not in module2.get_supported_encryption():
       raise Error('Encryption {} not supported between {} and {}'.format(
            str(encryption), module1.name, module2.name))

    return tools.generate_key(encryption.get_key_size())


def _parse_vendor_id(id):
    if not 1 <= id <= 2**16 - 1:
        raise Error('Vendor ID out of range')

    return id


def _parse_sancus_key(key_str):
    if key_str is None:
        return None

    key = binascii.unhexlify(key_str)

    keysize = tools.get_sancus_key_size()

    if len(key) != keysize:
        raise Error('Keys should be {} bytes'.format(keysize))

    return key


def _parse_key(key_str):
    if key_str is None:
        return None

    return binascii.unhexlify(key_str)


def _parse_frequency(freq):
    if not 1 <= freq <= 2**32 - 1:
        raise Error('Frequency out of range')

    return freq


def _load_module_file(file_name, config):
    path = Path(file_name)
    return path if path.is_absolute() else config.get_dir() / path


_node_load_funcs = {
    'sancus': _load_sancus_node,
    'sgx': _load_sgx_node,
    'native': _load_native_node
}


_module_load_funcs = {
    'sancus': _load_sancus_module,
    'sgx': _load_sgx_module,
    'native': _load_native_module
}


def dump(config, file_name):
    with open(file_name, 'w') as f:
        json.dump(_dump(config), f, indent=4)


@functools.singledispatch
def _dump(obj):
    assert False, 'No dumper for {}'.format(type(obj))


@_dump.register(Config)
def _(config):
    return {
        'nodes': _dump(config.nodes),
        'modules': _dump(config.modules),
        'connections': _dump(config.connections),
        'periodic-events' : _dump(config.periodic_events)
    }


@_dump.register(list)
def _(l):
    return [_dump(e) for e in l]


@_dump.register(SancusNode)
def _(node):
    return {
        "type": "sancus",
        "name": node.name,
        "ip_address": str(node.ip_address),
        "vendor_id": node.vendor_id,
        "vendor_key": _dump(node.vendor_key),
        "reactive_port": node.reactive_port,
        "deploy_port": node.deploy_port
    }


@_dump.register(SancusModule)
def _(module):
    return {
        "type": "sancus",
        "name": module.name,
        "files": _dump(module.files),
        "node": module.node.name,
        "binary": _dump(module.binary),
        "symtab": _dump(module.symtab),
        "id": _dump(module.id),
        "key": _dump(module.key)
    }


@_dump.register(SGXNode)
def _(node):
    return {
        "type": "sgx",
        "name": node.name,
        "ip_address": str(node.ip_address),
        "reactive_port": node.reactive_port,
        "deploy_port": node.deploy_port
    }


@_dump.register(SGXModule)
def _(module):
    return {
        "type": "sgx",
        "name": module.name,
        "node": module.node.name,
        "vendor_key": module.vendor_key,
        "ra_settings": module.ra_settings,
        "features": module.features,
        "id": module.id,
        "binary": _dump(module.binary),
        "sgxs": _dump(module.sgxs),
        "signature": _dump(module.sig),
        "key": _dump(module.key),
        "data": _dump(module.data)
    }


@_dump.register(NativeNode)
def _(node):
    return {
        "type": "native",
        "name": node.name,
        "ip_address": str(node.ip_address),
        "reactive_port": node.reactive_port,
        "deploy_port": node.deploy_port
    }


@_dump.register(NativeModule)
def _(module):
    return {
        "type": "native",
        "name": module.name,
        "node": module.node.name,
        "features": module.features,
        "id": module.id,
        "binary": _dump(module.binary),
        "key": _dump(module.key),
        "data": _dump(module.data)
    }


@_dump.register(Connection)
def _(conn):
    from_module = None if conn.direct else conn.from_module.name

    return {
        "name": conn.name,
        "from_module": from_module,
        "from_output": conn.from_output,
        "from_request": conn.from_request,
        "to_module": conn.to_module.name,
        "to_input": conn.to_input,
        "to_handler": conn.to_handler,
        "encryption": conn.encryption.to_str(),
        "key": _dump(conn.key),
        "id": conn.id,
        "direct": conn.direct,
        "nonce": conn.nonce
    }


@_dump.register(PeriodicEvent)
def _(event):
    return {
        "module": event.module.name,
        "entry": event.entry,
        "frequency": event.frequency
    }


@_dump.register(bytes)
@_dump.register(bytearray)
def _(bs):
    return binascii.hexlify(bs).decode('ascii')


@_dump.register(str)
@_dump.register(int)
def _(x):
    return x


@_dump.register(Path)
def _(path):
    return str(path)


@_dump.register(tuple)
def _(t):
    return { t[1] : t[0] }


@_dump.register(types.CoroutineType)
def _(coro):
    return _dump(asyncio.get_event_loop().run_until_complete(coro))


@_dump.register(dict)
def _(dict):
    return dict


# Rules
def evaluate_rules(rules):
    bad_rules = [r for r in rules if not rules[r]]

    for rule in bad_rules:
        logging.error("Broken rule: {}".format(rule))

    if bad_rules:
        raise Error("Bad JSON configuration")


def is_present(dict, key):
    return key in dict and dict[key] is not None

def has_value(dict, key, value):
    return is_present(dict, key) and dict[key] == value

def authorized_keys(dict, keys):
    for key in dict:
        if key not in keys:
            return False

    return True

def connection_rules(dict, deploy):
    return {
        "to_module not present":
            is_present(dict, "to_module"),
        "encryption not present":
            is_present(dict, "encryption"),

        "either direct=True or from_module + from_{output, request}":
            has_value(dict, "direct", True) != (is_present(dict, "from_module") \
            and (is_present(dict, "from_output") != is_present(dict, "from_request"))),

        "either one between to_input and to_handler":
            is_present(dict, "to_input") != is_present(dict, "to_handler"),

        "direct or from_output->to_input or from_request->to_handler":
            has_value(dict, "direct", True) or (is_present(dict, "from_output") and is_present(dict, "to_input")) \
            or (is_present(dict, "from_request") and is_present(dict, "to_handler")),

        "key present ONLY after deployment":
            (deploy and not is_present(dict, "key")) or (not deploy and is_present(dict, "key")),

        "nonce present ONLY after deployment":
            (deploy and not is_present(dict, "nonce")) or (not deploy and is_present(dict, "nonce")),

        "id present ONLY after deployment":
            (deploy and not is_present(dict, "id")) or (not deploy and is_present(dict, "id")),

        "name mandatory after deployment":
            deploy or (not deploy and is_present(dict, "name")),

        "direct mandatory after deployment":
            deploy or (not deploy and is_present(dict, "direct")),

        "from_module and to_module must be different":
            dict.get("from_module") != dict["to_module"],

        "only authorized keys":
            authorized_keys(dict, ["name", "from_module", "from_output",
                "from_request", "to_module", "to_input", "to_handler",
                "encryption", "key", "id", "direct", "nonce"])
    }
