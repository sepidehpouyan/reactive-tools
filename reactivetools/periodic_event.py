import asyncio
import logging

class PeriodicEvent:
    def __init__(self, module, entry, frequency, established):
        self.module = module
        self.entry = entry
        self.frequency = frequency
        self.established = established


    @staticmethod
    def load(events_dict, config):
        module = config.get_module(events_dict['module'])
        entry = events_dict['entry']
        frequency = events_dict['frequency']
        established = events_dict.get('established')

        return PeriodicEvent(module, entry, frequency, established)


    def dump(self):
        return {
            "module": self.module.name,
            "entry": self.entry,
            "frequency": self.frequency,
            "established": self.established
            }


    async def register(self):
        if self.established:
            return

        node = self.module.node

        await node.register_entrypoint(self.module, self.entry, self.frequency)

        logging.info('Registered %s:%s on %s every %d ms',
                     self.module.name, self.entry, node.name, self.frequency)

        self.established = True
