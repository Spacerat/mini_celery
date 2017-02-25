""" This file just sets up the 'app'. It is imported both by the distributed clients, and by anything which wants to add tasks to the system """
from orchestrator import Client, JSONTransport, RedisBroker

transport = JSONTransport()
broker = RedisBroker(transport)
app = Client(broker)
