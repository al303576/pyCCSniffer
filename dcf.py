from packet_handler import PacketHandler
class DcfPacket(object):

    def __init__(self,SniffedPacket=None,stats=None):
        
        self.sequence_number = stats['Captured']
        seconds = SniffedPacket.timestampUsec / 1e6
        self.timestamp = f'{seconds:.6f}'
        self.length = SniffedPacket.len
        self.data = bytearray(SniffedPacket._SniffedPacket__macPDUByteArray).hex()
        rssi, corr, crc_ok = PacketHandler.checkPacket(SniffedPacket._SniffedPacket__macPDUByteArray)
        self.lqi = corr
        self.fcs =  1 if crc_ok else 0
        self.power_dbm = rssi
        self.channel = stats['Channel']
        self.channel_seq_number = self.sequence_number
        self.duplicated_packet = 0
        self.timestamp_sync = 1
        self.capture_device_id = 0x7fff

        

    def __repr__(self):

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

