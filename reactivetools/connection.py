import asyncio
import logging
from enum import IntEnum

from .crypto import Encryption

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
    cnt = 0

    def __init__(self, name, from_module, from_output, from_request, to_module,
        to_input, to_handler, encryption, key, id, nonce, direct):
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

        if direct:
            self.direct = True
            self.from_index = None
        else:
            self.direct = False # to avoid assigning None
            self.from_index = ConnectionIndex(ConnectionIO.OUTPUT, from_output) if from_output is not None \
                else ConnectionIndex(ConnectionIO.REQUEST, from_request)

        self.to_index = ConnectionIndex(ConnectionIO.INPUT, to_input) if to_input is not None \
            else ConnectionIndex(ConnectionIO.HANDLER, to_handler)

    async def establish(self):
        if self.direct:
            await self.__establish_direct()
        else:
            await self.__establish_normal()


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
    def get_connection_id():
        id = Connection.cnt
        Connection.cnt += 1
        return id
