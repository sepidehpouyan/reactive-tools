import logging
import asyncio
import binascii

from .base import Module
from ..nodes import TrustZoneNode
from .. import tools
from ..crypto import Encryption
from ..dumpers import *
from ..loaders import *

class Error(Exception):
    pass


class TrustZoneModule(Module):
    def __init__(self, name, node, priority, deployed, nonce, attested, files_dir,
                    binary, id, key, inputs, outputs, entrypoints):
        super().__init__(name, node, priority, deployed, nonce, attested)

        self.files_dir = files_dir
        self.id = id
        self.key =  key
        self.inputs =  inputs
        self.outputs =  outputs
        self.entrypoints =  entrypoints

        self.uuid_for_MK = ""

        self.__build_fut = tools.init_future(binary)
        self.__attest_fut = tools.init_future(attested if attested else None)


    @staticmethod
    def load(mod_dict, node_obj):
        name = mod_dict['name']
        node = node_obj
        priority = mod_dict.get('priority')
        deployed = mod_dict.get('deployed')
        nonce = mod_dict.get('nonce')
        attested = mod_dict.get('attested')
        files_dir = mod_dict.get('files_dir')
        binary = mod_dict.get('binary')
        id = mod_dict.get('id')
        key = parse_key(mod_dict.get('key'))
        inputs = mod_dict.get('inputs')
        outputs = mod_dict.get('outputs')
        entrypoints = mod_dict.get('entrypoints')
        return TrustZoneModule(name, node, priority, deployed, nonce, attested, files_dir,
                                binary, id, key, inputs, outputs, entrypoints)


    def dump(self):
        return {
            "type": "trustzone",
            "name": self.name,
            "node": self.node.name,
            "priority": self.priority,
            "deployed": self.deployed,
            "nonce": self.nonce,
            "attested": self.attested,
            "files_dir": self.files_dir,
            "binary": dump(self.binary) if self.deployed else None,
            "id": self.id,
            "key": dump(self.key),
            "inputs":self.inputs,
            "outputs":self.outputs,
            "entrypoints":self.entrypoints
        }

    # --- Properties --- #

    @property
    async def binary(self):
        return await self.build()

    # --- Implement abstract methods --- #

    async def build(self):
        if self.__build_fut is None:
            self.__build_fut = asyncio.ensure_future(self.__build())

        return await self.__build_fut


    async def deploy(self):
        await self.node.deploy(self)


    async def attest(self):
        if self.__attest_fut is None:
            self.__attest_fut = asyncio.ensure_future(self.node.attest(self))

        return await self.__attest_fut


    async def get_id(self):
        return self.id

    async def get_input_id(self, input):
        if isinstance(input, int):
            return input

        inputs = self.inputs

        if input not in inputs:
            raise Error("Input not present in inputs")

        return inputs[input]

    async def get_output_id(self, output):
        if isinstance(output, int):
            return output

        outputs = self.outputs

        if output not in outputs:
            raise Error("Output not present in outputs")

        return outputs[output]

    async def get_entry_id(self, entry):
        if entry.isnumeric():
            return int(entry)

        entrypoints = self.entrypoints

        if entry not in entrypoints:
            raise Error("Entry not present in entrypoints")

        return entrypoints[entry]

    async def get_key(self):
        return self.key


    @staticmethod
    def get_supported_nodes():
        return [TrustZoneNode]


    @staticmethod
    def get_supported_encryption():
        return [Encryption.AES, Encryption.SPONGENT]

     # --- Other methods --- #

    async def __build(self):
        hex = '%032x' % (self.id)
        self.uuid_for_MK = '%s-%s-%s-%s-%s' % (hex[:8], hex[8:12], hex[12:16], hex[16:20], hex[20:])

        binary = ""

        compiler = "CROSS_COMPILE=arm-linux-gnueabihf-"
        plat = "PLATFORM=vexpress-qemu_virt"
        dev_kit = "TA_DEV_KIT_DIR=/optee/optee_os/out/arm/export-ta_arm32"
        binary_name = "BINARY=" + self.uuid_for_MK

        cmd = "make -C " + self.files_dir + "/" + self.name + " " + compiler + " " + plat + \
             " " + dev_kit + " " + binary_name

        await tools.run_async_shell(cmd)

        binary = self.files_dir + "/" + self.name + "/" + self.uuid_for_MK + ".ta"

        return binary
