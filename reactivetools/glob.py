from enum import IntEnum
import os

BUILD_DIR = os.path.join(os.getcwd(), "build")

class Error(Exception):
    pass

class BuildMode(IntEnum):
    DEBUG       = 0
    RELEASE     = 1

    @staticmethod
    def from_str(mode):
        mode_lower = mode.lower()

        if mode_lower == "debug":
            return BuildMode.DEBUG
        if mode_lower == "release":
            return BuildMode.RELEASE

        raise Error("Bad BuildMode: {}".format(mode))

    def to_str(self):
        if self == BuildMode.DEBUG:
            return "debug"
        if self == BuildMode.RELEASE:
            return "release"

        raise Error("BuildMode::to_str failed: this should never happen")


__BUILD_MODE = BuildMode.DEBUG

def set_build_mode(mode):
    global __BUILD_MODE
    __BUILD_MODE = BuildMode.from_str(mode)

def get_build_mode():
    return __BUILD_MODE
