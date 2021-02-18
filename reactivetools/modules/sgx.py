import asyncio
import logging
import os
import aiofile

from .base import Module

from ..nodes import SGXNode
from .. import tools
from .. import glob
from ..crypto import Encryption
from ..dumpers import *
from ..loaders import *

# Apps
RA_SP = "ra_sp"
RA_CLIENT = "ra_client"

# SGX build/sign
SGX_TARGET = "x86_64-fortanix-unknown-sgx"
BUILD_APP = "cargo build {{}} {{}} --target={} --manifest-path={{}}/Cargo.toml".format( SGX_TARGET)
CONVERT_SGX = "ftxsgx-elf2sgxs {} --heap-size 0x20000 --stack-size 0x20000 --threads 4 {}"
SIGN_SGX = "sgxs-sign --key {} {} {} {} --xfrm 7/0 --isvprodid 0 --isvsvn 0"


class Object():
    pass

class Error(Exception):
    pass


async def _generate_sp_keys():
    dir = tools.create_tmp_dir()

    priv = os.path.join(dir, "private_key.pem")
    pub = os.path.join(dir, "public_key.pem")

    cmd = "ssh-keygen"
    args_private = "-t rsa -f {} -b 2048 -N ''".format(priv).split()
    args_public = "-f {}.pub -e -m pem".format(priv).split()

    await tools.run_async_shell(cmd, *args_private)
    await tools.run_async(cmd, *args_public, output_file=pub)

    return pub, priv


async def _run_ra_sp():
    # kill old ra_sp (if running)
    try:
        await tools.run_async("pkill", "-f", RA_SP)
    except:
        pass

    arg = await SGXModule._get_ra_sp_priv_key()

    return await tools.run_async_background(RA_SP, arg)


class SGXModule(Module):
    _sp_keys_fut = asyncio.ensure_future(_generate_sp_keys())
    _ra_sp_fut = asyncio.ensure_future(_run_ra_sp())

    def __init__(self, name, node, priority, deployed, nonce, vendor_key,
                ra_settings, features, id, binary, key, sgxs, signature, data,
                folder):
        super().__init__(name, node, priority, deployed, nonce)

        self.__deploy_fut = tools.init_future(id) # not completely true
        self.__generate_fut = tools.init_future(data)
        self.__build_fut = tools.init_future(binary)
        self.__convert_sign_fut = tools.init_future(sgxs, signature)
        self.__ra_fut = tools.init_future(key)

        self.vendor_key = vendor_key
        self.ra_settings = ra_settings
        self.features = [] if features is None else features
        self.id = id if id is not None else node.get_module_id()
        self.port = self.node.reactive_port + self.id
        self.output = os.path.join(os.getcwd(), "build", name)
        self.folder = folder


    @staticmethod
    def load(mod_dict, node_obj):
        name = mod_dict['name']
        node = node_obj
        priority = mod_dict.get('priority')
        deployed = mod_dict.get('deployed')
        nonce = mod_dict.get('nonce')
        vendor_key = parse_file_name(mod_dict['vendor_key'])
        settings = parse_file_name(mod_dict['ra_settings'])
        features = mod_dict.get('features')
        id = mod_dict.get('id')
        binary = parse_file_name(mod_dict.get('binary'))
        key = parse_key(mod_dict.get('key'))
        sgxs = parse_file_name(mod_dict.get('sgxs'))
        signature = parse_file_name(mod_dict.get('signature'))
        data = mod_dict.get('data')
        folder = mod_dict.get('folder') or name

        return SGXModule(name, node, priority, deployed, nonce, vendor_key,
                settings, features, id, binary, key, sgxs, signature, data, folder)

    def dump(self):
        return {
            "type": "sgx",
            "name": self.name,
            "node": self.node.name,
            "priority": self.priority,
            "deployed": self.deployed,
            "nonce": self.nonce,
            "vendor_key": self.vendor_key,
            "ra_settings": self.ra_settings,
            "features": self.features,
            "id": self.id,
            "binary": dump(self.binary),
            "sgxs": dump(self.sgxs),
            "signature": dump(self.sig),
            "key": dump(self.key),
            "data": dump(self.data),
            "folder": self.folder
        }

    # --- Properties --- #

    @property
    async def data(self):
        data = await self.generate_code()
        return data

    @property
    async def inputs(self):
        data = await self.data
        return data["inputs"]


    @property
    async def outputs(self):
        data = await self.data
        return data["outputs"]


    @property
    async def entrypoints(self):
        data = await self.data
        return data["entrypoints"]


    @property
    async def handlers(self):
        data = await self.data
        return data["handlers"]


    @property
    async def requests(self):
        data = await self.data
        return data["requests"]

    @property
    async def key(self):
        if self.__ra_fut is None:
            self.__ra_fut = asyncio.ensure_future(self.__remote_attestation())

        return await self.__ra_fut


    @property
    async def binary(self):
        return await self.build()


    @property
    async def sgxs(self):
        if self.__convert_sign_fut is None:
            self.__convert_sign_fut = asyncio.ensure_future(self.__convert_sign())

        sgxs, _ = await self.__convert_sign_fut

        return sgxs


    @property
    async def sig(self):
        if self.__convert_sign_fut is None:
            self.__convert_sign_fut = asyncio.ensure_future(self.__convert_sign())

        _, sig = await self.__convert_sign_fut

        return sig


    # --- Implement abstract methods --- #

    async def build(self):
        if self.__build_fut is None:
            self.__build_fut = asyncio.ensure_future(self.__build())

        return await self.__build_fut


    async def deploy(self):
        if self.__deploy_fut is None:
            self.__deploy_fut = asyncio.ensure_future(self.node.deploy(self))

        await self.__deploy_fut


    async def get_id(self):
        return self.id


    async def get_input_id(self, input):
        if isinstance(input, int):
            return input

        inputs = await self.inputs

        if input not in inputs:
            raise Error("Input not present in inputs")

        return inputs[input]


    async def get_output_id(self, output):
        if isinstance(output, int):
            return output

        outputs = await self.outputs

        if output not in outputs:
            raise Error("Output not present in outputs")

        return outputs[output]


    async def get_entry_id(self, entry):
        if entry.isnumeric():
            return int(entry)

        entrypoints = await self.entrypoints

        if entry not in entrypoints:
            raise Error("Entry not present in entrypoints")

        return entrypoints[entry]


    async def get_request_id(self, request):
        if isinstance(request, int):
            return request

        requests = await self.requests

        if request not in requests:
            raise Error("Request not present in requests")

        return requests[request]


    async def get_handler_id(self, handler):
        if isinstance(handler, int):
            return handler

        handlers = await self.handlers

        if handler not in handlers:
            raise Error("Handler not present in handlers")

        return handlers[handler]


    async def get_key(self):
        return await self.key


    @staticmethod
    def get_supported_nodes():
        return [SGXNode]


    @staticmethod
    def get_supported_encryption():
        return [Encryption.AES, Encryption.SPONGENT]


    # --- Static methods --- #

    @staticmethod
    async def _get_ra_sp_pub_key():
        pub, _ = await SGXModule._sp_keys_fut

        return pub


    @staticmethod
    async def _get_ra_sp_priv_key():
        _, priv = await SGXModule._sp_keys_fut

        return priv


    @staticmethod
    async def cleanup():
        try:
            process = await SGXModule._ra_sp_fut
            process.kill()
            await asyncio.sleep(0.1) # to avoid weird error messages
        except:
            pass


    # --- Others --- #

    async def generate_code(self):
        if self.__generate_fut is None:
            self.__generate_fut = asyncio.ensure_future(self.__generate_code())

        return await self.__generate_fut


    async def __generate_code(self):
        try:
            import rustsgxgen
        except:
            raise Error("rust-sgx-gen not installed! Check README.md")

        args = Object()

        args.input = self.folder
        args.output = self.output
        args.moduleid = self.id
        args.emport = self.node.deploy_port
        args.runner = rustsgxgen.Runner.SGX
        args.spkey = await self._get_ra_sp_pub_key()
        args.print = None

        data, _ = rustsgxgen.generate(args)
        logging.info("Generated code for module {}".format(self.name))

        return data


    async def __build(self):
        await self.generate_code()

        release = "--release" if glob.get_build_mode() == glob.BuildMode.RELEASE else ""
        features = "--features " + " ".join(self.features) if self.features else ""

        cmd = BUILD_APP.format(release, features, self.output).split()
        await tools.run_async(*cmd)

        binary = os.path.join(self.output, "target", SGX_TARGET,
                        glob.get_build_mode().to_str(), self.folder)

        logging.info("Built module {}".format(self.name))

        return binary


    async def __convert_sign(self):
        binary = await self.binary
        debug = "--debug" if glob.get_build_mode() == glob.BuildMode.DEBUG else ""

        sgxs = "{}.sgxs".format(binary)
        sig = "{}.sig".format(binary)

        cmd_convert = CONVERT_SGX.format(binary, debug).split()
        cmd_sign = SIGN_SGX.format(self.vendor_key, sgxs, sig, debug).split()

        await tools.run_async(*cmd_convert)
        await tools.run_async(*cmd_sign)

        logging.info("Converted & signed module {}".format(self.name))

        return sgxs, sig


    async def __remote_attestation(self):
        await self.deploy()
        await self._ra_sp_fut

        args = [str(self.node.ip_address), str(self.port), self.ra_settings, await self.sig]
        key = await tools.run_async_output(RA_CLIENT, *args)

        logging.info("Done Remote Attestation of {}".format(self.name))

        return key
