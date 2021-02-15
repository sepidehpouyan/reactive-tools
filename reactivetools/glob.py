# build mode
BUILD_MODE = "debug"

# Apps
RA_SP = "ra_sp"
RA_CLIENT = "ra_client"

# SGX build/sign
SGX_TARGET = "x86_64-fortanix-unknown-sgx"

RELEASE_FLAG = "{}".format("" if BUILD_MODE == "debug" else "--release")
DEBUG_FLAG = "{}".format("--debug" if BUILD_MODE == "debug" else "")

BUILD_APP = "cargo build {} {{}} --manifest-path={{}}/Cargo.toml".format(RELEASE_FLAG)
BUILD_SGX_APP = "{} --target={}".format(BUILD_APP, SGX_TARGET)
CONVERT_SGX = "ftxsgx-elf2sgxs {{}} --heap-size 0x20000 --stack-size 0x20000 --threads 4 {}".format(DEBUG_FLAG)
SIGN_SGX = "sgxs-sign --key {{}} {{}} {{}} {} --xfrm 7/0 --isvprodid 0 --isvsvn 0".format(DEBUG_FLAG)
