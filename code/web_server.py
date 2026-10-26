# -*- coding: utf-8 -*-
"""Module 5 - Web tren laptop.

Phuc vu trang trong thu muc web/ va API /api/*. Trinh duyet khong bao gio thay AIO_KEY:
moi lenh di qua may chu nay roi moi toi Adafruit (D6). Dang nhap bang mot mat khau
chung WEB_PASSWORD trong .env (D10).

WEB_DATA=mock: du lieu gia lap (web_mock.py). WEB_DATA=live: doc feed Adafruit (web_live.py).
WEB_DATA=gateway: chay luon Module 1 + 2 trong web (web_gateway.py), mot chuong trinh cho demo.

Chay:  python web_server.py   roi mo http://127.0.0.1:8000 tren laptop
"""

import hmac
import json
import queue
import secrets
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import config
from web_mock import CommandError, MockHome

WEB_ROOT = Path(__file__).resolve().parent / "web"
HOST = "127.0.0.1"
COOKIE = "yolo_session"
# Mot buoi demo. Het han thi trang tu ve man dang nhap.
SESSION_SECONDS = 12 * 3600
# Sai mat khau 5 lan trong 60 giay thi tam khoa dang nhap, vi web mo duoc cua.
MAX_FAILS = 5
FAIL_WINDOW = 60
MAX_BODY = 10000
# SSE gui mot dong rong moi 15 giay de trinh duyet biet ket noi con song.
PING_SECONDS = 15
# Nhip goi home.tick(): du nho de xac nhan thiet bi (~0.9 s) va dem nguoc cua muot.
TICK_SECONDS = 0.5
# Trang can dang nhap. css/js/img khong chua bi mat nen khong chan.
PRIVATE_PAGES = ("/", "/index.html", "/log.html")

# Tu khai bao loai file: tren Windows, mimetypes doc registry va co may tra .js la text/plain,
# trinh duyet se tu choi chay module JS.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}

# Chi cho tai font Google; con lai chi tu chinh may chu nay.
CSP = (
    "default-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "frame-ancestors 'none'"
)


class Sessions:
    """Phien dang nhap luu trong RAM. Tat may chu la moi nguoi phai dang nhap lai."""

    def __init__(self, password, clock=time.time):
        self.password = password
        self.clock = clock
        self.tokens = {}
        self.fails = []
        self.lock = threading.Lock()

    def login(self, password):
        """Tra ve (token, None) neu dung; (None, 'wrong') hoac (None, 'locked') neu khong."""
        with self.lock:
            now = self.clock()
            self.fails = [at for at in self.fails if now - at < FAIL_WINDOW]
            if len(self.fails) >= MAX_FAILS:
                return None, "locked"
            # Mat khau rong khong bao gio dung, ke ca khi nguoi dung gui chuoi rong.
            given = str(password).encode("utf-8")
            right = self.password.encode("utf-8")
            if not self.password or not hmac.compare_digest(given, right):
                self.fails.append(now)
                return None, "wrong"
            token = secrets.token_urlsafe(32)
            self.tokens[token] = now + SESSION_SECONDS
            return token, None

    def check(self, token):
        if not token:
            return False
        with self.lock:
            expires = self.tokens.get(token)
            if expires is None:
                return False
            if self.clock() >= expires:
                del self.tokens[token]
                return False
            return True

    def logout(self, token):
        with self.lock:
            self.tokens.pop(token, None)


class EventClient:
    def __init__(self):
        self.queue = queue.Queue(maxsize=200)
        # Trinh duyet doc cham, hang doi day: dong ket noi, trang tu noi lai va tai lai snapshot.
        self.stale = False


class EventHub:
    """Chuyen su kien tu MockHome toi tung trinh duyet dang mo /api/events."""

    def __init__(self):
        self.clients = set()
        self.lock = threading.Lock()

    def subscribe(self):
        client = EventClient()
        with self.lock:
            self.clients.add(client)
        return client

    def unsubscribe(self, client):
        with self.lock:
            self.clients.discard(client)

    def publish(self, kind, data):
        with self.lock:
            clients = list(self.clients)
        for client in clients:
            try:
                client.queue.put_nowait((kind, data))
            except queue.Full:
                client.stale = True


class App:
    def __init__(self, home, sessions, hub):
        self.home = home
        self.sessions = sessions
        self.hub = hub


class Handler(BaseHTTPRequestHandler):
    server_version = "YoloHome"
    sys_version = ""

    def log_message(self, format, *args):
        # Khong in tung request (SSE va tai trang rat nhieu), chi in loi o _send_error.
        pass

    # ---------- dinh tuyen ----------

    def do_GET(self):
        url = urlsplit(self.path)
        path = url.path
        if path.startswith("/api/"):
            if not self._authed():
                self._json(401, {"error": "Chưa đăng nhập"})
                return
            if path == "/api/state":
                self._json(200, self.server.app.home.snapshot())
            elif path == "/api/events":
                self._events()
            elif path == "/api/log":
                self._log(parse_qs(url.query))
            else:
                self._json(404, {"error": "Không có API này"})
            return
        if path in PRIVATE_PAGES and not self._authed():
            self._redirect("/login.html")
            return
        if path == "/login.html" and self._authed():
            self._redirect("/")
            return
        self._static(path)

    def do_POST(self):
        path = urlsplit(self.path).path
        body = self._read_json()
        if body is None:
            return
        app = self.server.app
        if path == "/api/login":
            self._login(body)
            return
        if path == "/api/logout":
            app.sessions.logout(self._token())
            self._json(200, {"ok": True}, cookie=COOKIE + "=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict")
            return
        if not self._authed():
            self._json(401, {"error": "Chưa đăng nhập"})
            return
        try:
            if path == "/api/thresholds":
                self._json(200, app.home.set_thresholds(body))
            elif path.startswith("/api/devices/"):
                device = path[len("/api/devices/"):]
                self._json(202, app.home.command(device, body))
            elif path.startswith("/api/sim/"):
                kind = path[len("/api/sim/"):]
                self._json(200, app.home.simulate(kind))
            else:
                self._json(404, {"error": "Không có API này"})
        except CommandError as exc:
            self._json(exc.status, {"error": exc.message})

    # ---------- API ----------

    def _login(self, body):
        token, problem = self.server.app.sessions.login(body.get("password", ""))
        if problem == "locked":
            self._json(429, {"error": "Sai quá nhiều lần. Thử lại sau 1 phút."})
            return
        if problem == "wrong":
            self._json(401, {"error": "Mật khẩu không chính xác"})
            return
        # HttpOnly: JS trong trang khong doc duoc token. SameSite=Strict: trang la khong gui lenh thay duoc.
        # Chua co Secure vi web chay http trong mang LAN (xem lai o ROADMAP 8.2).
        cookie = (
            COOKIE + "=" + token + "; Path=/; Max-Age=" + str(SESSION_SECONDS)
            + "; HttpOnly; SameSite=Strict"
        )
        self._json(200, {"ok": True}, cookie=cookie)

    def _log(self, params):
        def first(name, default=""):
            values = params.get(name)
            if not values:
                return default
            return values[0]

        try:
            page = int(first("page", "1"))
        except ValueError:
            page = 1
        try:
            data = self.server.app.home.log(first("type", "all"), first("date"), first("q"), page)
        except CommandError as exc:
            self._json(exc.status, {"error": exc.message})
            return
        self._json(200, data)

    def _events(self):
        app = self.server.app
        token = self._token()
        client = app.hub.subscribe()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            # Bao trinh duyet noi lai sau 3 giay neu mat ket noi.
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            while not client.stale and app.sessions.check(token):
                try:
                    kind, data = client.queue.get(timeout=PING_SECONDS)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                text = "event: " + kind + "\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"
                self.wfile.write(text.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            app.hub.unsubscribe(client)

    # ---------- file tinh ----------

    def _static(self, path):
        if path == "/":
            path = "/index.html"
        target = (WEB_ROOT / path.lstrip("/")).resolve()
        # Chan ../ ra ngoai thu muc web (vi du /../.env)
        if not target.is_relative_to(WEB_ROOT) or not target.is_file():
            self._json(404, {"error": "Không tìm thấy"})
            return
        content_type = CONTENT_TYPES.get(target.suffix.lower())
        if content_type is None:
            self._json(404, {"error": "Không tìm thấy"})
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        # Dang lam giao dien: luon hoi lai may chu de thay ban moi.
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
        self.end_headers()
        self.wfile.write(data)

    # ---------- tien ich ----------

    def _token(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(raw)
        except Exception:
            return None
        morsel = cookie.get(COOKIE)
        if morsel is None:
            return None
        return morsel.value

    def _authed(self):
        return self.server.app.sessions.check(self._token())

    def _read_json(self):
        """Doc body JSON. Loi thi tra loi luon va tra ve None."""
        # Chi nhan application/json: form HTML tu trang khac khong gui duoc kieu nay.
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("application/json"):
            self._json(415, {"error": "Cần Content-Type application/json"})
            return None
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._json(413, {"error": "Dữ liệu gửi lên quá lớn"})
            return None
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except ValueError:
            self._json(400, {"error": "JSON không hợp lệ"})
            return None
        if not isinstance(body, dict):
            self._json(400, {"error": "JSON phải là một object"})
            return None
        return body

    def _security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", CSP)

    def _json(self, status, data, cookie=None):
        if status >= 500:
            print("Loi web", status, self.command, self.path)
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self._security_headers()
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()


def make_server(app, host, port):
    server = ThreadingHTTPServer((host, port), Handler)
    # Luong SSE chay mai; daemon de Ctrl+C tat duoc may chu.
    server.daemon_threads = True
    server.app = app
    return server


def run_ticker(home, stop):
    while not stop.wait(TICK_SECONDS):
        try:
            home.tick()
        except Exception as exc:
            print("Loi khi cap nhat du lieu web:", exc)


def main():
    print("Web - Module 5")
    if not config.WEB_PASSWORD:
        print("Thieu WEB_PASSWORD trong file .env. Dat mot mat khau rieng roi chay lai.")
        sys.exit(1)
    if config.WEB_DATA not in ("mock", "live", "gateway"):
        print("WEB_DATA =", config.WEB_DATA, "khong hop le. Dung mock, live hoac gateway.")
        sys.exit(1)
    hub = EventHub()
    app = App(None, Sessions(config.WEB_PASSWORD), hub)
    # D12: chi mo tren chinh laptop (127.0.0.1). May khac trong Wi-Fi khong vao duoc, nen khong mo cua tu xa duoc.
    # Mo cong web truoc, de khi cong ban thi chua dung toi cong COM va Adafruit.
    try:
        server = make_server(app, HOST, config.WEB_PORT)
    except OSError as exc:
        print("Khong mo duoc cong", config.WEB_PORT, "-", exc)
        print("Doi WEB_PORT trong .env hoac tat chuong trinh dang dung cong do.")
        sys.exit(1)
    # Nhap ban that o day de che do gia lap khong can paho-mqtt, pyserial
    if config.WEB_DATA == "gateway":
        from web_gateway import GatewayHome

        print("Du lieu: chay luon Module 1 + 2 tren cong", config.COM_PORT)
        print("Khong chay gateway.py va ngat OhStem: ca hai can cung cong COM.")
        home = GatewayHome(hub.publish)
    elif config.WEB_DATA == "live":
        from web_live import LiveHome

        home = LiveHome(hub.publish)
        print("Du lieu: that, doc feed Adafruit IO (can gateway.py dang chay de co so moi)")
    else:
        home = MockHome(hub.publish)
        print("Du lieu: gia lap (khong noi board, khong noi Adafruit)")
    app.home = home
    stop = threading.Event()
    ticker = threading.Thread(target=run_ticker, args=(home, stop), daemon=True)
    ticker.start()
    print("Mo trinh duyet: http://127.0.0.1:" + str(config.WEB_PORT))
    print("Dung bang Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Dung.")
    finally:
        stop.set()
        server.server_close()
        if hasattr(home, "close"):
            home.close()


if __name__ == "__main__":
    main()
