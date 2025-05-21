import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt


# ——————————————————————————————————————————————
# HID usage map for common keys
# ——————————————————————————————————————————————
KEY_MAP = {
    # letters A–Z → 0x04–0x1d
    **{getattr(Qt, f'Key_{chr(c)}'): 0x04 + (c - ord('A'))
       for c in range(ord('A'), ord('Z')+1)},
    # digits 1–9 → 0x1e–0x26, 0 → 0x27
    **{getattr(Qt, f'Key_{d}'): 0x1e + (int(d)-1) for d in '123456789'},
    Qt.Key_0: 0x27,
    # common control keys
    Qt.Key_Enter:      0x28,
    Qt.Key_Return:     0x28,
    Qt.Key_Escape:     0x29,
    Qt.Key_Backspace:  0x2a,
    Qt.Key_Tab:        0x2b,
    Qt.Key_Space:      0x2c,
}

class KeyCaptureWindow(QMainWindow):
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.setWindowTitle("Keyboard Capture")
        self.setGeometry(200, 200, 400, 100)
        # ensure we get key events
        self.setFocusPolicy(Qt.StrongFocus)


    def keyPressEvent(self, event):
        # build modifier byte
        mod = 0x00
        if event.modifiers() & Qt.ShiftModifier:
            mod |= 0x02        # Left Shift
        if event.modifiers() & Qt.ControlModifier:
            mod |= 0x01        # Left Ctrl
        if event.modifiers() & Qt.AltModifier:
            mod |= 0x04        # Left Alt
        # you can add GUI (Win) or right‐side bits similarly

        hid_code = KEY_MAP.get(event.key())
        if hid_code:
            self.device.send_keyboard_data(mod, hid_code)

    def keyReleaseEvent(self, event):
        # send a “release” so host sees key-up
        self.device.send_keyboard_data(0x00, 0x00)

class Gui(object):
    def launch(device):
        app = QApplication(sys.argv)
        win = KeyCaptureWindow(device)
        win.show()
        sys.exit(app.exec_())
