"""copyright (c) 2022, al303576 (al303576@hotmail.com)
    part of this code was inspired by the work done by Andrew Dodd (andrew.john.dodd@gmail.com)"""

import errno
from tkinter.tix import Tree
import usb.core
import usb.util
import time
import cc253xemk

VENDOR_PRODUCTS = [cc253xemk.CC2531_USB_DESCRIPTOR,
                   cc253xemk.CC2530_USB_DESCRIPTOR]


class CC253xEmkMULTI(cc253xemk.CC253xEMK):

    def __init__(self, device=None, handler=None, channel=11, auto_init=False):
        super().__init__(handler, channel, auto_init)

        self.dev = device
        self.name = usb.util.get_string(self.dev, self.dev.iProduct)
        self.free = True

        self.initialise()

    def __repr__(self):
        if self.dev:
            return f'{self.name}, bcdDevice: 0x{self.dev.bcdDevice:04x},  Channel: {self.channel}'
        else:
            return 'No device connected'
    
    def initialise(self):
        if self.dev is None:
            raise IOError("Device not found")

        # must call this to establish the USB's "Config"
        self.dev.set_configuration()

        # get identity from Firmware command
        self.ident = self.dev.ctrl_transfer(cc253xemk.CC253xEMK.DIR_IN,
                                            cc253xemk.CC253xEMK.GET_IDENT, 0, 0, 256)

        # power on radio, wIndex = 4
        self.dev.ctrl_transfer(cc253xemk.CC253xEMK.DIR_OUT,
                               cc253xemk.CC253xEMK.SET_POWER,
                               wIndex=4)

        while True:
            # check if powered up
            power_status = self.dev.ctrl_transfer(cc253xemk.CC253xEMK.DIR_IN,
                                                  cc253xemk.CC253xEMK.GET_POWER, 0, 0, 1)
            if power_status[0] == 4: break
            time.sleep(0.1)

        self.set_channel(self.channel)



def _collect_cc253x_devices():
    """Collect all CC253x devices on the system
    """

    ti_devices = []

    try:
        for vp in VENDOR_PRODUCTS:
            usb_devices = usb.core.find(find_all=True, idVendor=vp.idVendor,
                                        idProduct=vp.idProduct)

            for usb_device in usb_devices:
                ti_device = CC253xEmkMULTI(device=usb_device)
                ti_device.vendor_product = vp
                ti_devices.append(ti_device)

        return ti_devices

    except usb.core.USBError:
        raise OSError(
            "Permission denied, you need to add an udev rule for this device",
            errno=errno.EACCES)


class SingleTonCC253XX(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SingleTonCC253XX, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def getInstance(self):
        return self._instance

    def __init__(self):
        """Creates the object and collect all CC253xEMK 
        devices on the current USB bus."""

        self.name = "CC253XX"
        self.version = "0.1"
        self.devices = _collect_cc253x_devices()

    def get_one_sniffer(self):
        """Get one free sniffer device from the list of devices."""

        for device in self.devices:
            if device.free:
                device.free = False
                return device

    def release_sniffer(self, device):
        """Release a sniffer device from the list of devices."""
        device.free = True
