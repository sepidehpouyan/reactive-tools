import json
import binascii
import ipaddress
from pathlib import Path
import os
import asyncio

import sancus.config

from .nodes import SancusNode
from .modules import SancusModule
from .connection import Connection


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

    async def install_async(self):
        futures = map(Connection.establish, self.connections)
        await asyncio.gather(*futures)

    def install(self):
        asyncio.get_event_loop().run_until_complete(self.install_async())


def load(file_name):
    with open(file_name, 'r') as f:
        contents = json.load(f)

    config = Config(file_name)
    config.nodes = _load_list(contents['nodes'], _load_node)
    config.modules = _load_list(contents['modules'],
                                lambda m: _load_module(m, config))
    config.connections = _load_list(contents['connections'],
                                    lambda c: _load_connection(c, config))
    return config


def _load_list(l, load_func):
    return [load_func(e) for e in l]


def _load_node(node_dict):
    return _node_load_funcs[node_dict['type']](node_dict)


def _load_sancus_node(node_dict):
    name = node_dict['name']
    vendor_id = _parse_vendor_id(node_dict['vendor_id'])
    vendor_key = _parse_vendor_key(node_dict['vendor_key'])
    ip_address = ipaddress.ip_address(node_dict['ip_address'])
    deploy_port = node_dict.get('deploy_port', 2000)
    reactive_port = node_dict.get('reactive_port', 2001)
    return SancusNode(name, vendor_id, vendor_key,
                      ip_address, deploy_port, reactive_port)


def _load_module(mod_dict, config):
    return _module_load_funcs[mod_dict['type']](mod_dict, config)


def _load_sancus_module(mod_dict, config):
    name = mod_dict['name']
    files = _load_list(mod_dict['files'],
                       lambda f: _load_module_file(f, config))
    node = config.get_node(mod_dict['node'])
    return SancusModule(name, files, node)


def _load_connection(conn_dict, config):
    from_module = config.get_module(conn_dict['from_module'])
    from_output = conn_dict['from_output']
    to_module = config.get_module(conn_dict['to_module'])
    to_input = conn_dict['to_input']

    # Don't use dict.get() here because we don't want to call os.urandom() when
    # not strictly necessary.
    if 'key' in conn_dict:
        key = conn_dict['key']
    else:
        key = os.urandom(sancus.config.SECURITY // 8)

    return Connection(from_module, from_output, to_module, to_input, key)


def _parse_vendor_id(id_str):
    assert 1 <= len(id_str) <= 4
    return int(id_str, base=16)


def _parse_vendor_key(key_str):
    key = binascii.unhexlify(key_str)

    if len(key) != sancus.config.SECURITY // 8:
        raise Error('Keys should be {} bit'.format(sancus.config.SECURITY))

    return key


def _load_module_file(file_name, config):
    path = Path(file_name)
    return path if path.is_absolute() else config.get_dir() / path


_node_load_funcs = {
    'sancus': _load_sancus_node
}


_module_load_funcs = {
    'sancus': _load_sancus_module
}

