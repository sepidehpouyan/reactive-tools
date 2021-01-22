import asyncio
import collections
import logging
import binascii

from abc import ABC, abstractmethod
from enum import IntEnum

from reactivenet import *

from .. import tools

class Error(Exception):
    pass

class Node(ABC):
    def __init__(self, name, ip_address, reactive_port, deploy_port, need_lock=False):
        self.name = name
        self.ip_address = ip_address
        self.reactive_port = reactive_port
        self.deploy_port = deploy_port

        self.__nonces = collections.Counter()

        if need_lock:
            self.__lock = asyncio.Lock()
        else:
            self.__lock = None

    @abstractmethod
    async def deploy(self, module):
        pass

    @abstractmethod
    async def set_key(self, module, conn_id, io_name, encryption, key, conn_io):
        pass


    # Default implementation of the following functions. If a specific architecture
    # needs a different implementation, do it in the subclass (e.g., SancusNode)

    async def connect(self, to_module, conn_id):
        module_id = await to_module.get_id()

        payload = tools.pack_int16(conn_id)                           + \
                  tools.pack_int16(module_id)                         + \
                  tools.pack_int16(to_module.node.reactive_port)      + \
                  to_module.node.ip_address.packed

        command = CommandMessage(ReactiveCommand.Connect,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Connecting id {} to {}'.format(conn_id, to_module.name))


    async def call(self, module, entry, arg=None):
        assert module.node is self
        module_id, entry_id = \
            await asyncio.gather(module.get_id(), module.get_entry_id(entry))

        payload = tools.pack_int16(module_id)       + \
                  tools.pack_int16(entry_id)        + \
                  (b'' if arg is None else arg)

        command = CommandMessage(ReactiveCommand.Call,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        response = await self._send_reactive_command(
                command,
                log='Sending call command to {}:{} ({}:{}) on {}'.format(
                     module.name, entry, module_id, entry_id, self.name)
                )

        if not response.ok():
            logging.error("Received error code {}".format(str(response.code)))
        else:
            logging.info("Response: \"{}\"".format(
                binascii.hexlify(response.message.payload).decode('ascii')))


    async def output(self, connection, arg=None):
        assert connection.to_module.node is self

        module_id = await connection.to_module.get_id()

        if arg is None:
            data = b''
        else:
            data = arg

        cipher = await connection.encryption.encrypt(connection.key,
                    tools.pack_int16(connection.nonce), data)

        payload = tools.pack_int16(module_id)               + \
                  tools.pack_int16(connection.id)           + \
                  cipher

        command = CommandMessage(ReactiveCommand.RemoteOutput,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Sending handle_output command of connection {}:{} to {} on {}'.format(
                     connection.id, connection.name, connection.to_module.name, self.name)
                )


    async def request(self, connection, arg=None):
        assert connection.to_module.node is self

        module_id = await connection.to_module.get_id()

        if arg is None:
            data = b''
        else:
            data = arg

        cipher = await connection.encryption.encrypt(connection.key,
                    tools.pack_int16(connection.nonce), data)

        payload = tools.pack_int16(module_id)               + \
                  tools.pack_int16(connection.id)           + \
                  cipher

        command = CommandMessage(ReactiveCommand.RemoteRequest,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        response = await self._send_reactive_command(
                command,
                log='Sending handle_request command of connection {}:{} to {} on {}'.format(
                     connection.id, connection.name, connection.to_module.name, self.name)
                )

        if not response.ok():
            logging.error("Received error code {}".format(str(response.code)))
            return

        resp_encrypted = response.message.payload
        plaintext = await connection.encryption.decrypt(connection.key,
                    tools.pack_int16(connection.nonce + 1), resp_encrypted)

        logging.info("Response: \"{}\"".format(
            binascii.hexlify(plaintext).decode('ascii')))


    async def register_entrypoint(self, module, entry, frequency):
        assert module.node is self
        module_id, entry_id = \
            await asyncio.gather(module.get_id(), module.get_entry_id(entry))

        payload = tools.pack_int16(module_id)       + \
                  tools.pack_int16(entry_id)        + \
                  tools.pack_int32(frequency)

        command = CommandMessage(ReactiveCommand.RegisterEntrypoint,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Sending RegisterEntrypoint command of {}:{} ({}:{}) on {}'.format(
                     module.name, entry, module_id, entry_id, self.name)
                )


    async def _send_reactive_command(self, command, log=None):
        if self.__lock is not None:
            async with self.__lock:
                return await self.__send_reactive_command(command, log)
        else:
            return await self.__send_reactive_command(command, log)


    @staticmethod
    async def __send_reactive_command(command, log):
        if log is not None:
            logging.info(log)

        if command.has_response():
            response =  await command.send_wait()
            if not response.ok():
                raise Error('Reactive command {} failed with code {}'
                                .format(str(command.code), str(response.code)))
            return response

        else:
            await command.send()
            return None


    def _get_nonce(self, module):
        nonce = self.__nonces[module]
        self.__nonces[module] += 1
        return nonce
