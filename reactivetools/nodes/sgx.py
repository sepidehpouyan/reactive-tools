import asyncio
import aiofile
import logging
from abc import ABC, abstractmethod
import binascii
import ipaddress

from reactivenet import *

from .base import Node
from ..connection import ConnectionIO
from .. import glob
from .. import tools
from ..crypto import Encryption
from ..dumpers import *
from ..loaders import *

class Error(Exception):
    pass

class SGXBase(Node):
    def __init__(self, name, ip_address, reactive_port, deploy_port, module_id):
        super().__init__(name, ip_address, reactive_port, deploy_port)

        self._moduleid = module_id if module_id else 1


    @abstractmethod
    async def deploy(self, module):
        pass


    async def set_key(self, module, conn_id, conn_io, encryption, key):
        assert module.node is self
        assert encryption in module.get_supported_encryption()

        io_id = await conn_io.get_index(module)
        nonce = module.nonce
        module.nonce += 1

        ad =    tools.pack_int8(encryption)                     + \
                tools.pack_int16(conn_id)                       + \
                tools.pack_int16(io_id)                         + \
                tools.pack_int16(nonce)

        cipher = await Encryption.AES.encrypt(await module.get_key(), ad, key)

        payload =   tools.pack_int16(module.id)                     + \
                    tools.pack_int16(ReactiveEntrypoint.SetKey)     + \
                    ad                                              + \
                    cipher

        command = CommandMessage(ReactiveCommand.Call,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Setting key of connection {} ({}:{}) on {} to {}'.format(
                     conn_id, module.name, conn_io.name, self.name,
                     binascii.hexlify(key).decode('ascii'))
                )


    def get_module_id(self):
        id = self._moduleid
        self._moduleid += 1

        return id


class SGXNode(SGXBase):
    type = "sgx"

    def __init__(self, name, ip_address, reactive_port, deploy_port, module_id, aesm_port):
        super().__init__(name, ip_address, reactive_port, deploy_port, module_id)

        self.aesm_port = aesm_port or 13741

    @staticmethod
    def load(node_dict):
        name = node_dict['name']
        ip_address = ipaddress.ip_address(node_dict['ip_address'])
        reactive_port = node_dict['reactive_port']
        deploy_port = node_dict.get('deploy_port') or reactive_port
        module_id = node_dict.get('module_id')
        aesm_port = node_dict.get('aesm_port')

        return SGXNode(name, ip_address, reactive_port, deploy_port,
                    module_id, aesm_port)


    def dump(self):
        return {
            "type": self.type,
            "name": self.name,
            "ip_address": str(self.ip_address),
            "reactive_port": self.reactive_port,
            "deploy_port": self.deploy_port,
            "module_id": self._moduleid,
            "aesm_port": self.aesm_port
        }


    async def deploy(self, module):
        if module.deployed:
            return

        async with aiofile.AIOFile(await module.sgxs, "rb") as f:
            sgxs = await f.read()

        async with aiofile.AIOFile(await module.sig, "rb") as f:
            sig = await f.read()


        payload =   tools.pack_int32(len(sgxs))                     + \
                    sgxs                                            + \
                    tools.pack_int32(len(sig))                      + \
                    sig

        command = CommandMessageLoad(payload,
                                self.ip_address,
                                self.deploy_port)

        await self._send_reactive_command(
            command,
            log='Deploying {} on {}'.format(module.name, self.name)
            )

        module.deployed = True
