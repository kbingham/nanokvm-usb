import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt


# ——————————————————————————————————————————————
# HID usage map for common keys
# ——————————————————————————————————————————————
# Todo: Refactor this to map each of /usr/include/qt5/QtCore/qnamespace.h
# entries to a suitable HID value
qt_to_hid_int_map = {
    Qt.Key_A: 0x04, Qt.Key_B: 0x05, Qt.Key_C: 0x06, Qt.Key_D: 0x07,
    Qt.Key_E: 0x08, Qt.Key_F: 0x09, Qt.Key_G: 0x0A, Qt.Key_H: 0x0B,
    Qt.Key_I: 0x0C, Qt.Key_J: 0x0D, Qt.Key_K: 0x0E, Qt.Key_L: 0x0F,
    Qt.Key_M: 0x10, Qt.Key_N: 0x11, Qt.Key_O: 0x12, Qt.Key_P: 0x13,
    Qt.Key_Q: 0x14, Qt.Key_R: 0x15, Qt.Key_S: 0x16, Qt.Key_T: 0x17,
    Qt.Key_U: 0x18, Qt.Key_V: 0x19, Qt.Key_W: 0x1A, Qt.Key_X: 0x1B,
    Qt.Key_Y: 0x1C, Qt.Key_Z: 0x1D,

    Qt.Key_1: 0x1E, Qt.Key_2: 0x1F, Qt.Key_3: 0x20, Qt.Key_4: 0x21,
    Qt.Key_5: 0x22, Qt.Key_6: 0x23, Qt.Key_7: 0x24, Qt.Key_8: 0x25,
    Qt.Key_9: 0x26, Qt.Key_0: 0x27,

    Qt.Key_Return: 0x28, Qt.Key_Enter: 0x28, Qt.Key_Escape: 0x29,
    Qt.Key_Backspace: 0x2A, Qt.Key_Tab: 0x2B, Qt.Key_Space: 0x2C,
    Qt.Key_Minus: 0x2D, Qt.Key_Equal: 0x2E, Qt.Key_BracketLeft: 0x2F,
    Qt.Key_BracketRight: 0x30, Qt.Key_Backslash: 0x31,
    Qt.Key_Semicolon: 0x33, Qt.Key_Apostrophe: 0x34,
    Qt.Key_QuoteLeft: 0x35, Qt.Key_Comma: 0x36, Qt.Key_Period: 0x37,
    Qt.Key_Slash: 0x38,

    Qt.Key_Shift: 0xE1, Qt.Key_Control: 0xE0,
    Qt.Key_Alt: 0xE2, Qt.Key_Meta: 0xE3,
    Qt.Key_Left: 0x50, Qt.Key_Right: 0x4F,
    Qt.Key_Up: 0x52, Qt.Key_Down: 0x51,

    Qt.Key_F1: 0x3A, Qt.Key_F2: 0x3B, Qt.Key_F3: 0x3C, Qt.Key_F4: 0x3D,
    Qt.Key_F5: 0x3E, Qt.Key_F6: 0x3F, Qt.Key_F7: 0x40, Qt.Key_F8: 0x41,
    Qt.Key_F9: 0x42, Qt.Key_F10: 0x43, Qt.Key_F11: 0x44, Qt.Key_F12: 0x45,

    Qt.Key_NumLock: 0x53, Qt.Key_Slash: 0x54,
    Qt.Key_Asterisk: 0x55, Qt.Key_Minus: 0x56,
}


# Build reverse lookup of all Qt.Key_* attributes
qt_key_name_map = {
    getattr(Qt, name): name
    for name in dir(Qt)
    if name.startswith("Key_")
}

def qt_key_code_to_name(key_code):
    return qt_key_name_map.get(key_code, f"UnknownKey({key_code})")

class KeyCaptureWindow(QMainWindow):
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.setWindowTitle("Keyboard Capture")
        self.setGeometry(200, 200, 400, 100)
        # ensure we get key events
        self.setFocusPolicy(Qt.StrongFocus)


    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return

        # build modifier byte
        mod = 0x00
        if event.modifiers() & Qt.ShiftModifier:
            mod |= 0x02        # Left Shift
        if event.modifiers() & Qt.ControlModifier:
            mod |= 0x01        # Left Ctrl
        if event.modifiers() & Qt.AltModifier:
            mod |= 0x04        # Left Alt
        # you can add GUI (Win) or right‐side bits similarly

        key = event.key()
        hid_code = qt_to_hid_int_map.get(key)
        name = qt_key_code_to_name(key)

        if hid_code:
            print(f"Sending key {name} as {hid_code}")
            self.device.send_keyboard_data(mod, hid_code)
        else:
            key = event.key()
            name = qt_key_code_to_name(key)
            print(f"Unhandled key event : {key} {name}")

    def keyReleaseEvent(self, event):
        # send a “release” so host sees key-up
        self.device.send_keyboard_data(0x00, 0x00)

class Gui(object):
    def launch(device):
        app = QApplication(sys.argv)
        win = KeyCaptureWindow(device)
        win.show()
        sys.exit(app.exec_())
