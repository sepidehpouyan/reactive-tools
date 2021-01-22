import argparse
import logging
import asyncio
import pdb
import sys
import binascii
import os

from . import config
from . import tools


class Error(Exception):
    pass


def _setup_logging(args):
    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    err_handler = logging.StreamHandler(sys.stderr)
    err_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    err_handler.setLevel(logging.WARNING)
    logging.root.addHandler(err_handler)

    class InfoFilter(logging.Filter):
        def filter(self, record):
            return record.levelno < logging.WARNING

    info_handler = logging.StreamHandler(sys.stdout)
    info_handler.setFormatter(logging.Formatter('%(message)s'))
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(InfoFilter())
    logging.root.addHandler(info_handler)

    logging.root.setLevel(level)


def _setup_pdb(args):
    if args.debug:
        sys.excepthook = \
                lambda type, value, traceback: pdb.post_mortem(traceback)


def _parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--verbose',
        help='Verbose output',
        action='store_true')
    parser.add_argument(
        '--debug',
        help='Debug output and open PDB on uncaught exceptions',
        action='store_true')

    subparsers = parser.add_subparsers(dest='command')
    # Workaround a Python bug. See http://bugs.python.org/issue9253#msg186387
    subparsers.required = True

    # deploy
    deploy_parser = subparsers.add_parser(
        'deploy',
        help='Deploy a reactive network')
    deploy_parser.set_defaults(command_handler=_handle_deploy)
    deploy_parser.add_argument(
        'config',
        help='Name of the configuration file describing the network')
    deploy_parser.add_argument(
        '--workspace',
        help='Root directory containing all the modules and the configuration file',
        default=".")
    deploy_parser.add_argument(
        '--result',
        help='File to write the resulting configuration to')
    deploy_parser.add_argument(
        '--deploy-in-order',
        help='Deploy modules in the order they are found in the config file',
        action='store_true')
    deploy_parser.add_argument(
        '--sancus-security',
        help='Override default Sancus key length, in bits (for spongent connections)',
        type=int)

    # build
    build_parser = subparsers.add_parser(
        'build',
        help='Build the executables of the SMs as declared in the input configuration file (for debugging)')
    build_parser.set_defaults(command_handler=_handle_build)
    build_parser.add_argument(
        'config',
        help='Name of the configuration file describing the network')
    build_parser.add_argument(
        '--workspace',
        help='Root directory containing all the modules and the configuration file',
        default=".")

    # call
    call_parser = subparsers.add_parser(
        'call',
        help='Call a deployed module')
    call_parser.set_defaults(command_handler=_handle_call)
    call_parser.add_argument(
        '--config',
        help='Specify configuration file to use '
             '(the result of a previous "deploy" run)',
        required=True)
    call_parser.add_argument(
        '--module',
        help='Name of the module to call',
        required=True)
    call_parser.add_argument(
        '--entry',
        help='Name of the module\'s entry point to call',
        required=True)
    call_parser.add_argument(
        '--arg',
        help='Argument to pass to the entry point (hex byte array)',
        type=binascii.unhexlify,
        default=None)

    # output
    output_parser = subparsers.add_parser(
        'output',
        help='Trigger the output of a \"direct\" connection (between deployer and SM)')
    output_parser.set_defaults(command_handler=_handle_output)
    output_parser.add_argument(
        '--config',
        help='Specify configuration file to use '
             '(the result of a previous "deploy" run)',
        required=True)
    output_parser.add_argument(
        '--connection',
        help='Connection ID or name of the connection',
        required=True)
    output_parser.add_argument(
        '--arg',
        help='Argument to pass to the output (hex byte array)',
        type=binascii.unhexlify,
        default=None)

    # request
    request_parser = subparsers.add_parser(
        'request',
        help='Trigger the request of a \"direct\" connection (between deployer and SM)')
    request_parser.set_defaults(command_handler=_handle_request)
    request_parser.add_argument(
        '--config',
        help='Specify configuration file to use '
             '(the result of a previous "deploy" run)',
        required=True)
    request_parser.add_argument(
        '--connection',
        help='Connection ID or name of the connection',
        required=True)
    request_parser.add_argument(
        '--arg',
        help='Argument to pass to the request (hex byte array)',
        type=binascii.unhexlify,
        default=None)

    return parser.parse_args(args)


def _handle_deploy(args):
    logging.info('Deploying %s', args.config)

    os.chdir(args.workspace)
    conf = config.load(args.config)

    if args.deploy_in_order:
        conf.deploy_modules_ordered()

    conf.install()

    if args.result is not None:
        logging.info('Writing post-deployment configuration to %s', args.result)
        config.dump(conf, args.result)

    conf.cleanup()


def _handle_build(args):
    logging.info('Building %s', args.config)

    os.chdir(args.workspace)
    conf = config.load(args.config)
    conf.build()
    conf.cleanup()


def _handle_call(args):
    logging.info('Calling %s:%s', args.module, args.entry)

    conf = config.load(args.config, False)
    module = conf.get_module(args.module)

    asyncio.get_event_loop().run_until_complete(
                                            module.call(args.entry, args.arg))

    conf.cleanup()


def _handle_output(args):
    logging.info('Triggering output of connection %s', args.connection)

    conf = config.load(args.config, False)

    if args.connection.isnumeric():
        conn = conf.get_connection_by_id(int(args.connection))
    else:
        conn = conf.get_connection_by_name(args.connection)


    if not conn.direct:
        raise Error("Connection is not direct.")

    if not conn.to_input:
        raise Error("Not a output-input connection")

    asyncio.get_event_loop().run_until_complete(
                                    conn.to_module.node.output(conn, args.arg))

    conn.nonce += 1
    config.dump(conf, args.config)

    conf.cleanup()


def _handle_request(args):
    logging.info('Triggering request of connection %s', args.connection)

    conf = config.load(args.config, False)

    if args.connection.isnumeric():
        conn = conf.get_connection_by_id(int(args.connection))
    else:
        conn = conf.get_connection_by_name(args.connection)


    if not conn.direct:
        raise Error("Connection is not direct.")

    if not conn.to_handler:
        raise Error("Not a request-handler connection")

    asyncio.get_event_loop().run_until_complete(
                                    conn.to_module.node.request(conn, args.arg))

    conn.nonce += 2
    config.dump(conf, args.config)

    conf.cleanup()


def main(raw_args=None):
    args = _parse_args(raw_args)

    _setup_logging(args)
    _setup_pdb(args)

    try:
        tools.set_sancus_key_size(args.sancus_security)
    except:
        pass

    try:
        args.command_handler(args)
    except BaseException as e:
        if args.debug:
            raise

        logging.error(e)
        return 1
    finally:
        # If we don't close the event loop explicitly, there is an unhandled
        # exception being thrown from its destructor. Not sure why but closing
        # it here prevents annoying noise.
        asyncio.get_event_loop().close()
