import asyncio
import logging
import binascii
import aiofile
import ipaddress
import struct

from reactivenet import *

from .base import Node
from .. import tools
from ..crypto import Encryption
from ..dumpers import *
from ..loaders import *


class Error(Exception):
    pass

class TrustZoneNode(Node):
    def __init__(self, name, ip_address, reactive_port, deploy_port):
        super().__init__(name, ip_address, reactive_port, deploy_port, need_lock=False)


    @staticmethod
    def load(node_dict):
        name = node_dict['name']
        ip_address = ipaddress.ip_address(node_dict['ip_address'])
        reactive_port = node_dict['reactive_port']
        deploy_port = node_dict.get('deploy_port') or reactive_port

        return TrustZoneNode(name, ip_address, reactive_port, deploy_port)


    def dump(self):
        return {
            "type": "trustzone",
            "name": self.name,
            "ip_address": str(self.ip_address),
            "reactive_port": self.reactive_port,
            "deploy_port": self.deploy_port,

        }


    async def deploy(self, module):
        assert module.node is self

        if module.deployed:
            return

        async with aiofile.AIOFile(await module.binary, "rb") as f:
            file_data = await f.read()

        id = tools.pack_int16(module.id)
        uid = module.uuid.to_bytes(16, 'big')
        size = struct.pack('!I', len(file_data) + len(id) + len(uid))

        payload = size + id + uid + file_data

        command = CommandMessageLoad(payload,
                                self.ip_address,
                                self.deploy_port)

        await self._send_reactive_command(
            command,
            log='Deploying {} on {}'.format(module.name, self.name)
            )

        module.deployed = True


    async def attest(self, module):
        assert module.node is self

        module_id = await module.get_id()

        challenge = tools.generate_key(16)

        payload =       tools.pack_int16(module_id)                     + \
                        tools.pack_int16(ReactiveEntrypoint.Attest)     + \
                        tools.pack_int16(len(challenge))                + \
                        challenge

        command = CommandMessage(ReactiveCommand.Call,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        res = await self._send_reactive_command(
                command,
                log='Attesting {}'.format(module.name)
                )

        # The result format is [tag] where the tag is the challenge's MAC
        challenge_response = res.message.payload
        expected_tag = await Encryption.AES.mac(module.key, challenge)

        if challenge_response != expected_tag:
            raise Error('Attestation of {} failed'.format(module.name))

        logging.info("Attestation of {} succeeded".format(module.name))
        module.attested = True


    async def set_key(self, module, conn_id, conn_io, encryption, key):
        assert module.node is self
        assert encryption in module.get_supported_encryption()

        module_id = await module.get_id()
        module_key = await module.get_key()

        io_id = await conn_io.get_index(module)
        nonce = module.nonce
        module.nonce += 1

        ad =    tools.pack_int8(encryption)                     + \
                tools.pack_int16(conn_id)                       + \
                tools.pack_int16(io_id)                         + \
                tools.pack_int16(nonce)

        cipher = await encryption.AES.encrypt(module_key, ad, key)

        payload =   tools.pack_int16(module_id)                       + \
                    tools.pack_int16(ReactiveEntrypoint.SetKey)       + \
                    ad                                                + \
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
