import asyncio
import functools
import types
import binascii

@functools.singledispatch
def dump(obj):
    assert False, 'No dumper for {}'.format(type(obj))


@dump.register(list)
def _(l):
    return [dump(e) for e in l]


@dump.register(bytes)
@dump.register(bytearray)
def _(bs):
    return binascii.hexlify(bs).decode('ascii')


@dump.register(str)
@dump.register(int)
def _(x):
    return x


@dump.register(tuple)
def _(t):
    return { t[1] : t[0] }


@dump.register(types.CoroutineType)
def _(coro):
    return dump(asyncio.get_event_loop().run_until_complete(coro))


@dump.register(dict)
def _(dict):
    return dict
