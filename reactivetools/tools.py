import logging
import tempfile
import os
import asyncio
import base64
import struct
from enum import Enum

from . import glob

class ProcessRunError(Exception):
    def __init__(self, args, result):
        self.args = args
        self.result = result

    def __str__(self):
        return 'Command "{}" exited with code {}' \
                    .format(' '.join(self.args), self.result)


class Error(Exception):
    pass


Verbosity = Enum('Verbosity', ['Normal', 'Verbose', 'Debug'])


def get_verbosity():
    log_at = logging.getLogger().isEnabledFor

    if log_at(logging.DEBUG):
        return Verbosity.Debug
    elif log_at(logging.INFO):
        return Verbosity.Verbose
    else:
        return Verbosity.Normal


def get_stderr():
    if get_verbosity() == Verbosity.Debug:
        return None
    else:
        return open(os.devnull, "wb")


def init_future(*results):
    if all(map(lambda x: x is None, results)):
        return None

    fut = asyncio.Future()
    result = results[0] if len(results) == 1 else results
    fut.set_result(result)
    return fut


async def run_async(*args, output_file=os.devnull, env=None):
    logging.debug(' '.join(args))

    process = await asyncio.create_subprocess_exec(*args,
                                            stdout=open(output_file, 'wb'),
                                            stderr=get_stderr(),
                                            env=env)
    result = await process.wait()

    if result != 0:
        raise ProcessRunError(args, result)


async def run_async_background(*args, env=None):
    logging.debug(' '.join(args))
    process = await asyncio.create_subprocess_exec(*args,
                                            stdout=open(os.devnull, 'wb'),
                                            stderr=get_stderr(),
                                            env=env)

    return process


async def run_async_output(*args, env=None):
    cmd = ' '.join(args)
    logging.debug(cmd)
    process = await asyncio.create_subprocess_exec(*args,
                                            stdout=asyncio.subprocess.PIPE,
                                            stderr=asyncio.subprocess.PIPE,
                                            env=env)
    out, err = await process.communicate()
    result = await process.wait()

    if result != 0:
        raise ProcessRunError(args, result)

    return out, err


async def run_async_shell(*args, env=None):
    cmd = ' '.join(args)
    logging.debug(cmd)
    process = await asyncio.create_subprocess_shell(cmd,
                                            stdout=open(os.devnull, 'wb'),
                                            stderr=get_stderr(),
                                            env=env)
    result = await process.wait()

    if result != 0:
        raise ProcessRunError(args, result)


def create_tmp(suffix='', dir=''):
    dir = os.path.join(glob.BUILD_DIR, dir)
    fd, path = tempfile.mkstemp(suffix=suffix, dir=dir)
    os.close(fd)
    return path


def create_tmp_dir():
    return tempfile.mkdtemp(dir=glob.BUILD_DIR)


def generate_key(length):
    return os.urandom(length)


def pack_int8(i):
    return struct.pack('!B', i)

def unpack_int8(i):
    return struct.unpack('!B', i)[0]

def pack_int16(i):
    return struct.pack('!H', i)

def unpack_int16(i):
    return struct.unpack('!H', i)[0]

def pack_int32(i):
    return struct.pack('!I', i)

def unpack_int32(i):
    return struct.unpack('!I', i)[0]
