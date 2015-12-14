import logging
import tempfile
import os
import asyncio


class ProcessRunError(Exception):
    def __init__(self, args, result):
        self.args = args
        self.result = result

    def __str__(self):
        return 'Command "{}" exited with code {}' \
                    .format(' '.join(self.args), self.result)


async def run_async(*args):
    logging.debug(' '.join(args))
    process = await asyncio.create_subprocess_exec(*args)
    result = await process.wait()

    if result != 0:
        raise ProcessRunError(args, result)


def create_tmp(suffix=''):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path

