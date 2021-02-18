import asyncio
import logging
import binascii

from abc import ABC, abstractmethod
from enum import IntEnum

from reactivenet import *

from .. import tools

class Error(Exception):
    pass

class Node(ABC):
    def __init__(self, name, ip_address, reactive_port, deploy_port, need_lock=False):
        """
        Generic attributes common to all Node subclasses

        ### Attributes ###
        name (str): name of the module
        ip_address (ip_address): IP of the node
        reactive_port (int): port where the event manager listens for events
        deploy_port (int): port where the event manager listens for new modules
        need_lock (bool): a bool indicating if the events need to be
                    delivered one at a time due to some limitations on the EM
        """

        self.name = name
        self.ip_address = ip_address
        self.reactive_port = reactive_port
        self.deploy_port = deploy_port

        if need_lock:
            self.__lock = asyncio.Lock()
        else:
            self.__lock = None



    """
    ### Description ###
    Creates a XXXNode object from a dict
    This should take all the information declared in the deployment descriptor
    and store it into the class as attributes.

    ### Parameters ###
    node_dict (dict): dictionary containing the definition of the node

    ### Returns ###
    An instance of the XXXNode class
    """
    @staticmethod
    @abstractmethod
    def load(node_dict):
        pass


    """
    ### Description ###
    Creates a dict from the XXXNode object (opposite procedure wrt. load)
    This dict, saved in the output deployment descriptor, and serves two purposes:
    1) to provide the deployer some information (e.g., keys used)
    2) to give it as an input of subsequent runs of the application
    Hence, ideally load() and dump() should involve the same attributes

    ### Parameters ###
    self: Node object

    ### Returns ###
    `dict`: description of the object
    """
    @abstractmethod
    def dump(self):
        pass


    """
    ### Description ###
    Coroutine. Deploy a module to the node

    How this is done depends on the architecture, in general the binary of the
    module must be sent to the Event Manager with a special event on the deploy_port

    *NOTE*: this coroutine should check if module has already been deployed
            (doing nothing if this is the case), and set module.deployed to True
            after deployment

    ### Parameters ###
    self: Node object
    module (XXXModule): module object to deploy

    ### Returns ###
    """
    @abstractmethod
    async def deploy(self, module):
        pass


    """
    ### Description ###
    Coroutine. Sets the key of a specific connection

    How this is done depends on the architecture, in general the key and other args
    must be sent to the Event Manager with a special event on the reactive_port

    conn_io indicates which input/output/request/handler is involved in the connection
    encryption indicates which crypto library is used in this connection

    *NOTE*: this coroutine should use module.nonce as part of associated data
            and increment it if everything went well

    ### Parameters ###
    self: Node object
    module (XXXModule): module where the key is being set
    conn_id (int): ID of the connection
    conn_io (ConnectionIO): object of the ConnectionIO class (see connection.py)
    encryption (Encryption): object of the Encryption class (see crypto.py)
    key (bytes): connection key

    ### Returns ###
    """
    @abstractmethod
    async def set_key(self, module, conn_id, conn_io, encryption, key):
        pass


    """
    Default implementation of some functions.
    Override them in the subclasses if you need a different implementation.
    """


    """
    ### Description ###
    Static coroutine. Cleanup operations to do before the application terminates

    ### Parameters ###

    ### Returns ###
    """
    @staticmethod
    async def cleanup():
        pass


    """
    ### Description ###
    Coroutine. Inform the EM of the source module that a new connection has
    been established, so that events can be correctly forwared to the recipient

    ### Parameters ###
    self: Node object
    to_module (XXXModule): destination module
    conn_id (int): ID of the connection

    ### Returns ###
    """
    async def connect(self, to_module, conn_id):
        module_id = await to_module.get_id()

        payload = tools.pack_int16(conn_id)                           + \
                  tools.pack_int16(module_id)                         + \
                  tools.pack_int16(to_module.node.reactive_port)      + \
                  to_module.node.ip_address.packed

        command = CommandMessage(ReactiveCommand.Connect,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Connecting id {} to {}'.format(conn_id, to_module.name))



    """
    ### Description ###
    Coroutine. Call the entry point of a module

    ### Parameters ###
    self: Node object
    to_module (XXXModule): target module
    entry (str): name of the entry point to call
    arg (bytes): argument to pass as a byte array (can be None)

    ### Returns ###
    """
    async def call(self, module, entry, arg=None):
        assert module.node is self

        module_id, entry_id = \
            await asyncio.gather(module.get_id(), module.get_entry_id(entry))

        payload = tools.pack_int16(module_id)       + \
                  tools.pack_int16(entry_id)        + \
                  (b'' if arg is None else arg)

        command = CommandMessage(ReactiveCommand.Call,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        response = await self._send_reactive_command(
                command,
                log='Sending call command to {}:{} ({}:{}) on {}'.format(
                     module.name, entry, module_id, entry_id, self.name)
                )

        if not response.ok():
            logging.error("Received error code {}".format(str(response.code)))
        else:
            logging.info("Response: \"{}\"".format(
                binascii.hexlify(response.message.payload).decode('ascii')))


    """
    ### Description ###
    Coroutine. Trigger the 'output' event of a direct connection

    ### Parameters ###
    self: Node object
    connection (Connection): connection object
    arg (bytes): argument to pass as a byte array (can be None)

    ### Returns ###
    """
    async def output(self, connection, arg=None):
        assert connection.to_module.node is self

        module_id = await connection.to_module.get_id()

        if arg is None:
            data = b''
        else:
            data = arg

        cipher = await connection.encryption.encrypt(connection.key,
                    tools.pack_int16(connection.nonce), data)

        payload = tools.pack_int16(module_id)               + \
                  tools.pack_int16(connection.id)           + \
                  cipher

        command = CommandMessage(ReactiveCommand.RemoteOutput,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Sending handle_output command of connection {}:{} to {} on {}'.format(
                     connection.id, connection.name, connection.to_module.name, self.name)
                )


    """
    ### Description ###
    Coroutine. Trigger the 'request' event of a direct connection

    ### Parameters ###
    self: Node object
    connection (Connection): connection object
    arg (bytes): argument to pass as a byte array (can be None)

    ### Returns ###
    """
    async def request(self, connection, arg=None):
        assert connection.to_module.node is self

        module_id = await connection.to_module.get_id()

        if arg is None:
            data = b''
        else:
            data = arg

        cipher = await connection.encryption.encrypt(connection.key,
                    tools.pack_int16(connection.nonce), data)

        payload = tools.pack_int16(module_id)               + \
                  tools.pack_int16(connection.id)           + \
                  cipher

        command = CommandMessage(ReactiveCommand.RemoteRequest,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        response = await self._send_reactive_command(
                command,
                log='Sending handle_request command of connection {}:{} to {} on {}'.format(
                     connection.id, connection.name, connection.to_module.name, self.name)
                )

        if not response.ok():
            logging.error("Received error code {}".format(str(response.code)))
            return

        resp_encrypted = response.message.payload
        plaintext = await connection.encryption.decrypt(connection.key,
                    tools.pack_int16(connection.nonce + 1), resp_encrypted)

        logging.info("Response: \"{}\"".format(
            binascii.hexlify(plaintext).decode('ascii')))



    """
    ### Description ###
    Coroutine. Register an entry point for periodic tasks

    ### Parameters ###
    self: Node object
    module (XXXModule): target module
    entry (str): entry point to call
    frequency (int): desired frequency of which the entry point will be called

    ### Returns ###
    """
    async def register_entrypoint(self, module, entry, frequency):
        assert module.node is self
        module_id, entry_id = \
            await asyncio.gather(module.get_id(), module.get_entry_id(entry))

        payload = tools.pack_int16(module_id)       + \
                  tools.pack_int16(entry_id)        + \
                  tools.pack_int32(frequency)

        command = CommandMessage(ReactiveCommand.RegisterEntrypoint,
                                Message(payload),
                                self.ip_address,
                                self.reactive_port)

        await self._send_reactive_command(
                command,
                log='Sending RegisterEntrypoint command of {}:{} ({}:{}) on {}'.format(
                     module.name, entry, module_id, entry_id, self.name)
                )


    """
    ### Description ###
    Coroutine. Wrapper to __send_reactive_command (see below)

    ### Parameters ###
    self: Node object
    command (ReactiveCommand): command to send to the node
    log (str): optional text message printed to stdout (can be None)

    ### Returns ###
    """
    async def _send_reactive_command(self, command, log=None):
        if self.__lock is not None:
            async with self.__lock:
                return await self.__send_reactive_command(command, log)
        else:
            return await self.__send_reactive_command(command, log)



    """
    ### Description ###
    Static coroutine. Helper function used to send a ReactiveCommand message to the node

    ReactiveCommand: defined in reactivenet: https://github.com/gianlu33/reactive-net

    ### Parameters ###
    command (ReactiveCommand): command to send to the node
    log (str): optional text message printed to stdout (can be None)

    ### Returns ###
    """
    @staticmethod
    async def __send_reactive_command(command, log):
        if log is not None:
            logging.info(log)

        if command.has_response():
            response =  await command.send_wait()
            if not response.ok():
                raise Error('Reactive command {} failed with code {}'
                                .format(str(command.code), str(response.code)))
            return response

        else:
            await command.send()
            return None
