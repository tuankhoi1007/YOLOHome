// Dashboard (Figma 11:593 / 11:1014 / 11:1418). Tai snapshot mot lan qua api.state(),
// sau do chi cap nhat theo su kien SSE. Cam bien len man hinh ngay khi may chu nhan (< 5 s).

import { api, listen } from "./api.js";
import { byId, setText } from "./dom.js";
import { ago, clock, num } from "./format.js";
import { Devices } from "./devices.js";
import { Ai } from "./ai.js";
import { RecentLog } from "./logview.js";
import { setupThresholds } from "./thresholds.js";
import { toast } from "./toast.js";

let state = null;
// Thoi diem (dong ho trinh duyet, ms) cam bien do lan cuoi, tinh tu "age" cua may chu
let sensorsAt = 0;
let serverUp = false;

const devices = new Devices(byId("devices"));
const ai = new Ai(byId("ai"), toast);
const recentLog = new RecentLog(byId("log-tabs"), byId("log-recent"));

// ---------- cam bien (muc 01) ----------

const METRICS = {
  temp: { card: "metric-temp", limit: "temp_max", over: (value, limit) => value > limit },
  humid: { card: "metric-humid", limit: "humid_max", over: (value, limit) => value > limit },
  light: { card: "metric-light", limit: "light_min", over: (value, limit) => value < limit },
};

function part(card, role) {
  return card.querySelector('[data-role="' + role + '"]');
}

// Chip nho goc phai the (11:626). Vuot nguong thi do.
function metricChip(name, value, over) {
  if (value === null || value === undefined) return ["chip", "Chưa có số"];
  if (over) return ["chip chip-danger", "VƯỢT NGƯỠNG!"];
  if (name === "humid") return value >= 50 && value <= 70 ? ["chip chip-ok", "Lý tưởng"] : ["chip", "Bình thường"];
  if (name === "light") return ["chip chip-warn", "Đủ sáng"];
  return ["chip chip-ok", "Bình thường"];
}

function renderSensors() {
  const sensors = state.sensors;
  const online = state.gateway.online && serverUp;
  for (const name in METRICS) {
    const meta = METRICS[name];
    const card = byId(meta.card);
    const value = sensors[name];
    const limit = state.thresholds[meta.limit];
    const over = value !== null && value !== undefined && meta.over(value, limit);
    card.classList.toggle("is-alert", over);
    setText(part(card, "value"), num(value));
    setText(part(card, "limit"), num(limit));
    const [chipClass, chipText] = metricChip(name, value, over);
    const chip = part(card, "chip");
    chip.className = chipClass;
    setText(chip, chipText);
    part(card, "dot").className = "dot " + (online ? "is-on" : "is-off");
  }
  renderAges();
}

// Moi giay: "Cap nhat: 3 giay truoc", hoac "Lan cuoi: 14:02:15" khi mat ket noi
function renderAges() {
  if (!state) return;
  const online = state.gateway.online && serverUp;
  const seconds = (Date.now() - sensorsAt) / 1000;
  const lastClock = clock(sensorsAt / 1000);
  const text = online ? "Cập nhật: " + ago(seconds) : "Lần cuối: " + lastClock + " (Không có dữ liệu mới)";
  for (const name in METRICS) {
    const card = byId(METRICS[name].card);
    setText(part(card, "age"), text);
    part(card, "age").parentElement.classList.toggle("is-stale", !online);
  }
  setText(byId("conn-banner-text"), serverUp ? "Các thông số hiển thị giá trị lưu lần cuối lúc " + lastClock + "." : "Đang thử kết nối lại…");
}

// ---------- canh bao va den LED (Module 2) ----------

function renderAlert() {
  const alert = state.alert;
  const banner = byId("led-banner");
  banner.classList.toggle("is-alert", !alert.ok);
  if (alert.ok) {
    setText(byId("led-title"), "Đèn LED RGB phần cứng (Chân P14):");
    setText(byId("led-text"), "Đang sáng Xanh lá (môi trường trong ngưỡng).");
  } else {
    setText(byId("led-title"), "Đèn LED RGB (P14) đang nhấp nháy ĐỎ:");
    setText(byId("led-text"), alert.text);
  }
  setText(byId("sim-overheat"), "Mô phỏng vượt ngưỡng nhiệt độ (>" + num(state.thresholds.temp_max) + "°C)");
}

// "Nhiệt độ cao: 32.2°C (ngưỡng 30) | Ánh sáng thấp: ..." -> "Nhiệt độ cao|Ánh sáng thấp"
function alertKinds(alert) {
  if (alert.ok) return "";
  return alert.text
    .split(" | ")
    .map((part) => part.split(":")[0].trim())
    .sort()
    .join("|");
}

// ---------- ket noi: Gateway va may chu web ----------

function renderConnection() {
  const gateway = state ? state.gateway : { online: false, label: "" };
  const online = gateway.online && serverUp;
  byId("gateway-dot").className = "status-dot " + (online ? "is-on" : "is-off");
  let text;
  if (!serverUp) text = "Máy chủ web: mất kết nối";
  else text = "Gateway: " + gateway.label + " / MQTT · " + (gateway.online ? "Online" : "Offline");
  setText(byId("gateway-text"), text);

  const banner = byId("conn-banner");
  banner.hidden = online || !state;
  setText(byId("conn-banner-title"), serverUp ? "Mất kết nối Adafruit IO / Gateway." : "Mất kết nối máy chủ web.");
  const testOffline = byId("test-offline");
  testOffline.setAttribute("aria-pressed", gateway.online ? "false" : "true");
  byId("test-offline-text").replaceChildren(...(gateway.online ? ["Test", document.createElement("br"), "Offline"] : ["Bật lại", document.createElement("br"), "Online"]));
  devices.setOffline(!online);
  renderAges();
}

// ---------- tai lai toan bo ----------

async function reload() {
  try {
    state = await api.state();
  } catch (err) {
    return;
  }
  sensorsAt = Date.now() - state.sensors.age * 1000;
  for (const node of document.querySelectorAll("[data-mock-only]")) node.hidden = !state.features.simulate;
  renderSensors();
  renderAlert();
  devices.load(state);
  ai.load(state);
  renderConnection();
  if (state.features.log) recentLog.reload();
}

// Tai ngay, khong doi SSE mo; moi lan SSE noi lai thi tai lai de khong sot su kien.
serverUp = true;
reload();

listen({
  open: () => {
    serverUp = true;
    ai.setServerUp(true);
    reload();
  },
  lost: () => {
    serverUp = false;
    ai.setServerUp(false);
    renderConnection();
  },
  sensors: (sensors) => {
    if (!state) return;
    state.sensors = sensors;
    sensorsAt = Date.now() - sensors.age * 1000;
    renderSensors();
  },
  alert: (alert) => {
    if (!state) return;
    const before = state.alert;
    state.alert = alert;
    renderAlert();
    renderSensors();
    // Chi bao khi bat dau canh bao hoac doi loai van de, khong bao moi lan so doi
    if (!alert.ok && (before.ok || alertKinds(alert) !== alertKinds(before))) {
      toast({ title: "Cảnh báo Module 2", text: alert.text, tone: "danger" });
    } else if (alert.ok && !before.ok) {
      toast({ title: "Hết cảnh báo", text: "Môi trường đã trở về trong ngưỡng.", tone: "ok" });
    }
  },
  thresholds: (values) => {
    if (!state) return;
    state.thresholds = values;
    renderSensors();
    renderAlert();
  },
  gateway: (gateway) => {
    if (!state) return;
    state.gateway = gateway;
    renderSensors();
    renderConnection();
  },
  device: (view) => devices.onEvent(view),
  face: (face) => ai.onFace(face),
  voice: (voice) => ai.onVoice(voice),
  log: (entry) => recentLog.onEntry(entry),
});

// ---------- nut tren header ----------

setupThresholds(
  () => state.thresholds,
  () => state.features.thresholds_write,
  (saved) => {
    state.thresholds = { temp_max: saved.temp_max, humid_max: saved.humid_max, light_min: saved.light_min };
    renderSensors();
    renderAlert();
    toast({ title: "Đã lưu ngưỡng", text: "Nhiệt > " + num(saved.temp_max) + "°C, ẩm > " + num(saved.humid_max) + "%, sáng < " + num(saved.light_min) + ".", tone: "ok" });
    // Ngưỡng có feed chưa tồn tại trên Adafruit: báo rõ là chưa lưu lên cloud
    if (saved.note) toast({ title: "Lưu ý", text: saved.note, tone: "danger" });
  },
);

byId("test-offline").addEventListener("click", () => {
  api.simulate(state.gateway.online ? "offline" : "online").catch((err) => toast({ title: "Lỗi", text: err.message, tone: "danger" }));
});

byId("sim-overheat").addEventListener("click", () => {
  api.simulate("overheat").catch((err) => toast({ title: "Không mô phỏng được", text: err.message, tone: "danger" }));
});

byId("conn-retry").addEventListener("click", () => {
  if (!serverUp) {
    location.reload();
  } else if (state.features.simulate) {
    api.simulate("online").catch((err) => toast({ title: "Lỗi", text: err.message, tone: "danger" }));
  } else {
    reload();
  }
});

byId("logout").addEventListener("click", async () => {
  try {
    await api.logout();
  } finally {
    location.href = "/login.html";
  }
});

setInterval(() => {
  renderAges();
  devices.tick();
}, 1000);
