#!/usr/bin/env python
"""

   pyCCSniffer - a python module to connect to the CC2531emk USB dongle, decode
                 the received frames and provide a quick way to get to your
                 bytes!

   Copyright (c) 2014, Andrew Dodd (andrew.john.dodd@gmail.com)

   This is takes the best parts of two existing sniffers:
   1. ccsniffer - Copyright (c) 2012, George Oikonomou (oikonomou@users.sf.net)
   2. sensniffer - Copyright (C) 2012 Christian Panton <christian@panton.org>

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software Foundation,
   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
"""

import argparse
import logging
import sys
from binascii import hexlify
from builtins import input
from datetime import datetime
from io import StringIO

from cc253xemk import CC253xEMK
from packet_handler import PacketHandler, SniffedPacket
from dcf import DcfPacket
"""
   Functionality
   -------------
   Read IEEE802.15.4 frames from the default CC2531 EMK sniffer firmware, 
   decode them and store them in memory (and maybe print(them yeah)!).

   In interactive mode, the user can also input commands from stdin.
"""

__version__ = '0.0.1'

defaults = {
    'debug_level': 'WARNING',
    'log_level': 'INFO',
    'log_file': 'pyCCSniffer.log',
    'channel': 11,
}

logger = logging.getLogger(__name__)


class DefaultHandler:
    def __init__(self, handlers=None, stats=None):
        self.stats = {} if stats is None else stats
        self.stats['Captured'] = 0
        self.stats['Non-Frame'] = 0
        
        # Centralized and Distributed defaults TC keys added by default
        self.stats['DCF-Packets'] = [
            "#Format=4",
            "# SNA v2.2.0.4 SUS:20090709 ACT:819705",
            '#SEC_KEY:panid=-1 type=2 seqnum=-1 device1="................" device2="................" key="5A6967426565416C6C69616E63653039"',
            '#SEC_KEY:panid=-1 type=2 seqnum=-1 device1="................" device2="................" key="D0D1D2D3D4D5D6D7D8D9DADBDCDDDEDF"'
            ]
        
        self.last_timestamp = -1
        self.start_seconds = (datetime.now() -
                              datetime(1970, 1, 1)).total_seconds()
        self.times_wrapped = 0
        self.__handlers = handlers or []
        self.last_heartbeat_time = None

    def received_valid_frame(self, timestamp, mac_pdu):
        """ Dispatches any received packets to all registered handlers

        Args:
            timestamp: The timestamp the packet was received, as reported by 
                    the sniffer device, in microseconds.
            macPDU: The 802.15.4 MAC-layer PDU, starting with the Frame Control 
                    Field (FCF).
        """
        if len(mac_pdu) > 0:
            if timestamp < self.last_timestamp:
                self.times_wrapped += 1
                logger.warning(f"Timestamp wrapped - {self.times_wrapped}")

            self.last_timestamp = timestamp
            synced_timestamp = self.start_seconds + ( (self.times_wrapped << 32) | timestamp )
            
            self.stats['Captured'] += 1
            packet = SniffedPacket(mac_pdu, synced_timestamp)

            # Add the raw packet to the DCF packet list, this list will be written to a dcf file
            dcf_packet = DcfPacket(packet, self.stats)
            self.stats['DCF-Packets'].append(str(dcf_packet))

            for handler in self.__handlers:
                handler.handleSniffedPacket(packet)

    def received_invalid_frame(self, timestamp, frame_len, frame):
        logger.warning(
            f"Received a frame with incorrect length, pkgLen:{frame_len}, len(frame):{len(frame)}"
        )
        self.stats['Non-Frame'] += 1

    def received_heartbeat_frame(self, counter):
        current_time = datetime.now()
        delta = current_time - self.last_heartbeat_time if self.last_heartbeat_time else ""
        logger.warning(f"HEARTBEAT - {counter} - {delta}")
        self.last_heartbeat_time = current_time

    def received_unknown_command(self, cmd, payload_len, payload):
        logger.warning(
            f"UNKNOWN - CMD[{cmd:02x}] Len[{payload_len}] Bytes[{payload}]")

    def received_invalid_command(self, cmd, payload_len, payload):
        logger.warning(
            f"INVALID - CMD[{cmd:02x}] Len[{payload_len}] Bytes[{payload}]")


def arg_parser():
    
    debug_choices = ('DEBUG', 'INFO', 'WARNING', 'ERROR')

    parser = argparse.ArgumentParser(add_help=False,
                                     description='Read IEEE802.15.4 frames \
    from a CC2531EMK packet sniffer device, parse them and dispay them in text.'
                                     )

    in_group = parser.add_argument_group('Input Options')
    
    in_group.add_argument(
        '-c',
        '--channel',
        type=int,
        action='store',
        choices=list(range(11, 27)),
        default=defaults['channel'],
        help=
        f"Set the sniffer's CHANNEL. Valid range: 11-26. (Default: {defaults['channel']}",
    )

    in_group.add_argument(
        '-a',
        '--annotation',
        type=str,
        help='Include a free-form annotation on every capture.')

    log_group = parser.add_argument_group('Verbosity and Logging')
    
    log_group.add_argument(
        '-r',
        '--rude',
        action='store_true',
        default=False,
        help=
        'Run in non-interactive mode, without accepting user input. (Default Disabled)'
    )
    
    log_group.add_argument(
        '-D',
        '--debug-level',
        action='store',
        choices=debug_choices,
        default=defaults['debug_level'],
        help=
        f"Print messages of severity DEBUG_LEVEL or higher (Default {defaults['debug_level']}",
    )
    
    log_group.add_argument('-L',
                           '--log-file',
                           action='store',
                           nargs='?',
                           const=defaults['log_file'],
                           default=False,
                           help=f"""Log output in LOG_FILE. If -L is specified 
                                   but LOG_FILE is omitted, {defaults['log_file']} will be used.
                                   If the argument is omitted altogether,
                                   logging will not take place at all.""")
    log_group.add_argument('-l',
                           '--log-level',
                           action='store',
                           choices=debug_choices,
                           default=defaults['log_level'],
                           help=f"""Log messages of severity LOG_LEVEL or 
                                   higher. Only makes sense if -L is also 
                                   specified (Default {defaults['log_level']})"""
                           )

    gen_group = parser.add_argument_group('General Options')
    
    gen_group.add_argument('-v',
                           '--version',
                           action='version',
                           version=f'pyCCSniffer v{__version__}')
    
    gen_group.add_argument('-h',
                           '--help',
                           action='help',
                           help='Shows this message and exits')

    return parser.parse_args()


def dump_stats(stats):
    s = StringIO()

    s.write('Frame Stats:\n')
    for name, count in list(stats.items()):
        if name == "DCF-Packets": 
            continue
        s.write(f'{name:20s}: {count}\n')

    print(s.getvalue())

    with open("dcf_file_created.dcf", 'w') as file_handler:
        for item in stats['DCF-Packets']:
            file_handler.write("{}\n".format(item))


def log_init():
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, args.debug_level))
    cf = logging.Formatter('%(message)s')
    ch.setFormatter(cf)
    logger.addHandler(ch)

    if args.log_file:
        fh = logging.handlers.RotatingFileHandler(filename=args.log_file,
                                                  maxBytes=5000000)
        fh.setLevel(getattr(logging, args.log_level))
        ff = logging.Formatter('%(asctime)s - %(levelname)8s - %(message)s')
        fh.setFormatter(ff)
        logger.addHandler(fh)


if __name__ == '__main__':
    args = arg_parser()
    log_init()

    logger.info('Started logging')

    dcf_packets = []
    stats = {}
    packetHandler = PacketHandler(stats)
    packetHandler.enable()

    if args.annotation:
        packetHandler.setAnnotation(args.annotation)

    stats['Channel'] = args.channel

    # Create a list of handlers to dispatch to, NB: handlers must have a "handleSniffedPacket" method
    handler = DefaultHandler([packetHandler], stats=stats)

    snifferDev = CC253xEMK(handler, args.channel)

    def printHelp():
        h = StringIO()
        deviceStr = str(snifferDev)
        h.write(deviceStr + '\n')
        h.write('-' * len(deviceStr) + '\n')
        h.write('Commands:\n')
        h.write('c: Print current RF Channel\n')
        h.write('h,?: Print this message\n')
        h.write('[11,26]: Change RF channel\n')
        h.write('s: Start/stop the packet capture\n')
        h.write('d: Toggle frame dissector\n')
        h.write('a*: Set an annotation (write "a" to remove it)\n')
        h.write('p: Print all capture packets\n')
        h.write('q: Quit the program and creates a dcf with the captured packets\n')
        h = h.getvalue()
        print(h)

    if args.rude == False:
        printHelp()

    try:
        while 1:
            if args.rude:
                if not snifferDev.isRunning():
                    snifferDev.start()
            else:
                try:
                    # use the Windows friendly "raw_input()", instead of select()
                    cmd = input('')

                    if '' != cmd:
                        logger.debug(f'User input: "{cmd}"')
                        if cmd in ('h', '?'):
                            printHelp()
                        elif cmd == 'c':
                            # We'll only ever see this if the user asked for it, so we are
                            # running interactive. Print away
                            print(
                                f'Sniffing in channel: {snifferDev.get_channel()}'
                            )
                        elif cmd == 'd':
                            if packetHandler.isEnabled():
                                packetHandler.disable()
                                print("Dissector disabled")
                            else:
                                packetHandler.enable()
                                print("Dissector enabled")
                        elif cmd == 'p':
                            logger.info('User requested print all')
                            packetHandler.printAllFrames()

                        elif cmd == 'q':
                            logger.info('User requested shutdown')
                            sys.exit(0)
                        elif cmd == 's':
                            if snifferDev.isRunning():
                                snifferDev.stop()
                                print("Stopped")
                            else:
                                snifferDev.start()
                                print("Started")
                        elif 'a' == cmd[0]:
                            if 1 == len(cmd):
                                packetHandler.setAnnotation('')
                            else:
                                packetHandler.setAnnotation(cmd[1:].strip())
                        elif int(cmd) in range(11, 27):
                            snifferDev.set_channel(int(cmd))
                            stats['Channel'] = cmd
                            print(
                                f'Sniffing in channel: {snifferDev.get_channel()}'
                            )
                        else:
                            print("Channel must be from 11 to 26 inclusive.")
                except ValueError:
                    print('Unknown Command. Type h or ? for help')

    except (KeyboardInterrupt, SystemExit):
        logger.warning('Shutting down')
        if snifferDev.isRunning():
            snifferDev.stop()
        dump_stats(packetHandler.stats)
        sys.exit(0)
