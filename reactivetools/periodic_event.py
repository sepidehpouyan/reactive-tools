from collections import namedtuple
import asyncio
import logging

class PeriodicEvent(namedtuple('PeriodicEvent', ['module', 'entry', 'frequency'])):
    async def register(self):
        node = self.module.node

        await node.register_entrypoint(self.module, self.entry, self.frequency)

        logging.info('Registered %s:%s on %s every %d ms',
                     self.module.name, self.entry, node.name, self.frequency)
