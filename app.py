"""Squeeze: drag a file in Explorer, press Shift, drop it on a wedge to compress it.
Runs in the system tray. Windows only (the trigger uses user32); the menu itself is plain Qt."""
import math, os, subprocess, sys

from PySide6.QtCore import QFileInfo, QObject, QPointF, QRectF, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QIcon, QImageReader,
                           QLinearGradient, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QFileIconProvider, QLabel, QMenu, QSystemTrayIcon, QWidget

import engine

# ---- menu layout -----------------------------------------------------------
# (title, mode, [(label, hint, value)], default option index)
KB = 1024
CATS = [
    ("Quality", "quality", [("Low", "smallest", 40), ("Medium", "balanced", 65), ("High", "best look", 85)], 1),
    ("Size", "size", [("100 KB", "", 100 * KB), ("500 KB", "", 500 * KB), ("1 MB", "", 1024 * KB), ("2 MB", "", 2048 * KB)], 2),
    ("ZIP", "zip", [], 0),
]
W, H, CX, CY = 460, 500, 230, 230
R0, R1, R2, R3 = 62, 128, 134, 214          # centre hole, inner ring end, outer ring start/end
ACCENT, INK = QColor("#2F7BF5"), QColor("#14181F")
SOURCE_CLASSES = {"CabinetWClass", "ExploreWClass", "Progman", "WorkerW", "#32770"}  # Explorer, Desktop, file dialogs


def fmt(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def thumb(path):
    if path.lower().endswith(tuple(engine.IMG)):
        r = QImageReader(path)
        r.setAutoTransform(True)
        s = r.size()
        if s.isValid():
            s.scale(112, 112, Qt.KeepAspectRatioByExpanding)
            r.setScaledSize(s)
            img = r.read()
            if not img.isNull():
                return QPixmap.fromImage(img)
    return QFileIconProvider().icon(QFileInfo(path)).pixmap(48, 48)


def wedge(r_in, r_out, a0, a1):
    """Ring segment between clockwise-from-top angles a0..a1 (degrees)."""
    ro = QRectF(CX - r_out, CY - r_out, 2 * r_out, 2 * r_out)
    ri = QRectF(CX - r_in, CY - r_in, 2 * r_in, 2 * r_in)
    p = QPainterPath()
    p.arcMoveTo(ro, 90 - a0)
    p.arcTo(ro, 90 - a0, -(a1 - a0))
    p.arcTo(ri, 90 - a1, a1 - a0)
    p.closeSubpath()
    return p


def polar(r, a):
    return QPointF(CX + r * math.sin(math.radians(a)), CY - r * math.cos(math.radians(a)))


# ---- the radial menu -------------------------------------------------------
class RadialMenu(QWidget):
    chosen = Signal(list, str, int, str)   # files, mode, value, label
    dismissed = Signal()

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.setFixedSize(W, H)
        self.files, self.pix = [], None
        self.cat = self.opt = None
        self.zone = None
        self.winId()  # create the native window now so it is already a registered drop target

    def popup(self, pos):
        self.files, self.pix, self.cat, self.opt, self.zone = [], None, None, None, None
        scr = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        x = min(max(pos.x() - CX, g.left()), g.right() - W)
        y = min(max(pos.y() - CY, g.top()), g.bottom() - H)
        self.move(x, y)
        self.show()
        self.raise_()

    # -- hit testing
    def _hover(self, p):
        dx, dy = p.x() - CX, p.y() - CY
        r, a = math.hypot(dx, dy), math.degrees(math.atan2(dx, -dy)) % 360
        self.opt, self.zone = None, "none"
        if r < R0:
            self.cat, self.zone = None, "centre"
        elif r <= R1:
            self.cat, self.zone = int(((a + 60) % 360) // 120), "inner"
        elif r >= R2 and r <= R3 and self.cat is not None and CATS[self.cat][2]:
            n = len(CATS[self.cat][2])
            rel = (a - (self.cat * 120 - 60)) % 360
            if rel < 120:
                self.opt, self.zone = int(rel // (120 / n)), "outer"
        self.update()

    def choice(self):
        """-> (mode, value, caption) or None"""
        if self.cat is None:
            return None
        title, mode, opts, dflt = CATS[self.cat]
        if mode == "zip":
            return ("zip", 0, "Zip it") if self.zone == "inner" else None
        if self.zone == "inner":
            self.opt_eff = dflt
        elif self.zone == "outer" and self.opt is not None:
            self.opt_eff = self.opt
        else:
            return None
        label, _, value = opts[self.opt_eff]
        return (mode, value, f"By quality: {label}" if mode == "quality" else f"Shrink to under {label}")

    # -- drag and drop
    def _accept(self, e):
        if e.possibleActions() & Qt.CopyAction:
            e.setDropAction(Qt.CopyAction)   # copy, never move: Explorer must not delete the original
        e.accept()

    def dragEnterEvent(self, e):
        if not e.mimeData().hasUrls():
            return
        self.files = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if self.files:
            self.pix = thumb(self.files[0])
        self._accept(e)
        self._hover(e.position())

    def dragMoveEvent(self, e):
        self._accept(e)
        self._hover(e.position())

    def dragLeaveEvent(self, e):
        self.hide()
        self.dismissed.emit()

    def dropEvent(self, e):
        self._hover(e.position())
        c, files = self.choice(), self.files
        self._accept(e)
        self.hide()
        if c and files:
            self.chosen.emit(files, c[0], c[1], c[2])
        else:
            self.dismissed.emit()

    # -- painting
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(CX, CY)
        p.setPen(Qt.NoPen)
        for i in range(7, 0, -1):                      # soft shadow
            p.setBrush(QColor(30, 50, 80, 5))
            p.drawEllipse(c, R3 + 6 + i * 2, R3 + 6 + i * 2)
        p.setBrush(QColor(206, 219, 233, 175))         # frosted bezel (also keeps the disc hit-testable)
        p.drawEllipse(c, R3 + 7, R3 + 7)

        glass = QLinearGradient(0, CY - R3, 0, CY + R3)
        glass.setColorAt(0, QColor(255, 255, 255, 245))
        glass.setColorAt(1, QColor(221, 231, 242, 245))

        def draw(path, hot, soft=False):
            p.setPen(QPen(QColor(255, 255, 255, 230), 1.5))
            p.setBrush(ACCENT if hot else QColor(207, 224, 255, 250) if soft else glass)
            p.drawPath(path)

        def label(pt, main, sub, hot):
            p.setPen(Qt.white if hot else INK)
            f = QFont("Segoe UI", 10, QFont.Bold)
            p.setFont(f)
            dy = -7 if sub else 0
            p.drawText(QRectF(pt.x() - 55, pt.y() - 12 + dy, 110, 24), Qt.AlignCenter, main)
            if sub:
                f = QFont("Segoe UI", 8)
                p.setFont(f)
                p.setPen(QColor(255, 255, 255, 210) if hot else QColor(80, 90, 105))
                p.drawText(QRectF(pt.x() - 55, pt.y() + 3, 110, 18), Qt.AlignCenter, sub)

        for i, (title, mode, opts, dflt) in enumerate(CATS):
            hot = self.cat == i and self.zone == "inner"
            a0 = i * 120 - 60
            draw(wedge(R0, R1, a0 + 1, a0 + 119), hot, self.cat == i and self.zone == "outer")
            label(polar((R0 + R1) / 2, a0 + 60), title, "", hot)

        if self.cat is not None and CATS[self.cat][2]:
            opts, dflt = CATS[self.cat][2], CATS[self.cat][3]
            step = 120 / len(opts)
            base = self.cat * 120 - 60
            for j, (lab, hint, _) in enumerate(opts):
                hot = self.opt == j
                soft = self.zone == "inner" and j == dflt
                a0 = base + j * step
                draw(wedge(R2, R3, a0 + 1, a0 + step - 1), hot, soft)
                label(polar((R2 + R3) / 2, a0 + step / 2), lab, hint, hot)

        p.setPen(QPen(QColor(255, 255, 255, 230), 1.5))  # centre: preview + filename pill
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawEllipse(c, R0 - 4, R0 - 4)
        if self.files:
            if self.pix and not self.pix.isNull():
                path = QPainterPath()
                path.addRoundedRect(QRectF(CX - 26, CY - 38, 52, 52), 8, 8)
                p.save()
                p.setClipPath(path)
                side = min(self.pix.width(), self.pix.height())
                src = QRectF((self.pix.width() - side) / 2, (self.pix.height() - side) / 2, side, side)
                p.drawPixmap(QRectF(CX - 26, CY - 38, 52, 52), self.pix, src)
                p.restore()
            name = os.path.basename(self.files[0].rstrip("/\\")) if len(self.files) == 1 else f"{len(self.files)} items"
            p.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
            text = QFontMetrics(p.font()).elidedText(name, Qt.ElideMiddle, 92)
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect(QRectF(CX - 52, CY + 18, 104, 22), 6, 6)
            p.setPen(Qt.white)
            p.drawText(QRectF(CX - 52, CY + 18, 104, 22), Qt.AlignCenter, text)

        ch = self.choice()                              # caption under the wheel
        text = ch[2] if ch else "Drop on an option"
        p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        w = QFontMetrics(p.font()).horizontalAdvance(text) + 28
        box = QRectF(CX - w / 2, CY + R3 + 18, w, 30)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 24, 31, 215))
        p.drawRoundedRect(box, 15, 15)
        p.setPen(Qt.white)
        p.drawText(box, Qt.AlignCenter, text)


# ---- result toast ----------------------------------------------------------
class Toast(QLabel):
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("background:#14181F;color:white;padding:12px 18px;border-radius:12px;font:10pt 'Segoe UI';")
        self.path = None
        self.timer = QTimer(self, singleShot=True, interval=5000)
        self.timer.timeout.connect(self.hide)

    def say(self, text, path=None):
        self.path = path
        self.setText(text)
        self.adjustSize()
        g = QGuiApplication.primaryScreen().availableGeometry()
        self.move(g.right() - self.width() - 20, g.bottom() - self.height() - 20)
        self.show()
        self.timer.start()

    def mousePressEvent(self, e):
        if self.path and os.path.exists(self.path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self.path)])
        self.hide()


# ---- background job --------------------------------------------------------
class Signals(QObject):
    done = Signal(list, list)


class Job(QRunnable):
    def __init__(self, files, mode, value, sig):
        super().__init__()
        self.args, self.sig = (files, mode, value), sig

    def run(self):
        self.sig.done.emit(*engine.run(*self.args))


# ---- app: global trigger (left mouse held + Shift while over Explorer) ------
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    u32 = ctypes.windll.user32
    u32.GetAsyncKeyState.restype = ctypes.c_short
    u32.WindowFromPoint.argtypes, u32.WindowFromPoint.restype = [wintypes.POINT], ctypes.c_void_p
    u32.GetAncestor.argtypes, u32.GetAncestor.restype = [ctypes.c_void_p, ctypes.c_uint], ctypes.c_void_p
    u32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

    import winreg
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def startup_cmd():
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        return f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.abspath(__file__)}"'

    def startup_enabled():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
                winreg.QueryValueEx(k, "Squeeze")
            return True
        except OSError:
            return False

    def set_startup(on):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "Squeeze", 0, winreg.REG_SZ, startup_cmd())
            else:
                try:
                    winreg.DeleteValue(k, "Squeeze")
                except OSError:
                    pass

    def key_down(vk):
        return bool(u32.GetAsyncKeyState(vk) & 0x8000)

    def over_explorer():
        pt = wintypes.POINT()
        u32.GetCursorPos(ctypes.byref(pt))
        hwnd = u32.WindowFromPoint(pt)
        root = u32.GetAncestor(hwnd, 2) if hwnd else None  # GA_ROOT
        buf = ctypes.create_unicode_buffer(256)
        if root:
            u32.GetClassNameW(root, buf, 256)
        return buf.value in SOURCE_CLASSES


def make_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(ACCENT)
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(Qt.white)
    p.drawEllipse(22, 22, 20, 20)
    p.setPen(QPen(Qt.white, 3))
    for a in (0, 120, 240):
        p.drawLine(QPointF(32, 32), QPointF(32 + 26 * math.sin(math.radians(a + 60)), 32 - 26 * math.cos(math.radians(a + 60))))
    p.end()
    return QIcon(pm)


class App:
    def __init__(self):
        self.qt = QApplication(sys.argv)
        self.qt.setQuitOnLastWindowClosed(False)
        self.menu, self.toast, self.sig = RadialMenu(), Toast(), Signals()
        self.menu.chosen.connect(self.start)
        self.menu.dismissed.connect(self.disarm)
        self.sig.done.connect(self.finished)
        self.press = None
        self.press_ok = False
        self.armed = True

        self.tray = QSystemTrayIcon(make_icon())
        self.tray.setToolTip("Squeeze: drag a file, press Shift")
        m = QMenu()
        m.addAction("Drag a file in Explorer, then press Shift").setEnabled(False)
        st = m.addAction("Start with Windows")
        st.setCheckable(True)
        st.setChecked(startup_enabled())
        st.toggled.connect(set_startup)
        m.addSeparator()
        m.addAction("Quit", self.qt.quit)
        self.tray.setContextMenu(m)
        self.tray.show()

        self.timer = QTimer(interval=25)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def disarm(self):
        self.armed = False

    def poll(self):
        down, shift = key_down(0x01), key_down(0x10)
        if not shift:
            self.armed = True
        if not down:
            self.press = None
            return
        pos = QCursor.pos()
        if self.press is None:
            self.press, self.press_ok = pos, over_explorer()
            return
        moved = (pos - self.press).manhattanLength() > 12
        if shift and moved and self.armed and self.press_ok and not self.menu.isVisible():
            self.menu.popup(pos)
            QTimer.singleShot(30, lambda: u32.mouse_event(1, 1, 0, 0, 0))   # 1px nudge so OLE re-targets the new window
            QTimer.singleShot(60, lambda: u32.mouse_event(1, 0xFFFFFFFF, 0, 0, 0))

    def start(self, files, mode, value, label):
        self.toast.say(f"{label}…")
        QThreadPool.globalInstance().start(Job(files, mode, value, self.sig))

    def finished(self, results, errors):
        lines = []
        if len(results) == 1:
            out, a, b = results[0]
            lines.append(f"✓ {os.path.basename(out)}\n{fmt(a)} → {fmt(b)}  (−{100 - b * 100 // max(a, 1)}%)")
        elif results:
            a, b = sum(r[1] for r in results), sum(r[2] for r in results)
            lines.append(f"✓ {len(results)} files\n{fmt(a)} → {fmt(b)}  (−{100 - b * 100 // max(a, 1)}%)")
        lines += errors[:2]
        self.toast.say("\n".join(lines) or "Nothing to do", results[0][0] if results else None)

    def run(self):
        return self.qt.exec()


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("Squeeze runs on Windows only.")
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW(None, False, "SqueezeSingleInstance")
    if ctypes.get_last_error() == 183:   # already running
        sys.exit(0)
    sys.exit(App().run())
