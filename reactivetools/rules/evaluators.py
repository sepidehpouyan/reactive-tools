import yaml
import os
import logging

from ..descriptor import DescriptorType

def is_present(dict, key):
    return key in dict and dict[key] is not None


def has_value(dict, key, value):
    return is_present(dict, key) and dict[key] == value


def is_positive_number(val, bits=16):
    if not isinstance(val, int):
        return False

    if not 1 <= val <= 2**bits - 1:
        return False

    return True


def authorized_keys(dict, keys):
    for key in dict:
        if key not in keys:
            return False

    return True


# file: relative path of the file from the "rules" directory
# e.g., i want to load the rules of sancus.yaml under nodes folder:
#       file == "nodes/sancus.yaml"
def load_rules(file):
    try:
        path = os.path.join(os.path.dirname(__file__), file)
        data = DescriptorType.YAML.load(path)
        return data if data is not None else {}
    except Exception as e:
        logging.warning("Something went wrong during load of {}".format(file))
        logging.debug(e)
        return {}
