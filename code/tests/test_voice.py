"""Phase 7: bo khop lenh giong noi, luot nghe tren GatewayHome va nut micro o ban mock.

Khong can faster_whisper, sounddevice hay mic: thay VoiceEngine bang FakeEngine.
"""

from tests.test_gateway import FakeClock, Recorder  # dat bien moi truong gia truoc khi import config
from tests.test_module3 import make_web  # noqa: E402

import random  # noqa: E402
import tempfile  # noqa: E402
import threading  # noqa: E402
import unicodedata  # noqa: E402
import unittest  # noqa: E402
from pathlib import Path  # noqa: E402

from yolohome import config  # noqa: E402
from yolohome.voice import VOICE_COMMANDS, match_command  # noqa: E402
from yolohome.voice.listen import (  # noqa: E402
    ModelError,
    RecordingError,
    Transcript,
    VoiceEngine,
    load_model,
    model_label,
    parse_mic,
)
from yolohome.web.mock import MOCK_TRANSCRIBE, CommandError, MockHome  # noqa: E402


class FakeEngine:
    """Thay VoiceEngine: moi lan listen tra ve cau tiep theo trong texts, hoac nem loi trong errors."""

    label = "Whisper test"

    def __init__(self, texts=(), errors=(), gate=None):
        self.texts = list(texts)
        self.errors = list(errors)
        self.gate = gate
        self.ready = True
        self.error = None
        self.calls = 0

    def load(self):
        return object()

    def listen(self, on_status=None):
        self.calls += 1
        on_status("listening", "Mic test")
        if self.gate is not None:
            self.gate.wait(2)
        if self.errors:
            error = self.errors.pop(0)
            if error is not None:
                raise error
        on_status("transcribing", "")
        return Transcript(self.texts.pop(0), 3.0, 1.2, 0.4)


class MatchCommandTest(unittest.TestCase):
    def test_four_commands(self):
        self.assertEqual(match_command("bật đèn"), ("light", {"on": True}))
        self.assertEqual(match_command("tắt đèn"), ("light", {"on": False}))
        self.assertEqual(match_command("bật quạt"), ("fan", {"on": True}))
        self.assertEqual(match_command("tắt quạt"), ("fan", {"on": False}))

    def test_case_punctuation_spaces_and_nfd(self):
        self.assertEqual(match_command("  Bật   Đèn. "), ("light", {"on": True}))
        self.assertEqual(match_command("TẮT QUẠT!"), ("fan", {"on": False}))
        decomposed = unicodedata.normalize("NFD", "bật quạt")
        self.assertEqual(match_command(decomposed), ("fan", {"on": True}))

    def test_rejects_everything_else(self):
        for text in ("", "đừng bật đèn", "đừng tắt quạt", "bật đèn rồi tắt quạt", "mở cửa", "Bật đen", "bật đèn lên"):
            self.assertIsNone(match_command(text), text)


class ListenHelpersTest(unittest.TestCase):
    def test_parse_mic(self):
        self.assertIsNone(parse_mic(""))
        self.assertIsNone(parse_mic(None))
        self.assertEqual(parse_mic(" 2 "), 2)
        self.assertEqual(parse_mic("Microphone Array"), "Microphone Array")

    def test_model_label(self):
        self.assertEqual(model_label("small"), "Whisper small")
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(model_label(folder), Path(folder).name)

    def test_incomplete_model_folder_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "model.bin").write_bytes(b"")
            with self.assertRaises(ModelError) as caught:
                load_model(folder)
            self.assertIn("config.json", str(caught.exception))

    def test_missing_model_folder_is_reported(self):
        with self.assertRaises(ModelError) as caught:
            load_model(str(Path(tempfile.gettempdir()) / "khong-co-mo-hinh" / "pho"))
        self.assertIn("VOICE_MODEL", str(caught.exception))

    def test_engine_keeps_error_and_retries(self):
        attempts = []

        def loader(source):
            attempts.append(source)
            if len(attempts) == 1:
                raise ModelError("Chưa có mô hình")
            return "model"

        engine = VoiceEngine("small", loader=loader)
        try:
            import sounddevice  # noqa: F401
        except ImportError:
            with self.assertRaises(ModelError):
                engine.load()
            self.assertIn("requirements-voice.txt", engine.error)
            self.assertFalse(engine.ready)
            return
        with self.assertRaises(ModelError):
            engine.load()
        self.assertEqual(engine.error, "Chưa có mô hình")
        self.assertEqual(engine.load(), "model")
        self.assertTrue(engine.ready)
        self.assertIsNone(engine.error)


def voice_web(engine):
    home, gw, clock, events = make_web()
    home.voice_engine = engine
    return home, gw, clock, events


def run_turn(home):
    home.start_voice()
    home.voice_thread.join(timeout=5)
    home.tick()


def statuses(events):
    return [data["status"] for kind, data in events.events if kind == "voice"]


class GatewayVoiceTest(unittest.TestCase):
    def test_valid_command_sends_exactly_one_request(self):
        home, gw, clock, events = voice_web(FakeEngine(["Bật quạt."]))
        run_turn(home)
        self.assertEqual(statuses(events), ["listening", "transcribing", "sent"])
        self.assertEqual(events.last("voice")["text"], "Bật quạt.")
        gw.ser.lines = []
        gw.next_sample = 0
        gw.step()
        fan_lines = [line for line in gw.ser.written if line.startswith(b"FAN:")]
        # Quat bat lai dung toc do da nho (65%)
        self.assertEqual(fan_lines, [b"FAN:65\n"])
        log = home.log(kind="voice")
        self.assertEqual(log["items"][0]["status"], "Đã gửi")
        self.assertEqual(home.snapshot()["voice"]["status"], "sent")

    def test_out_of_scope_sentence_sends_nothing(self):
        home, gw, clock, events = voice_web(FakeEngine(["đừng bật quạt"]))
        run_turn(home)
        self.assertEqual(events.last("voice")["status"], "rejected")
        self.assertIn("bốn lệnh", events.last("voice")["message"])
        gw.ser.lines = []
        gw.next_sample = 0
        gw.step()
        self.assertFalse(any(line.startswith((b"FAN:", b"LIGHT:")) for line in gw.ser.written))
        self.assertEqual(home.log(kind="voice")["items"][0]["status"], "Từ chối")

    def test_mic_error_releases_the_lock(self):
        engine = FakeEngine(["bật đèn"], errors=[RecordingError("Mic mất mẫu."), None])
        home, gw, clock, events = voice_web(engine)
        run_turn(home)
        self.assertEqual(events.last("voice")["status"], "error")
        self.assertEqual(events.last("voice")["message"], "Mic mất mẫu.")
        run_turn(home)
        self.assertEqual(events.last("voice")["status"], "sent")
        self.assertEqual(engine.calls, 2)

    def test_second_click_while_listening_is_busy(self):
        gate = threading.Event()
        home, gw, clock, events = voice_web(FakeEngine(["tắt đèn"], gate=gate))
        home.start_voice()
        with self.assertRaises(CommandError) as caught:
            home.start_voice()
        self.assertEqual(caught.exception.status, 409)
        gate.set()
        home.voice_thread.join(timeout=5)
        home.tick()
        self.assertEqual(events.last("voice")["status"], "sent")

    def test_rate_limit_becomes_voice_error(self):
        home, gw, clock, events = voice_web(FakeEngine(["bật quạt"]))
        home.command("fan", {"on": True, "speed": 40})
        run_turn(home)
        self.assertEqual(events.last("voice")["status"], "error")
        self.assertIn("2 giây", events.last("voice")["message"])

    def test_no_command_after_close(self):
        gate = threading.Event()
        home, gw, clock, events = voice_web(FakeEngine(["bật quạt"], gate=gate))
        home.start_voice()
        home.stop.set()
        gate.set()
        home.voice_thread.join(timeout=5)
        self.assertTrue(gw.commands.empty())

    def test_voice_off_is_503_and_snapshot_explains(self):
        home, gw, clock, events = make_web()
        home.voice_note = "Giọng nói đang tắt (VOICE_ENABLE=0 trong .env)."
        with self.assertRaises(CommandError) as caught:
            home.start_voice()
        self.assertEqual(caught.exception.status, 503)
        view = home.snapshot()
        self.assertTrue(view["features"]["voice"])
        self.assertFalse(view["features"]["voice_live"])
        self.assertIn("VOICE_ENABLE", view["voice_note"])
        self.assertEqual(view["voice_commands"], [text for text, device, on in VOICE_COMMANDS])

    def test_preload_failure_is_logged(self):
        home, gw, clock, events = make_web()

        def broken(source):
            raise ModelError("Chưa có mô hình Whisper small trong cache.")

        home.voice_engine = VoiceEngine("small", loader=broken)
        home._preload_voice()
        home.tick()
        self.assertEqual(events.last("voice")["status"], "off")
        self.assertFalse(home.snapshot()["features"]["voice_live"])
        self.assertIsNone(home.snapshot()["voice"])
        self.assertEqual(home.log(kind="system")["items"][0]["status"], "Lỗi")


class MockVoiceTest(unittest.TestCase):
    def make(self):
        clock = FakeClock()
        events = Recorder()
        home = MockHome(events, clock=clock, ack_ms=900, rng=random.Random(1))
        return home, clock, events

    def test_staged_turn_then_device_confirms(self):
        home, clock, events = self.make()
        self.assertEqual(home.start_voice(), {"status": "started"})
        self.assertEqual(events.last("voice")["status"], "listening")
        with self.assertRaises(CommandError) as caught:
            home.start_voice()
        self.assertEqual(caught.exception.status, 409)
        clock.advance(config.VOICE_SECONDS)
        home.tick()
        self.assertEqual(events.last("voice")["status"], "transcribing")
        clock.advance(MOCK_TRANSCRIBE)
        home.tick()
        self.assertEqual(events.last("voice")["status"], "sent")
        self.assertEqual(events.last("voice")["text"], "bật đèn")
        clock.advance(1)
        home.tick()
        self.assertTrue(events.last("device")["on"])
        home.start_voice()

    def test_offline_turn_is_an_error(self):
        home, clock, events = self.make()
        home.simulate("offline")
        home.start_voice()
        clock.advance(config.VOICE_SECONDS + MOCK_TRANSCRIBE)
        home.tick()
        self.assertEqual(events.last("voice")["status"], "error")


if __name__ == "__main__":
    unittest.main()
