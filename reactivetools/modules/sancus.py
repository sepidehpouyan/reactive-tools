import logging
import asyncio
import binascii
from enum import Enum
from collections import namedtuple

from elftools.elf import elffile

from .base import Module
from ..nodes import SancusNode
from .. import tools
from ..crypto import Encryption


class Error(Exception):
    pass


class SancusModule(Module):
    def __init__(self, name, node, priority, deployed, files, cflags, ldflags,
                 binary=None, id=None, symtab=None, key=None):
        super().__init__(name, node, priority, deployed)

        self.__check_init_args(node, binary, id, symtab, key)

        self.files = files
        self.cflags = cflags
        self.ldflags = ldflags

        self.__build_fut = tools.init_future(binary)
        self.__deploy_fut = tools.init_future(id, symtab)
        self.__key_fut = tools.init_future(key)


    # --- Properties --- #

    @property
    async def binary(self):
        return await self.build()

    @property
    async def id(self):
        id, _ = await self.deploy()
        return id

    @property
    async def symtab(self):
        _, symtab = await self.deploy()
        return symtab

    @property
    async def key(self):
        if self.__key_fut is None:
            self.__key_fut = asyncio.ensure_future(self._calculate_key())

        return await self.__key_fut


    # --- Implement abstract methods --- #

    async def build(self):
        if self.__build_fut is None:
            self.__build_fut = asyncio.ensure_future(self.__build())

        return await self.__build_fut


    async def deploy(self):
        if self.__deploy_fut is None:
            self.__deploy_fut = asyncio.ensure_future(self.node.deploy(self))

        return await self.__deploy_fut


    async def call(self, entry, arg=None):
        return await self.node.call(self, entry, arg)


    async def get_id(self):
        return await self.id


    async def get_input_id(self, input):
        return await self.get_io_id(input)


    async def get_output_id(self, output):
        return await self.get_io_id(output)


    async def get_entry_id(self, entry):
        # If it is a number, that is the ID (given by the deployer)
        if entry.isnumeric():
            return int(entry)

        return await self._get_entry_id(entry)


    async def get_request_id(self, request):
        raise Error("Requests not supported in Sancus")


    async def get_handler_id(self, handler):
        raise Error("Handlers not supported in Sancus")


    async def get_key(self):
        return await self.key


    @staticmethod
    def get_supported_node_type():
        return SancusNode


    @staticmethod
    def get_supported_encryption():
        return [Encryption.SPONGENT]


    # --- Static methods --- #

    @staticmethod
    def _get_build_config(verbosity):
        if verbosity == tools.Verbosity.Debug:
            flags = ['--debug']
        # elif verbosity == tools.Verbosity.Verbose:
        #     flags = ['--verbose']
        else:
            flags = []

        cflags = flags
        ldflags = flags + ['--inline-arithmetic']

        return _BuildConfig(cc='sancus-cc', cflags=cflags,
                            ld='sancus-ld', ldflags=ldflags )


    # --- Others --- #

    async def get_io_id(self, io):
        # If io is a number, that is the ID (given by the deployer)
        if isinstance(io, int):
            return io

        return await self._get_io_id(io)


    def __check_init_args(self, node, binary, id, symtab, key):
        if not isinstance(node, self.get_supported_node_type()):
            clsname = lambda o: type(o).__name__
            raise Error('A {} cannot run on a {}'
                    .format(clsname(self), clsname(node)))

        # For now, either all optionals should be given or none. This might be
        # relaxed later if necessary.
        optionals = (binary, id, symtab, key)

        if None in optionals and any(map(lambda x: x is not None, optionals)):
            raise Error('Either all of the optional node parameters '
                        'should be given or none')


    async def __build(self):
        logging.info('Building module %s from %s',
                     self.name, ', '.join(map(str, self.files)))

        config = self._get_build_config(tools.get_verbosity())
        objects = {str(p): tools.create_tmp(suffix='.o') for p in self.files}

        cflags = config.cflags + self.cflags
        build_obj = lambda c, o: tools.run_async(config.cc, *cflags,
                                                 '-c', '-o', o, c)
        build_futs = [build_obj(c, o) for c, o in objects.items()]
        await asyncio.gather(*build_futs)

        binary = tools.create_tmp(suffix='.elf')
        ldflags = config.ldflags + self.ldflags

        # setting connections (if not specified in JSON file)
        if not any("--num-connections" in flag for flag in ldflags):
            ldflags.append("--num-connections {}".format(self.connections))

        await tools.run_async(config.ld, *ldflags,
                              '-o', binary, *objects.values())
        return binary



    async def _calculate_key(self):
        try:
            import sancus.crypto
        except:
            raise Error("Cannot import sancus.crypto! Maybe the Sancus toolchain is not installed, or python modules are not in PYTHONPATH")

        linked_binary = await self.__link()

        with open(linked_binary, 'rb') as f:
            key = sancus.crypto.get_sm_key(f, self.name, self.node.vendor_key)
            logging.info('Module key for %s: %s',
                         self.name, binascii.hexlify(key).decode('ascii'))
            return key


    async def __link(self):
        linked_binary = tools.create_tmp(suffix='.elf')

        # NOTE: we use '--noinhibit-exec' flag because the linker complains
        #       if the addresses of .bss section are not aligned to 2 bytes
        #       using this flag instead, the output file is still generated
        await tools.run_async('msp430-ld', '-T', await self.symtab,
                      '-o', linked_binary, '--noinhibit-exec', await self.binary)
        return linked_binary


    async def _get_io_id(self, io_name):
        sym_name = '__sm_{}_io_{}_idx'.format(self.name, io_name)
        symbol = await self.__get_symbol(sym_name)

        if symbol is None:
            raise Error('Module {} has no endpoint named {}'
                            .format(self.name, io_name))

        return symbol


    async def _get_entry_id(self, entry_name):
        sym_name = '__sm_{}_entry_{}_idx'.format(self.name, entry_name)
        symbol = await self.__get_symbol(sym_name)

        if symbol is None:
            raise Error('Module {} has no entry named {}'
                            .format(self.name, entry_name))

        return symbol


    async def __get_symbol(self, name):
        if not await self.binary:
            raise Error("ELF file not present for {}, cannot extract symbol ID of {}".format(self.name, name))

        with open(await self.binary, 'rb') as f:
            elf = elffile.ELFFile(f)
            for section in elf.iter_sections():
                if isinstance(section, elffile.SymbolTableSection):
                    for symbol in section.iter_symbols():
                        sym_section = symbol['st_shndx']
                        if symbol.name == name and sym_section != 'SHN_UNDEF':
                            return symbol['st_value']


_BuildConfig = namedtuple('_BuildConfig', ['cc', 'cflags', 'ld', 'ldflags'])
