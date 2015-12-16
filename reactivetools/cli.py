import argparse
import logging
import asyncio
import pdb
import sys

from . import config


def _setup_logging(args):
    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(format='%(message)s', level=level)


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

    deploy_parser = subparsers.add_parser(
        'deploy',
        help='Deploy a reactive network')
    deploy_parser.set_defaults(command_handler=_handle_deploy)
    deploy_parser.add_argument(
        'config',
        help='Configuration file describing the network')
    deploy_parser.add_argument(
        '--result',
        help='File to write the resulting configuration to')

    return parser.parse_args(args)


def _handle_deploy(args):
    logging.info('Deploying %s', args.config)

    conf = config.load(args.config)
    conf.install()

    if args.result is not None:
        logging.info('Writing post-deployment configuration to %s', args.result)
        config.dump(conf, args.result)


def main(raw_args=None):
    args = _parse_args(raw_args)

    _setup_logging(args)
    _setup_pdb(args)

    args.command_handler(args)

    # If we don't close the event loop explicitly, there is an unhandled
    # exception being thrown from its destructor. Not sure why but closing it
    # here prevents annoying noise.
    asyncio.get_event_loop().close()

