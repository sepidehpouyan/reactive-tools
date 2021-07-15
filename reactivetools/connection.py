import asyncio
import logging
from enum import IntEnum

from .dumpers import *
from .loaders import *
from .rules.evaluators import *

from .crypto import Encryption
from . import tools

class Error(Exception):
    pass

class ConnectionIO(IntEnum):
    OUTPUT      = 0x0
    INPUT       = 0x1
    REQUEST     = 0x2
    HANDLER     = 0x3

class ConnectionIndex():
    def __init__(self, type, name):
        self.type = type
        self.name = name
        self.index = None


    async def set_index(self, module):
        if self.type == ConnectionIO.OUTPUT:
            self.index = await module.get_output_id(self.name)
        elif self.type == ConnectionIO.INPUT:
            self.index = await module.get_input_id(self.name)
        elif self.type == ConnectionIO.REQUEST:
            self.index = await module.get_request_id(self.name)
        elif self.type == ConnectionIO.HANDLER:
            self.index = await module.get_handler_id(self.name)


    async def get_index(self, module):
        if self.index:
            return self.index

        await self.set_index(module)
        return self.index

class Connection:
    def __init__(self, name, from_module, from_output, from_request, to_module,
        to_input, to_handler, encryption, key, id, nonce, direct, established):
        self.name = name
        self.from_module = from_module
        self.from_output = from_output
        self.from_request = from_request
        self.to_module = to_module
        self.to_input = to_input
        self.to_handler = to_handler
        self.encryption = encryption
        self.key = key
        self.id = id
        self.nonce = nonce
        self.established = established

        if direct:
            self.direct = True
            self.from_index = None
        else:
            self.direct = False # to avoid assigning None
            self.from_index = ConnectionIndex(ConnectionIO.OUTPUT, from_output) if from_output is not None \
                else ConnectionIndex(ConnectionIO.REQUEST, from_request)

        self.to_index = ConnectionIndex(ConnectionIO.INPUT, to_input) if to_input is not None \
            else ConnectionIndex(ConnectionIO.HANDLER, to_handler)


    @staticmethod
    def load(conn_dict, config):
        direct = conn_dict.get('direct')
        from_module = config.get_module(conn_dict['from_module']) if is_present(conn_dict, 'from_module') else None
        from_output = conn_dict.get('from_output')
        from_request = conn_dict.get('from_request')
        to_module = config.get_module(conn_dict['to_module'])
        to_input = conn_dict.get('to_input')
        to_handler = conn_dict.get('to_handler')
        encryption = Encryption.from_str(conn_dict['encryption'])
        key = parse_key(conn_dict.get('key')) or Connection.generate_key(from_module, to_module, encryption) # auto-generated key
        nonce = conn_dict.get('nonce') or 0
        id = conn_dict.get('id')
        established = conn_dict.get('established')

        if id is None:
            id = config.connections_current_id # incremental ID
            config.connections_current_id += 1

        name = conn_dict.get('name') or "conn{}".format(id)

        if from_module is not None:
            from_module.connections += 1
        to_module.connections += 1

        return Connection(name, from_module, from_output, from_request, to_module,
            to_input, to_handler, encryption, key, id, nonce, direct, established)


    def dump(self):
        from_module = None if self.direct else self.from_module.name

        return {
            "name": self.name,
            "from_module": from_module,
            "from_output": self.from_output,
            "from_request": self.from_request,
            "to_module": self.to_module.name,
            "to_input": self.to_input,
            "to_handler": self.to_handler,
            "encryption": self.encryption.to_str(),
            "key": dump(self.key),
            "id": self.id,
            "direct": self.direct,
            "nonce": self.nonce,
            "established": self.established
        }


    async def establish(self):
        if self.established:
            return

        if self.direct:
            await self.__establish_direct()
        else:
            await self.__establish_normal()

        self.established = True


    async def __establish_normal(self):
        from_node, to_node = self.from_module.node, self.to_module.node

        # TODO check if the module is the same: if so, abort!

        connect = from_node.connect(self.to_module, self.id)
        set_key_from = from_node.set_key(self.from_module, self.id, self.from_index,
                                     self.encryption, self.key)
        set_key_to = to_node.set_key(self.to_module, self.id, self.to_index,
                                     self.encryption, self.key)

        await asyncio.gather(connect, set_key_from, set_key_to)

        logging.info('Connection %d:%s from %s:%s on %s to %s:%s on %s established',
                     self.id, self.name, self.from_module.name, self.from_index.name, from_node.name,
                     self.to_module.name, self.to_index.name, to_node.name)


    async def __establish_direct(self):
        to_node = self.to_module.node

        await to_node.set_key(self.to_module, self.id, self.to_index,
                                     self.encryption, self.key)

        logging.info('Direct connection %d:%s to %s:%s on %s established',
                     self.id, self.name, self.to_module.name, self.to_index.name, to_node.name)


    @staticmethod
    def generate_key(module1, module2, encryption):
        if (module1 is not None and encryption not in module1.get_supported_encryption()) \
            or encryption not in module2.get_supported_encryption():
           raise Error('Encryption {} not supported between {} and {}'.format(
                str(encryption), module1.name, module2.name))

        return tools.generate_key(encryption.get_key_size())
