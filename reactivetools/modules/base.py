from abc import ABC, abstractmethod

class Module(ABC):
    def __init__(self, name, node, priority, deployed):
        self.name = name
        self.node = node
        self.priority = priority
        self.deployed = deployed
        self.connections = 0

    @abstractmethod
    async def build(self):
        pass

    @abstractmethod
    async def deploy(self):
        pass

    @abstractmethod
    async def call(self, entry, arg=None):
        pass

    @abstractmethod
    async def get_id(self):
        pass

    @abstractmethod
    async def get_input_id(self, input):
        pass

    @abstractmethod
    async def get_output_id(self, output):
        pass

    @abstractmethod
    async def get_entry_id(self, entry):
        pass

    @abstractmethod
    async def get_request_id(self, request):
        pass

    @abstractmethod
    async def get_handler_id(self, handler):
        pass

    @abstractmethod
    async def get_key(self):
        pass

    @abstractmethod
    def get_supported_node_type():
        pass

    @abstractmethod
    def get_supported_encryption():
        pass
