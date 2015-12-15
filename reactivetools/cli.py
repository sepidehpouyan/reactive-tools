import argparse
import logging

from . import config


def _parse_args(args):
    parser = argparse.ArgumentParser()

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

    return parser.parse_args(args)


def _handle_deploy(args):
    logging.info('Deploying %s', args.config)

    conf = config.load(args.config)
    conf.install()


def main(raw_args=None):
    args = _parse_args(raw_args)
    args.command_handler(args)

