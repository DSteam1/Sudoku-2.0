#!/usr/bin/env python
import socket
import struct
from threading import Thread
import json
from Tkinter import END, TclError
from utils import init_logging

LOG = init_logging()

MC_GROUP = '224.3.29.71'
MC_PORT = 50000


class AnnounceListener(Thread):

    def __init__(self, servers_lb, server_list):
        Thread.__init__(self)
        self.server_list = server_list  # Shared object between main thread an current thread
        self.servers_lb = servers_lb  # Servers listbox

    def run(self):

        # Create the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to the server address
        sock.bind(('', MC_PORT))

        # Tell the OS to add this socket to the multicast group
        # on all interfaces.
        group = socket.inet_aton(MC_GROUP)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        print('\nWaiting for announce messages')

        # Receive/respond loop
        while True:
            data, address = sock.recvfrom(1024)

            #print('%d received %s bytes from %s' % (time.time(), len(data), address))
            #print(data)

            try:
                rec_dict = json.loads(data)
                server = (rec_dict['exchange'], rec_dict['host'], rec_dict['port'])
                if server not in self.server_list:
                    self.server_list.append(server)  # Add server to list
                    self.servers_lb.insert(END, server[0])  # Insert new server to listbox
            except ValueError, e:
                LOG.error(e)
            except KeyError, e:
                LOG.error("No index: " + str(e))
            except TclError, e:
                pass
