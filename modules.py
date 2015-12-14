import logging
import asyncio
from enum import Enum
from collections import namedtuple

from elftools.elf import elffile

import sancus.crypto

from nodes import SancusNode
import tools


class Error(Exception):
    pass


class Module:
    def __init__(self, name, files, node):
        if not isinstance(node, self.get_supported_node_type()):
            clsname = lambda o: type(o).__name__
            raise Error('A {} cannot run on a {}'
                    .format(clsname(self), clsname(node)))

        self.name = name
        self.files = files
        self.node = node
        self.__build_fut = None
        self.__deploy_fut = None
        self.__key_fut = None

    @property
    async def binary(self):
        if self.__build_fut is None:
            self.__build_fut = asyncio.ensure_future(self.__build())

        return await self.__build_fut

    @property
    async def id(self):
        id, _ = await self.__deploy()
        return id

    @property
    async def symtab(self):
        _, symtab = await self.__deploy()
        return symtab

    @property
    async def key(self):
        if self.__key_fut is None:
            self.__key_fut = asyncio.ensure_future(self._calculate_key())

        return await self.__key_fut

    async def get_io_id(self, io_name):
        return await self._get_io_id(io_name)

    async def __build(self):
        logging.info('Building module %s from %s',
                     self.name, ', '.join(map(str, self.files)))

        config = self._get_build_config(_get_verbosity())
        objects = {str(p): tools.create_tmp(suffix='.o') for p in self.files}

        build_obj = lambda c, o: tools.run_async(config.cc, *config.cflags,
                                                 '-c', '-o', o, c)
        build_futs = [build_obj(c, o) for c, o in objects.items()]
        await asyncio.gather(*build_futs)

        binary = tools.create_tmp(suffix='.elf')
        await tools.run_async(config.ld, *config.ldflags,
                              '-o', binary, *objects.values())
        return binary

    async def __deploy(self):
        if self.__deploy_fut is None:
            self.__deploy_fut = asyncio.ensure_future(self.node.deploy(self))

        return await self.__deploy_fut


class SancusModule(Module):
    async def _calculate_key(self):
        linked_binary = await self.__link()

        with open(linked_binary, 'rb') as f:
            return sancus.crypto.get_sm_key(f, self.name, self.node.vendor_key)

    async def __link(self):
        linked_binary = tools.create_tmp(suffix='.elf')
        await tools.run_async('msp430-ld', '-T', await self.symtab,
                              '-o', linked_binary, await self.binary)
        return linked_binary

    async def _get_io_id(self, io_name):
        with open(await self.binary, 'rb') as f:
            elf = elffile.ELFFile(f)
            sym_name = '__sm_{}_io_{}_idx'.format(self.name, io_name)
            symbol = self.__get_symbol(elf, sym_name)

            if symbol is None:
                raise Error('Module {} has no endpoint named {}'
                                .format(self.name, io_name))

            return symbol

    @staticmethod
    def get_supported_node_type():
        return SancusNode

    @staticmethod
    def _get_build_config(verbosity):
        if verbosity == _Verbosity.Debug:
            flags = ['--debug']
        # elif verbosity == _Verbosity.Verbose:
        #     flags = ['--verbose']
        else:
            flags = []

        return _BuildConfig(cc='sancus-cc', cflags=flags,
                            ld='sancus-ld', ldflags=flags)

    @staticmethod
    def __get_symbol(elf, name):
        name = name.encode('ascii')
        for section in elf.iter_sections():
            if isinstance(section, elffile.SymbolTableSection):
                for symbol in section.iter_symbols():
                    sym_section = symbol['st_shndx']
                    if symbol.name == name and sym_section != 'SHN_UNDEF':
                        return symbol['st_value']


_BuildConfig = namedtuple('_BuildConfig', ['cc', 'cflags', 'ld', 'ldflags'])
_Verbosity = Enum('_Verbosity', ['Normal', 'Verbose', 'Debug'])


def _get_verbosity():
    log_at = logging.getLogger().isEnabledFor

    if log_at(logging.DEBUG):
        return _Verbosity.Debug
    elif log_at(logging.INFO):
        return _Verbosity.Verbose
    else:
        return _Verbosity.Normal

