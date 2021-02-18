from .base import Module
from .sancus import SancusModule
from .native import NativeModule
from .sgx import SGXModule
from .trustzone import TrustZoneModule

module_rules = {
    "sancus"    : "sancus.yaml",
    "sgx"       : "sgx.yaml",
    "native"    : "native.yaml",
    "trustzone" : "trustzone.yaml"
}

module_funcs = {
    "sancus"    : SancusModule.load,
    "sgx"       : SGXModule.load,
    "native"    : NativeModule.load,
    "trustzone" : TrustZoneModule.load
}

module_cleanup_coros = [
    SancusModule.cleanup,
    SGXModule.cleanup,
    NativeModule.cleanup,
    TrustZoneModule.cleanup
]
