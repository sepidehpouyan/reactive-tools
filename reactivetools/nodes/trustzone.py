# Here some common libs, you might need more, or you might not need some of these.
# If you do not use one library, remove it
import asyncio
import logging
import binascii
import aiofile
import ipaddress

from reactivenet import *

from .base import Node
from .. import tools
from ..dumpers import *
from ..loaders import *

class Error(Exception):
    pass

# Look at base.py and other implementation for hints about what you have to do
# You might need to override some additional functions in base.py (or maybe not)

class TrustZoneNode(Node):
    # add init parameters as you need
    def __init__(self, name, ip_address, reactive_port, deploy_port):
        # I do not think you need the lock; this was a sort of "hack" I did
        # for Sancus, since the connection to the computer was made through UART
        super().__init__(name, ip_address, reactive_port, deploy_port, need_lock=False)
        raise Error("TrustZoneNode::__init__ not implemented")


    @staticmethod
    def load(node_dict):
        raise Error("TrustZoneNode::load not implemented")


    def dump(self):
        raise Error("TrustZoneNode::dump not implemented")


    async def deploy(self, module):
        raise Error("TrustZoneNode::deploy not implemented")


    async def set_key(self, module, conn_id, conn_io, encryption, key):
        raise Error("TrustZoneNode::set_key not implemented")
