#!/usr/bin/env python
import socket
import struct
import sys
import time
import json
from threading import Thread
from utils import init_logging

LOG = init_logging()

MC_GROUP = '224.3.29.71'
MC_PORT = 50000
INTERVAL = 5  # Interval in seconds of announce messages


class Announcer(Thread):

    def __init__(self, host, port, exchange):
        Thread.__init__(self)
        self.host = host
        self.port = port
        self.exchange = exchange

    def run(self):

        multicast_group = (MC_GROUP, MC_PORT)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the TTL to 1 so the messages wouldn't  go past the local network segment.
        ttl = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        # Announce message in JSON format
        message = json.dumps({'host': self.host, 'port': self.port, 'exchange': self.exchange})

        try:
            while True:
                # Send data to the multicast group
                #LOG.info('Announcing server info: "%s"' % message)
                sock.sendto(message, multicast_group)
                time.sleep(INTERVAL)
        finally:
            print >> sys.stderr, 'Closing socket'
            sock.close()


