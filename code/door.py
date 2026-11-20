# -*- coding: utf-8 -*-
"""Lenh cua (servo) va trang thai dong/mo.

Khong mo cong COM o day. Gateway goi format_* roi ghi serial, va dung DoorController
de biet khi nao gui OPEN/CLOSE. P0 la cam bien anh sang, P14 la den RGB, nen servo
khong duoc gan vao hai chan do. Chan mac dinh P4 vi tai lieu servo cua OhStem cam
vao P4; nhom doi bang SERVO_PIN khi chot D4.
"""

# Giu cua mo 10 giay roi tu dong. Trung voi web_mock.DOOR_RELOCK.
DEFAULT_OPEN_SECONDS = 10

# Chan cam duoc servo. P0 va P14 da co viec khac (CLAUDE.md).
_BLOCKED = ("P0", "P14")


def parse_servo_pin(text):
    """Tra ve 'P4'. Sai chan thi ValueError, khong bao gio tra P0 hay P14."""
    name = str(text).strip().upper().replace(" ", "")
    if name.startswith("PIN"):
        name = "P" + name[3:]
    if name.startswith("P"):
        number = name[1:]
    else:
        number = name
        name = "P" + number
    if not number.isdigit():
        raise ValueError("Chan servo khong hop le: " + str(text))
    value = int(number)
    if value < 1 or value > 16:
        raise ValueError("Chan servo phai tu P1 den P16, tru P14")
    name = "P" + str(value)
    if name in _BLOCKED:
        raise ValueError("P0 la cam bien anh sang, P14 la den RGB")
    return name


def format_pin_command(pin):
    return "DOOR:PIN:" + parse_servo_pin(pin)


def format_door_command(action):
    if action not in ("OPEN", "CLOSE"):
        raise ValueError("Lenh cua chi la OPEN hoac CLOSE")
    return "DOOR:" + action


def parse_door_ack(line):
    """Doc dong board tra ve.

    Tra ve ('state', locked), ('error', text), ('pin', 'P4'), hoac None neu khong phai ack cua.
    """
    text = line.strip().upper()
    if text == "DOOR:OPEN":
        return ("state", False)
    if text == "DOOR:CLOSE":
        return ("state", True)
    if text.startswith("DOOR:ERR"):
        return ("error", text)
    if text.startswith("DOOR:PIN:"):
        pin = text.split(":", 2)[-1]
        return ("pin", pin)
    return None


class DoorController:
    """Nho cua dang khoa hay mo, va khi nao phai gui lenh.

    request() khong cham serial. No tra ve:
    - 'OPEN' / 'CLOSE': can ghi lenh, cho board tra loi
    - 'REFRESH': dang mo san, chi keo dai gio tu khoa
    - None: khong lam gi (dang cho ack, hoac da dung trang thai)
    """

    def __init__(self, open_seconds, clock):
        self.open_seconds = open_seconds
        self._clock = clock
        self.locked = True
        self.relock_at = None
        # True/False ma ta dang cho board xac nhan. None neu khong cho.
        self.pending = None
        self.source = ""

    def now(self):
        return self._clock()

    def request(self, locked, source):
        if self.pending is not None:
            return None
        locked = bool(locked)
        if locked == self.locked:
            # Dang mo san: nguoi vua nhan them lan nua thi reset dong ho, khong gui them lenh.
            if not locked and self.relock_at is not None:
                self.relock_at = self.now() + self.open_seconds
                self.source = source
                return "REFRESH"
            return None
        self.pending = locked
        self.source = source
        if locked:
            return "CLOSE"
        return "OPEN"

    def ack(self, locked):
        """Board da lam xong. locked True nghia la cua dong."""
        self.locked = bool(locked)
        self.pending = None
        if self.locked:
            self.relock_at = None
        else:
            self.relock_at = self.now() + self.open_seconds

    def clear_pending(self):
        """Gui lenh that bai hoac board tra DOOR:ERR. Giu nguyen trang thai da xac nhan."""
        self.pending = None

    def tick(self):
        """Goi thuong xuyen. Het gio mo thi tra ve 'CLOSE'."""
        if self.pending is not None or self.locked or self.relock_at is None:
            return None
        if self.now() < self.relock_at:
            return None
        return self.request(True, "Tự khóa")

    def view(self):
        now = self.now()
        relock_in = None
        if not self.locked and self.relock_at is not None:
            relock_in = max(0, round(self.relock_at - now, 1))
        return {
            "device": "door",
            "locked": self.locked,
            "relock_in": relock_in,
            "at": now,
            "source": self.source,
        }
