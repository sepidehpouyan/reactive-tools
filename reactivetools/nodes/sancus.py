import asyncio
import logging
import binascii
import aiofile
from enum import IntEnum

from reactivenet import *

from .base import Node
from .. import tools


class Error(Exception):
    pass


class SetKeyResultCode(IntEnum):
    Ok                = 0x0
    IllegalConnection = 0x1
    MalformedPayload  = 0x2
    InternalError     = 0x3


class SancusNode(Node):
    def __init__(self, name, vendor_id, vendor_key,
                 ip_address, reactive_port, deploy_port):
        super().__init__(name, ip_address, reactive_port, deploy_port, need_lock=True)

        self.vendor_id = vendor_id
        self.vendor_key = vendor_key


    async def deploy(self, module):
        assert module.node is self

        if module.deployed is not None:
            return

        async with aiofile.AIOFile(await module.binary, "rb") as f:
            file_data = await f.read()

        # The packet format is [NAME \0 VID ELF_FILE]
        payload =   module.name.encode('ascii') + b'\0'   + \
                    tools.pack_int16(self.vendor_id)      + \
                    file_data

        command = CommandMessage(ReactiveCommand.Load,
                                Message(payload),
                                self.ip_address,
                                self.deploy_port)

        res = await self._send_reactive_command(
                command,
                log='Deploying {} on {}'.format(module.name, self.name)
                )


        sm_id = tools.unpack_int16(res.message.payload[:2])
        if sm_id == 0:
            raise Error('Deploying {} on {} failed'
                            .format(module.name, self.name))

        symtab = res.message.payload[2:]
        symtab_file = tools.create_tmp(suffix='.ld')

        # aiofile for write operations is bugged (version 3.3.3)
        # I get a "bad file descriptor" error after writes.
        with open(symtab_file, "wb") as f:
            f.write(symtab[:-1]) # Drop last 0 byte

        return sm_id, symtab_file


    async def set_key(self, module, conn_id, conn_io, encryption, key):
        assert module.node is self
        assert encryption in module.get_supported_encryption()

        module_id, module_key, io_id = await asyncio.gather(
                               module.id, module.key, conn_io.get_index(module))

        nonce = tools.pack_int16(self._get_nonce(module))
        io_id = tools.pack_int16(io_id)
        conn_id_packed = tools.pack_int16(conn_id)
        ad = conn_id_packed + io_id + nonce

        cipher = await encryption.SPONGENT.encrypt(module_key, ad, key)

        # The payload format is [sm_id, entry_id, 16 bit nonce, index, wrapped(key), tag]
        # where the tag includes the nonce and the index.
        payload =       tools.pack_int16(module_id)                     + \
                        tools.pack_int16(ReactiveEntrypoint.SetKey)     + \
                        ad                                              + \
                        cipher

        command = CommandMessage(ReactiveCommand.Call,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        res = await self._send_reactive_command(
                command,
                log='Setting key of {}:{} on {} to {}'.format(
                     module.name, conn_io.name, self.name,
                     binascii.hexlify(key).decode('ascii'))
                )

        # The result format is [tag] where the tag includes the nonce and result code
        res_code = res.message.payload[:2]
        res_code_enum = SetKeyResultCode(tools.unpack_int16(res_code))
        if res_code_enum != SetKeyResultCode.Ok:
            raise Error("Received result code {}".format(str(res_code_enum)))

        set_key_tag = res.message.payload[2:]
        expected_tag = await encryption.SPONGENT.mac(module_key, nonce + res_code)

        if set_key_tag != expected_tag:
            raise Error('Module response has wrong tag')


    async def connect(self, to_module, conn_id):
        module_id = await to_module.get_id()

        # HACK for sancus event manager:
        # if ip address is 0.0.0.0 it handles the connection as local
        ip_address = b'\x00' * 4 if \
                to_module.node is self else \
                to_module.node.ip_address.packed

        payload = tools.pack_int16(conn_id)                           + \
                  tools.pack_int16(module_id)                         + \
                  tools.pack_int16(to_module.node.reactive_port)      + \
                  ip_address

        command = CommandMessage(ReactiveCommand.Connect,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Connecting id {} to {}'.format(conn_id, to_module.name))
