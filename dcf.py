"""

   DCF - Is a moodule to format raw bytes as DCF packet, DCF packets can
   be loaded into wireshark to decode the data. 

   Copyright (c) 2022, al303576 (al303576@hotmail.com)

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
class DcfPacket(object):
    def __init__(self,sequence_number=None, channel=None,
                timestamp=None, length=None, data=None, lqi=None,
                fcs=None, power_dbm=None, channel_seq_number=None,
                duplicated_packet=0, timestamp_sync=1,
                capture_device_id=0x7fff):
        """
        sequence_number: The sequence number of the packet.
        channel: The channel the packet was received on.
        timestamp: The timestamp of the packet in uSeconds. 
        length: The length of the packet.
        data: byteArray the raw data of the packet
        lqi: The LQI of the packet.
        fcs: The FCS of the packet.
        power_dbm: The power of the packet.
        channel_seq_number: The channel sequence number of the packet.
        duplicated_packet: The duplicated packet flag of the packet.
        timestamp_sync: The timestamp sync flag of the packet.
        capture_device_id: The capture device id of the packet.
        """
        
        self.sequence_number = sequence_number

        seconds = timestamp / 1e6
        # timestamp needs to be forced to have only 6 digits in its float part, 
        # otherwise some decoders will not be able to decode the packet.
        # i.e 53.580159244 -> 53.580159
        self.timestamp = f'{seconds:.6f}'
        self.length = length

        #convert the byteArray to a hes string
        self.data = bytearray(data).hex()

        self.lqi = lqi
        self.fcs =  fcs
        self.power_dbm = power_dbm
        self.channel = channel
        self.channel_seq_number = self.sequence_number
        self.duplicated_packet = duplicated_packet
        self.timestamp_sync = timestamp_sync
        self.capture_device_id = capture_device_id

    def __repr__(self):
        """
        Returns a string representation of the DCF object in a single line.
        i.e 
        1 53.580159 50 4188BAFECAFFFFB8E10912FCFFB8E10167279064FEFF570B002862E10200279064FEFF570B0000514251E02B0C2602D722EB 107 1 -39 11 1 0 1 32767
        """
        dcf_entry = (f"{self.sequence_number} "
                     f"{self.timestamp} "
                     f"{self.length} "
                     f"{self.data} "
                     f"{self.lqi} "
                     f"{self.fcs} "
                     f"{self.power_dbm} "
                     f"{self.channel} " 
                     f"{self.channel_seq_number} "
                     f"{self.duplicated_packet} "
                     f"{self.timestamp_sync} "
                     f"{self.capture_device_id}")

        return dcf_entry.upper()
    
    @staticmethod
    def dcf_header():
        """
        Returns a string representation of the DCF header.
        Centralized and Distributed defaults TC link keys are added by default
        """
        dcf_header =["#Format=4",
                    "# SNA v2.2.0.4 SUS:20090709 ACT:819705",
                    '#SEC_KEY:panid=-1 type=2 seqnum=-1 device1="................" device2="................" key="5A6967426565416C6C69616E63653039"',
                    '#SEC_KEY:panid=-1 type=2 seqnum=-1 device1="................" device2="................" key="D0D1D2D3D4D5D6D7D8D9DADBDCDDDEDF"']
        return '\n'.join(dcf_header)


