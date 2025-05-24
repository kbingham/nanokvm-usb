#!/usr/bin/env python3

import logging
import serial
import threading

from enum import IntEnum
from typing import List

from gui import Gui


"""
See:
 - https://github.com/sipeed/NanoKVM-USB/blob/main/desktop/src/main/device/serial-port.ts
 - https://github.com/sipeed/NanoKVM-USB/blob/main/desktop/src/main/device/proto.ts
"""


def get_bit(value: int, bit: int) -> int:
    """Return the bit (0 or 1) at position `bit` in `value`."""
    return (value >> bit) & 1

# ----------------------------------------------------------------------
# helpers for byte conversions
# ----------------------------------------------------------------------
def int_to_byte(value: int) -> int:
    """Clamp an integer into a single byte."""
    return value & 0xFF

def int_to_little_endian_list(value: int, length: int = 2) -> List[int]:
    """Return a list of `length` bytes, little‐endian, representing `value`."""
    return [(value >> (8 * i)) & 0xFF for i in range(length)]

class CmdEvent(IntEnum):
    GET_INFO = 0x01
    SEND_KB_GENERAL_DATA = 0x02
    SEND_KB_MEDIA_DATA = 0x03
    SEND_MS_ABS_DATA = 0x04
    SEND_MS_REL_DATA = 0x05
    SEND_MY_HID_DATA = 0x06
    READ_MY_HID_DATA = 0x87
    GET_PARA_CFG = 0x08
    SET_PARA_CFG = 0x09
    GET_USB_STRING = 0x0A
    SET_USB_STRING = 0x0B
    SET_DEFAULT_CFG = 0x0C
    RESET = 0x0F



class CmdPacket:
    HEAD1 = 0x57
    HEAD2 = 0xAB

    def __init__(self, addr: int = 0x00, cmd: int = 0x00, data: List[int] = None):
        self.ADDR = 0x00
        self.CMD = 0x00
        self.LEN = 0x00
        self.DATA: List[int] = []
        self.SUM = 0x00

        if data is None:
            data = []

        # if negative addr or cmd, treat `data` as a raw packet to decode
        if addr < 0 or cmd < 0:
            self.decode(data)
        else:
            self._save(addr, cmd, data)

    def encode(self) -> List[int]:
        """Build the byte packet."""
        return [self.HEAD1, self.HEAD2, self.ADDR, self.CMD, self.LEN, *self.DATA, self.SUM]

    def decode(self, raw: List[int]) -> int:
        """Parse a raw byte stream into fields. Returns 0 on success, -1 on failure."""
        hi = self._find_head(raw)
        if hi < 0:
            print("cannot find HEAD")
            return -1

        if len(raw) - hi < 6:
            print("len error1")
            return -1

        addr = raw[hi + 2]
        cmd = raw[hi + 3]
        data_len = raw[hi + 4]

        if len(raw) < hi + 5 + data_len + 1:
            print("len error2")
            return -1

        try:
            summ = raw[hi + 5 + data_len]
        except IndexError:
            print("len error3")
            return -1

        s = sum(raw[hi : hi + 5 + data_len])
        if (s & 0xFF) != summ:
            # checksum mismatch
            return -1

        # all good—assign to self
        self.ADDR = addr
        self.CMD = cmd
        self.LEN = data_len
        self.DATA = raw[hi + 5 : hi + 5 + data_len]
        self.SUM = summ
        return 0

    def _find_head(self, lst: List[int]) -> int:
        """Find the index of the [HEAD1, HEAD2] sequence in `lst`."""
        seq = [self.HEAD1, self.HEAD2]
        for i in range(len(lst) - 1):
            if lst[i] == seq[0] and lst[i + 1] == seq[1]:
                return i
        return -1

    def _save(self, addr: int, cmd: int, data: List[int]) -> None:
        """Prepare fields and compute checksum."""
        self.ADDR = addr
        self.CMD = cmd
        self.DATA = data.copy()
        self.LEN = len(data)

        total = self.HEAD1 + self.HEAD2 + self.ADDR + self.CMD + self.LEN + sum(self.DATA)
        self.SUM = total & 0xFF



class InfoPacket:
    def __init__(self, data: List[int]):
        if data[0] < 0x30:
            raise ValueError("version error")

        version_e = data[0] - 0x30
        version = 1.0 + version_e / 10.0
        self.CHIP_VERSION = f"V{version:.1f}"

        self.IS_CONNECTED = bool(data[1])
        self.NUM_LOCK = get_bit(data[2], 0) == 1
        self.CAPS_LOCK = get_bit(data[2], 1) == 1
        self.SCROLL_LOCK = get_bit(data[2], 2) == 1

    def __str__(self) -> str:
        return (
            f"InfoPacket(\n"
            f"  CHIP_VERSION: {self.CHIP_VERSION}\n"
            f"  IS_CONNECTED: {self.IS_CONNECTED}\n"
            f"  NUM_LOCK:     {self.NUM_LOCK}\n"
            f"  CAPS_LOCK:    {self.CAPS_LOCK}\n"
            f"  SCROLL_LOCK:  {self.SCROLL_LOCK}\n"
            f")"
        )

    __repr__ = __str__



class NanoKVM(object):
    def __init__(self, serial_instance, addr=0x00, debug=False):
        self.serial_port = serial_instance
        self.addr = addr
        self._write_lock = threading.Lock()

    def get_info(self) -> "InfoPacket":
        pkt = CmdPacket(self.addr, CmdEvent.GET_INFO).encode()
        self.serial_port.write(bytes(pkt))
        raw = self.serial_port.read(14)
        print("RAW INFO RESPONSE:", [hex(b) for b in raw])
        ret = CmdPacket(-1, -1, list(raw)).decode(list(raw))
        print("decode() returned", ret)

        rsp = CmdPacket(-1, -1, list(raw))
        return InfoPacket(rsp.DATA)

    def send_hid_report(self, data) -> None:
        #print("HID REPORT DATA: ", [hex(b) for b in data])
        pkt = CmdPacket(self.addr, CmdEvent.SEND_KB_GENERAL_DATA, data[:8]).encode()
        self.serial_port.write(bytes(pkt))

    def send_keyboard_data(self, modifier: int, key: int) -> None:
        data = [modifier, 0x00, 0x00, 0x00, key, 0x00, 0x00, 0x00]
        self.send_hid_report(data)

    def send_mouse_relative_data(self, key: int, x: int, y: int, scroll: int) -> None:
        x_b = int_to_byte(x)
        y_b = int_to_byte(y)
        data = [0x01, key, x_b, y_b, scroll]
        pkt = CmdPacket(self.addr, CmdEvent.SEND_MS_REL_DATA, data).encode()
        self.serial_port.write(bytes(pkt))

    def send_mouse_absolute_data(
        self, key: int, width: int, height: int, x: int, y: int, scroll: int
    ) -> None:
        x_abs = 0 if width == 0 else (x * 4096) // width
        y_abs = 0 if height == 0 else (y * 4096) // height
        x_le = int_to_little_endian_list(x_abs)
        y_le = int_to_little_endian_list(y_abs)
        data = [0x02, key, *x_le, *y_le, scroll]
        pkt = CmdPacket(self.addr, CmdEvent.SEND_MS_ABS_DATA, data).encode()
        self.serial_port.write(bytes(pkt))



if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Sipeed Nano-KVM USB",
        epilog="""\
This is a work in progress.
        """)

    parser.add_argument('serial')

    parser.add_argument(
        '-v', '--verbose',
        dest='verbosity',
        action='count',
        help='print more diagnostic messages (option can be given multiple times)',
        default=0)

    args = parser.parse_args()

    if args.verbosity > 3:
        args.verbosity = 3
    level = (logging.WARNING,
             logging.INFO,
             logging.DEBUG,
             logging.NOTSET)[args.verbosity]
    logging.basicConfig(level=logging.INFO)
    #~ logging.getLogger('root').setLevel(logging.INFO)
    logging.getLogger('rfc2217').setLevel(level)


    # connect to serial port
    # ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True)
    ser = serial.Serial()
    ser.port = args.serial
    ser.baudrate = 57600
    ser.timeout = 3     # required so that the reader thread can exit

    # reset control line as no _remote_ "terminal" has been connected yet
    ser.dtr = False
    ser.rts = False

    try:
        ser.open()
    except serial.SerialException as e:
        logging.error("Could not open serial port {}: {}".format(ser.name, e))
        sys.exit(1)


    logging.info("Serving serial port: {}".format(ser.name))
    settings = ser.get_settings()

    nano = NanoKVM(ser)

    print(nano.get_info())

    Gui.launch(nano)

    # Restore previous settings if we can
    ser.apply_settings(settings)
