from .base import Node
from .sancus import SancusNode
from .native import NativeNode
from .sgx import SGXNode

node_rules = {
    "sancus"    : "sancus.yaml",
    "sgx"       : "sgx.yaml",
    "native"    : "native.yaml"
}

node_funcs = {
    "sancus"    : SancusNode.load,
    "sgx"       : SGXNode.load,
    "native"    : NativeNode.load
}

node_cleanup_coros = [
    SancusNode.cleanup,
    SGXNode.cleanup,
    NativeNode.cleanup
]
