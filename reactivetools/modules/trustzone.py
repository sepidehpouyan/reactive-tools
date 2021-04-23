# Here some common libs, you might need more, or you might not need some of these.
# If you do not use one library, remove it
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


# Look at base.py and other implementation for hints about what you have to do
# You might need to override some additional functions in base.py (or maybe not)

class TrustZoneModule(Module):
    # add init parameters as you need
    def __init__(self, name, node, priority, deployed, nonce):
        super().__init__(name, node, priority, deployed, nonce)
        raise Error("TrustZoneModule::__init__ not implemented")


    @staticmethod
    def load(mod_dict, node_obj):
        raise Error("TrustZoneModule::load not implemented")


    def dump(self):
        raise Error("TrustZoneModule::dump not implemented")


    # --- Implement abstract methods --- #

    async def build(self):
        raise Error("TrustZoneModule::build not implemented")


    async def deploy(self):
        raise Error("TrustZoneModule::deploy not implemented")


    async def attest(self):
        raise Error("TrustZoneModule::attest not implemented")


    async def get_id(self):
        raise Error("TrustZoneModule::get_id not implemented")


    async def get_input_id(self, input):
        raise Error("TrustZoneModule::get_input_id not implemented")


    async def get_output_id(self, output):
        raise Error("TrustZoneModule::get_output_id not implemented")


    async def get_entry_id(self, entry):
        raise Error("TrustZoneModule::get_entry_id not implemented")


    async def get_key(self):
        raise Error("TrustZoneModule::get_key not implemented")


    @staticmethod
    def get_supported_nodes():
        return [TrustZoneNode]


    @staticmethod
    def get_supported_encryption():
        return [Encryption.AES, Encryption.SPONGENT]
