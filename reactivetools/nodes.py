import asyncio
import struct
import contextlib
import collections
import logging
import binascii
from enum import IntEnum

import sancus.crypto

from . import tools


class Error(Exception):
    pass


class Node:
    def __init__(self, name, ip_address, deploy_port=2000, reactive_port=2001):
        self.name = name
        self.ip_address = ip_address
        self.deploy_port = deploy_port
        self.reactive_port = reactive_port
        self.__nonces = collections.Counter()

        # Our Contiki implementation does not support *any* concurrent
        # connections. Not on the same port, not on different ports. Therefore,
        # we use a single lock to make sure all connections made to the node are
        # serialized.
        self.__lock = asyncio.Lock()

    async def deploy(self, module):
        packet = await self.__create_install_packet(module)

        async with self.__lock:
            logging.info('Deploying %s on %s', module.name, self.name)

            reader, writer = await asyncio.open_connection(str(self.ip_address),
                                                           self.deploy_port)

            # TODO is the connection properly closed by closing the writer?
            with contextlib.closing(writer):
                writer.write(packet)
                sm_id = self.__unpack_int(await reader.read(2))

                if sm_id == 0:
                    raise Error('Deploying {} on {} failed'
                                    .format(module.name, self.name))

                symtab = await reader.read()

        symtab_file = tools.create_tmp(suffix='.ld')

        with open(symtab_file, 'wb') as f:
            f.write(symtab[:-1]) # Drop last 0 byte

        return sm_id, symtab_file

    async def connect(self, from_module, from_output, to_module, to_input):
        assert from_module.node is self

        results = await asyncio.gather(from_module.id,
                                       from_module.get_io_id(from_output),
                                       to_module.id,
                                       to_module.get_io_id(to_input))
        from_module_id, from_output_id, to_module_id, to_input_id = results

        payload = self.__pack_int(from_module_id)   + \
                  self.__pack_int(from_output_id)   + \
                  self.__pack_int(to_module_id)     + \
                  to_module.node.ip_address.packed  + \
                  self.__pack_int(to_input_id)

        await self.__send_reactive_command(
                _ReactiveCommand.Connect, payload,
                log=('Connecting %s:%s to %s:%s on %s',
                     from_module.name, from_output,
                     to_module.name, to_input,
                     self.name))

    async def set_key(self, module, io_name, key):
        module_id, module_key, io_id = await asyncio.gather(
                               module.id, module.key, module.get_io_id(io_name))

        nonce = self.__pack_int(self.__get_nonce(module))
        io_id = self.__pack_int(io_id)
        ad = nonce + io_id
        cipher, tag = sancus.crypto.wrap(module_key, ad, key)

        # The payload format is [sm_id, 16 bit nonce, index, wrapped(key), tag]
        # where the tag includes the nonce and the index.
        payload = self.__pack_int(module_id) + ad + cipher + tag

        # The result format is [16 bit result code, tag] where the tag includes
        # the nonce and the result code.
        result_len = 2 + sancus.config.SECURITY // 8

        result = await self.__send_reactive_command(
                    _ReactiveCommand.SetKey, payload, result_len,
                    log=('Setting key of %s:%s on %s to %s',
                         module.name, io_name, self.name,
                         binascii.hexlify(key).decode('ascii')))

        set_key_code_packed = result.payload[0:2]
        set_key_code = self.__unpack_int(set_key_code_packed)
        set_key_tag = result.payload[2:]
        set_key_ad = nonce + set_key_code_packed
        expected_tag = sancus.crypto.mac(module_key, set_key_ad)

        if set_key_tag != expected_tag:
            raise Error('Module response has wrong tag')

        if set_key_code != _ReactiveSetKeyResultCode.Ok:
            raise Error('Got error code from module: {}'.format(set_key_code))

    def __get_nonce(self, module):
        nonce = self.__nonces[module]
        self.__nonces[module] += 1
        return nonce

    async def __send_reactive_command(self, command, payload, result_len=0,
                                      *, log=None):
        packet = self.__create_reactive_packet(command, payload)

        # The Contiki implementation only supports 1 concurrent connection to
        # the reactive server
        async with self.__lock:
            if log is not None:
                logging.info(*log)

            reader, writer = await asyncio.open_connection(str(self.ip_address),
                                                           self.reactive_port)

            with contextlib.closing(writer):
                writer.write(packet)
                raw_result = await reader.readexactly(result_len + 1)
                code = _ReactiveResultCode(raw_result[0])

                if code != _ReactiveResultCode.Ok:
                    raise Error('Reactive command {} failed with code {}'
                                    .format(command, code))

                return _ReactiveResult(code, raw_result[1:])


    def __create_reactive_packet(self, command, payload):
        return self.__pack_int(command)      + \
               self.__pack_int(len(payload)) + \
               payload;

    async def __create_install_packet(self, module):
        # The packet format is [LEN NAME \0 VID ELF_FILE]
        # LEN is the length of the packet without LEN itself

        # Unfortunately, there is no asyncio support for file operations
        with open(await module.binary, 'rb') as f:
            file_data = f.read()

        # +3 is the NULL terminator of the name + 2 bytes of the VID
        length = len(file_data) + len(module.name) + 3

        return self.__pack_int(length)              + \
               module.name.encode('ascii') + b'\0'  + \
               self.__pack_int(self.vendor_id)      + \
               file_data

    @staticmethod
    def __pack_int(i):
        return struct.pack('!H', i)

    @staticmethod
    def __unpack_int(i):
        return struct.unpack('!H', i)[0]



class SancusNode(Node):
    def __init__(self, name, vendor_id, vendor_key,
                 ip_address, deploy_port=2000, reactive_port=2001):
        super().__init__(name, ip_address, deploy_port, reactive_port)
        self.vendor_id = vendor_id
        self.vendor_key = vendor_key


class _ReactiveCommand(IntEnum):
    Connect   = 0x0
    SetKey    = 0x1
    PostEvent = 0x2
    Call      = 0x3


class _ReactiveResultCode(IntEnum):
    Ok                = 0x0
    ErrIllegalCommand = 0x1
    ErrPayloadFormat  = 0x2
    ErrInternal       = 0x3


class _ReactiveResult:
    def __init__(self, code, payload=bytearray()):
        self.code = code
        self.payload = payload


class _ReactiveSetKeyResultCode(IntEnum):
    Ok                   = 0x0,
    ErrIllegalConnection = 0x1,
    ErrWrongTag          = 0x2
