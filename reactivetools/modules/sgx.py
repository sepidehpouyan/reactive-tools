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
ATTESTER = "sgx-attester"

# SGX build/sign
SGX_TARGET = "x86_64-fortanix-unknown-sgx"
BUILD_APP = "cargo build {{}} {{}} --target={} --manifest-path={{}}/Cargo.toml".format( SGX_TARGET)
CONVERT_SGX = "ftxsgx-elf2sgxs {} --heap-size 0x20000 --stack-size 0x20000 --threads 4 {}"
SIGN_SGX = "sgxs-sign --key {} {} {} {} --xfrm 7/0 --isvprodid 0 --isvsvn 0"


class Object():
    pass

class Error(Exception):
    pass


class SGXModule(Module):
    sp_lock = asyncio.Lock()

    def __init__(self, name, node, priority, deployed, nonce, attested, vendor_key,
                ra_settings, features, id, binary, key, sgxs, signature, data,
                folder, port):
        super().__init__(name, node, priority, deployed, nonce, attested)

        self.__generate_fut = tools.init_future(data)
        self.__build_fut = tools.init_future(binary)
        self.__convert_sign_fut = tools.init_future(sgxs, signature)
        self.__attest_fut = tools.init_future(key)
        self.__sp_keys_fut = asyncio.ensure_future(self.__generate_sp_keys())

        self.key = key
        self.vendor_key = vendor_key
        self.ra_settings = ra_settings
        self.features = [] if features is None else features
        self.id = id if id is not None else node.get_module_id()
        self.port = port or self.node.reactive_port + self.id
        self.output = os.path.join(glob.BUILD_DIR, folder)
        self.folder = folder


    @staticmethod
    def load(mod_dict, node_obj):
        name = mod_dict['name']
        node = node_obj
        priority = mod_dict.get('priority')
        deployed = mod_dict.get('deployed')
        nonce = mod_dict.get('nonce')
        attested = mod_dict.get('attested')
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
        port = mod_dict.get('port')

        return SGXModule(name, node, priority, deployed, nonce, attested, vendor_key,
                settings, features, id, binary, key, sgxs, signature, data, folder,
                port)

    def dump(self):
        return {
            "type": "sgx",
            "name": self.name,
            "node": self.node.name,
            "priority": self.priority,
            "deployed": self.deployed,
            "nonce": self.nonce,
            "attested": self.attested,
            "vendor_key": self.vendor_key,
            "ra_settings": self.ra_settings,
            "features": self.features,
            "id": self.id,
            "binary": dump(self.binary) if self.deployed else None,
            "sgxs": dump(self.sgxs) if self.deployed else None,
            "signature": dump(self.sig) if self.deployed else None,
            "key": dump(self.key) if self.attested else None,
            "data": dump(self.data) if self.deployed else None,
            "folder": self.folder,
            "port": self.port
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
        await self.node.deploy(self)


    async def attest(self):
        if self.__attest_fut is None:
            self.__attest_fut = asyncio.ensure_future(self.__attest())

        await self.__attest_fut


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
        return self.key


    @staticmethod
    def get_supported_nodes():
        return [SGXNode]


    @staticmethod
    def get_supported_encryption():
        return [Encryption.AES, Encryption.SPONGENT]


    # --- Static methods --- #

    @staticmethod
    async def cleanup():
        pass


    # --- Others --- #

    async def get_ra_sp_pub_key(self):
        pub, _, _ = await self.__sp_keys_fut

        return pub


    async def get_ra_sp_priv_key(self):
        _, priv, _ = await self.__sp_keys_fut

        return priv


    async def get_ias_root_certificate(self):
        _, _, cert = await self.__sp_keys_fut

        return cert


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
        args.spkey = await self.get_ra_sp_pub_key()
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


    async def __attest(self):
        env = {}
        env["SP_PRIVKEY"] = await self.get_ra_sp_priv_key()
        env["IAS_CERT"] = await self.get_ias_root_certificate()
        env["ENCLAVE_SETTINGS"] = self.ra_settings
        env["ENCLAVE_SIG"] = await self.sig
        env["ENCLAVE_HOST"] = str(self.node.ip_address)
        env["ENCLAVE_PORT"] = str(self.port)
        env["AESM_PORT"] = str(self.node.aesm_port)

        out, _ = await tools.run_async_output(ATTESTER, env=env)
        key_arr = eval(out) # from string to array
        key = bytes(key_arr) # from array to bytes

        logging.info("Done Remote Attestation of {}. Key: {}".format(self.name, key_arr))
        self.key = key
        self.attested = True


    async def __generate_sp_keys(self):
        async with self.sp_lock:
            priv = os.path.join(glob.BUILD_DIR, "private_key.pem")
            pub = os.path.join(glob.BUILD_DIR, "public_key.pem")
            ias_cert = os.path.join(glob.BUILD_DIR, "ias_root_ca.pem")

            # check if already generated in a previous run
            if all(map(lambda x : os.path.exists(x), [priv, pub, ias_cert])):
                return pub, priv, ias_cert

            cmd = "openssl"

            args_private = "genrsa -f4 -out {} 2048".format(priv).split()
            args_public = "rsa -in {} -outform PEM -pubout -out {}".format(priv, pub).split()

            await tools.run_async_shell(cmd, *args_private)
            await tools.run_async_shell(cmd, *args_public)

            cmd = "curl"
            url = "https://certificates.trustedservices.intel.com/Intel_SGX_Attestation_RootCA.pem".split()
            await tools.run_async(cmd, *url, output_file=ias_cert)

            return pub, priv, ias_cert
