import binascii
import ipaddress
import os
import asyncio
import logging

from .modules import Module
from .nodes import Node
from .connection import Connection
from .crypto import Encryption
from .periodic_event import PeriodicEvent
from . import tools
from .dumpers import *
from .loaders import *
from .rules.evaluators import *
from .descriptor import DescriptorType

from .nodes import node_rules, node_funcs, node_cleanup_coros
from .modules import module_rules, module_funcs, module_cleanup_coros


class Error(Exception):
    pass


class Config:
    def __init__(self):
        self.nodes = []
        self.modules = []
        self.connections = []
        self.connections_id = 0
        self.output_type = None

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
        # TODO: check if you want to only deploy or also do remote attestation
        futures = map(lambda x : x.get_key(), self.modules)
        await asyncio.gather(*futures)

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
        coros = list(map(lambda c: c(), node_cleanup_coros + module_cleanup_coros))
        await asyncio.gather(*coros)


    def cleanup(self):
        asyncio.get_event_loop().run_until_complete(self.cleanup_async())


    async def deploy_priority_modules(self):
        priority_modules = [sm for sm in self.modules if sm.priority is not None]
        priority_modules.sort(key=lambda sm : sm.priority)

        logging.debug("Priority modules: {}".format([sm.name for sm in priority_modules]))
        for module in priority_modules:
            await module.deploy()


def load(file_name, output_type=None):
    config = Config()
    desc_type = DescriptorType.from_str(output_type)

    contents, input_type = DescriptorType.load_any(file_name)

    # Output file format is:
    #   - desc_type if has been provided as input, or
    #   - the same type of the input file otherwise
    config.output_type = desc_type or input_type

    config.nodes = load_list(contents['nodes'],
                                lambda n: _load_node(n, config))
    config.modules = load_list(contents['modules'],
                                lambda m: _load_module(m, config))

    config.connections_current_id = contents.get('connections_current_id') or 0

    if 'connections' in contents:
        config.connections = load_list(contents['connections'],
                                        lambda c: _load_connection(c, config))
    else:
        config.connections = []

    if 'periodic-events' in contents:
        config.periodic_events = load_list(contents['periodic-events'],
                                        lambda e: _load_periodic_event(e, config))
    else:
        config.periodic_events = []

    return config


def _load_node(node_dict, config):
    # Basic rules common to all nodes
    evaluate_rules(os.path.join("default", "node.yaml"), node_dict)
    # Specific rules for a specific node type
    evaluate_rules(os.path.join("nodes", node_rules[node_dict['type']]), node_dict)

    return node_funcs[node_dict['type']](node_dict)


def _load_module(mod_dict, config):
    # Basic rules common to all nodes
    evaluate_rules(os.path.join("default", "module.yaml"), mod_dict)
    # Specific rules for a specific node type
    evaluate_rules(os.path.join("modules", module_rules[mod_dict['type']]), mod_dict)

    node = config.get_node(mod_dict['node'])
    module = module_funcs[mod_dict['type']](mod_dict, node)

    if node.__class__ not in module.get_supported_nodes():
        raise Error("Node {} ({}) does not support module {} ({})".format(
            node.name, node.__class__.__name__,
            module.name, module.__class__.__name__))

    return module


def _load_connection(conn_dict, config):
    evaluate_rules(os.path.join("default", "connection.yaml"), conn_dict)
    return Connection.load(conn_dict, config)


def _load_periodic_event(events_dict, config):
    evaluate_rules(os.path.join("default", "periodic_event.yaml"), events_dict)
    return PeriodicEvent.load(events_dict, config)


def evaluate_rules(rules_file, dict):
    rules = load_rules(rules_file)

    ok = True

    for r in rules:
        try:
            result = eval(rules[r])
        except:
            result = False

        if not result:
            logging.error("{} - Broken rule: {}".format(rules_file, r))
            ok = False

    if not ok:
        raise Error("Bad deployment descriptor")


def dump_config(config, file_name):
    config.output_type.dump(file_name, dump(config))


@dump.register(Config)
def _(config):
    dump(config.nodes)
    return {
            'nodes': dump(config.nodes),
            'modules': dump(config.modules),
            'connections_current_id': config.connections_current_id,
            'connections': dump(config.connections),
            'periodic-events' : dump(config.periodic_events)
        }


@dump.register(Node)
def _(node):
    return node.dump()


@dump.register(Module)
def _(module):
    return module.dump()


@dump.register(Connection)
def _(conn):
    return conn.dump()


@dump.register(PeriodicEvent)
def _(event):
    return event.dump()
