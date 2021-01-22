import base64
import asyncio
from enum import IntEnum

from . import tools
from . import glob

class Error(Exception):
    pass

class Encryption(IntEnum):
    AES         = 0x0
    SPONGENT    = 0x1

    @staticmethod
    def from_str(str):
        lower_str = str.lower()

        if lower_str == "aes":
            return Encryption.AES
        if lower_str == "spongent":
            return Encryption.SPONGENT

        raise Error("No matching encryption type for {}".format(str))

    def to_str(self):
        if self == Encryption.AES:
            return "aes"
        if self == Encryption.SPONGENT:
            return "spongent"

    def get_key_size(self):
        if self == Encryption.AES:
            return 16
        if self == Encryption.SPONGENT:
            return tools.get_sancus_key_size()

    async def encrypt(self, key, ad, data):
        if self == Encryption.AES:
            return await encrypt_aes(key, ad, data)
        if self == Encryption.SPONGENT:
            return await encrypt_spongent(key, ad, data)

    async def decrypt(self, key, ad, data):
        if self == Encryption.AES:
            return await decrypt_aes(key, ad, data)
        if self == Encryption.SPONGENT:
            return await decrypt_spongent(key, ad, data)

    async def mac(self, key, ad):
        if self == Encryption.AES:
            return await encrypt_aes(key, ad)
        if self == Encryption.SPONGENT:
            return await encrypt_spongent(key, ad)


async def encrypt_aes(key, ad, data=[]):
    args = [base64.b64encode(ad).decode(),
            base64.b64encode(data).decode(),
            base64.b64encode(key).decode()]

    out = await tools.run_async_output(glob.ENCRYPTOR, *args)
    return base64.b64decode(out)


async def decrypt_aes(key, ad, data=[]):
    args = [base64.b64encode(ad).decode(),
            base64.b64encode(data).decode(),
            base64.b64encode(key).decode(),
            "-d"]

    try:
        out = await tools.run_async_output(glob.ENCRYPTOR, *args)
        return base64.b64decode(out)
    except:
        raise Error("Decryption failed")


async def encrypt_spongent(key, ad, data=[]):
    try:
        import sancus.crypto
    except:
        raise Error("Cannot import sancus.crypto! Maybe the Sancus toolchain is not installed, or python modules are not in PYTHONPATH")

    cipher, tag = sancus.crypto.wrap(key, ad, data)
    return cipher + tag


async def decrypt_spongent(key, ad, data=[]):
    try:
        import sancus.crypto
        import sancus.config
    except:
        raise Error("Cannot import sancus.crypto! Maybe the Sancus toolchain is not installed, or python modules are not in PYTHONPATH")

    # data should be formed like this: [cipher, tag]
    tag_size = tools.get_sancus_key_size()
    cipher = data[:-tag_size]
    tag = data[-tag_size:]

    plain = sancus.crypto.unwrap(key, ad, cipher, tag)

    if plain is None:
        raise Error("Decryption failed")

    return plain
