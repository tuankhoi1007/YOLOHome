// The thiet bi (Module 3). Bo cuc theo Figma 11:700, trang thai theo 181:10:
// trang thai yeu cau va trang thai that cua thiet bi tach rieng; moi loi deu co cach xu ly.
//
// Vong doi mot lenh:
//   idle --bam--> sending --may chu nhan (202)--> waiting --su kien "device" khop--> done
//                    |                               |
//                    +--loi--> failed (Thu lai)      +--qua 3 giay--> timeout (Kiem tra trang thai)
// Cong tac, mau, toc do luon hien trang thai THAT (tu su kien "device"), khong hien trang thai yeu cau.

import { api } from "./api.js";
import { h } from "./dom.js";
import { num } from "./format.js";

// Yeu cau phi chuc nang: bam dieu khien -> thiet bi phan ung duoi 3 giay.
const TIMEOUT_MS = 3000;

const BUSY = ["sending", "waiting"];

class DeviceCard {
  constructor(name) {
    this.name = name;
    this.confirmed = null;
    this.phase = "idle";
    this.request = null;
    this.error = "";
    this.sentAt = 0;
    this.latency = null;
    this.timer = null;
    this.offline = false;
    this.root = null;
  }

  busy() {
    return BUSY.includes(this.phase);
  }

  locked() {
    // Khong cho bam khi dang cho lenh truoc hoac mat ket noi
    return this.offline || this.busy();
  }

  async send(body) {
    if (this.locked()) return;
    this.request = body;
    this.phase = "sending";
    this.error = "";
    this.sentAt = performance.now();
    this.render();
    try {
      await api.command(this.name, body);
    } catch (err) {
      this.phase = "failed";
      this.error = err.message;
      this.render();
      return;
    }
    // Xac nhan co the da ve truoc khi fetch tra loi
    if (this.phase !== "sending") return;
    this.phase = "waiting";
    clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      if (this.phase === "waiting") {
        this.phase = "timeout";
        this.render();
      }
    }, Math.max(0, TIMEOUT_MS - (performance.now() - this.sentAt)));
    this.render();
  }

  // Hoi lai may chu trang thai that, dung khi qua thoi gian cho
  async refresh() {
    try {
      const state = await api.state();
      this.confirmed = state.devices[this.name];
      this.phase = "idle";
    } catch (err) {
      this.phase = "failed";
      this.error = err.message;
    }
    this.render();
  }

  load(view) {
    this.confirmed = view;
    if (!this.busy()) this.render();
  }

  // Su kien "device" tu may chu: day la trang thai that cua thiet bi
  onEvent(view) {
    this.confirmed = view;
    const pending = BUSY.includes(this.phase) || this.phase === "timeout";
    if (pending && this.request && this.matches(view)) {
      clearTimeout(this.timer);
      this.latency = (performance.now() - this.sentAt) / 1000;
      this.phase = "done";
    }
    this.render();
  }

  matches(view) {
    for (const key in this.request) {
      if (view[key] !== this.request[key]) return false;
    }
    return true;
  }

  setOffline(offline) {
    if (this.offline === offline) return;
    this.offline = offline;
    this.render();
  }

  // Chip trang thai (181:10)
  chip() {
    if (this.phase === "sending") return ["chip-warn", "Đang gửi lệnh"];
    if (this.phase === "waiting") return ["chip-warn", "Chờ thiết bị xác nhận"];
    if (this.phase === "failed") return ["chip-danger", "Gửi lệnh thất bại"];
    if (this.phase === "timeout") return ["chip-danger", "Quá thời gian chờ"];
    return this.confirmed && this.confirmed.on ? ["chip-ok", "Đang hoạt động"] : ["", "Đã tắt"];
  }

  // Dong phan hoi: [tone, chu, nut]
  note() {
    const last = this.confirmed && this.confirmed.on ? "đã bật" : "đã tắt";
    if (this.phase === "sending") return ["tone-warn", "Đang gửi yêu cầu. Vui lòng chờ.", null];
    if (this.phase === "waiting") return ["tone-warn", "Đã gửi yêu cầu. Trạng thái cuối: " + last + ".", null];
    if (this.phase === "failed") {
      const retry = h("button", { type: "button", onclick: () => this.retry() }, "Thử lại");
      return ["tone-danger", "Không thể gửi lệnh. Trạng thái thiết bị chưa thay đổi. " + this.error, retry];
    }
    if (this.phase === "timeout") {
      const check = h("button", { type: "button", onclick: () => this.refresh() }, "Kiểm tra trạng thái");
      return ["tone-danger", "Chưa nhận phản hồi. Kiểm tra trạng thái trước khi gửi lại.", check];
    }
    if (this.phase === "done") return ["tone-ok", "Trạng thái đã được thiết bị xác nhận.", null];
    return ["tone-ok", "Thiết bị đã xác nhận " + (this.confirmed && this.confirmed.on ? "bật." : "tắt."), null];
  }

  retry() {
    const body = this.request;
    this.phase = "idle";
    this.send(body);
  }

  latencyText() {
    return this.latency === null ? "Phản hồi: –" : "Phản hồi: " + num(this.latency) + " s";
  }

  noteNode() {
    const [tone, text, button] = this.note();
    return h("div", { class: "device-note " + tone, role: "status" }, h("span", null, text), button);
  }

  overlay() {
    return h(
      "div",
      { class: "device-overlay" },
      h("span", { class: "device-overlay-icon", "aria-hidden": "true" }, "⚠"),
      h("strong", null, "Không thể gửi lệnh"),
      h("span", null, "Mất kết nối thiết bị"),
    );
  }

  mount(container) {
    this.root = h("article", { class: "card device", "aria-label": this.title });
    container.append(this.root);
    this.render();
  }

  render() {
    if (!this.root || !this.confirmed) return;
    this.root.classList.toggle("is-offline", this.offline);
    this.root.replaceChildren(...this.body(), this.overlay());
  }
}

function head(icon, title, sub, right) {
  return h(
    "div",
    { class: "device-head" },
    h(
      "div",
      { class: "device-id" },
      h("span", { class: "icon-box" }, h("img", { src: icon, width: 20, height: 20, alt: "" })),
      h("div", null, h("h3", { class: "device-title" }, title), h("p", { class: "device-sub" }, sub)),
    ),
    right,
  );
}

function chipNode([tone, text]) {
  return h("span", null, h("span", { class: "chip " + tone }, text));
}

class LightCard extends DeviceCard {
  constructor(colors) {
    super("light");
    this.title = "Đèn LED RGB";
    this.colors = colors;
  }

  colorName(hex) {
    const found = this.colors.find((color) => color.hex === hex);
    return found ? found.name : hex;
  }

  body() {
    const state = this.confirmed;
    const toggle = h("button", {
      class: "switch",
      type: "button",
      role: "switch",
      "aria-checked": state.on ? "true" : "false",
      "aria-label": "Nguồn đèn",
      disabled: this.locked(),
      onclick: () => this.send({ on: !state.on }),
    });
    const swatches = this.colors.map((color) =>
      h("button", {
        class: "swatch",
        type: "button",
        style: { background: color.hex },
        "aria-label": color.name,
        "aria-pressed": state.color === color.hex ? "true" : "false",
        disabled: this.locked(),
        onclick: () => this.send({ color: color.hex }),
      }),
    );
    return [
      head("img/icon-sun.svg", this.title, "4 LED RGB / P14", toggle),
      chipNode(this.chip()),
      h("p", { class: "device-desc" }, "Bật/tắt và chọn màu cho 4 LED RGB. Màu áp dụng khi đèn bật."),
      h(
        "div",
        { class: "device-control" },
        h("span", { class: "caps device-control-label" }, "Tông màu chỉ định"),
        h("div", { class: "swatches" }, swatches, h("span", { class: "swatch-name" }, this.colorName(state.color))),
      ),
      this.noteNode(),
      h(
        "div",
        { class: "device-foot" },
        h("span", null, "Trạng thái: ", h("strong", null, state.on ? "ĐANG BẬT" : "ĐÃ TẮT")),
        h("span", { class: "accent" }, this.latencyText()),
      ),
    ];
  }
}

class FanCard extends DeviceCard {
  constructor() {
    super("fan");
    this.title = "Quạt làm mát";
    this.dragging = false;
  }

  render() {
    // Dang keo thanh truot thi khong ve lai, tranh giat
    if (this.dragging) return;
    super.render();
  }

  body() {
    const state = this.confirmed;
    const toggle = h("button", {
      class: "switch",
      type: "button",
      role: "switch",
      "aria-checked": state.on ? "true" : "false",
      "aria-label": "Nguồn quạt",
      disabled: this.locked(),
      onclick: () => this.send({ on: !state.on }),
    });
    const label = h("strong", null, state.speed + "%");
    const range = h("input", {
      class: "range",
      type: "range",
      min: 0,
      max: 100,
      step: 5,
      value: state.speed,
      style: { "--fill": state.speed + "%" },
      "aria-label": "Tốc độ quạt",
      disabled: this.locked(),
    });
    range.addEventListener("input", () => {
      this.dragging = true;
      label.textContent = range.value + "%";
      range.style.setProperty("--fill", range.value + "%");
    });
    range.addEventListener("change", () => {
      this.dragging = false;
      this.send({ speed: Number(range.value) });
    });
    return [
      head("img/icon-fan.svg", this.title, "Quạt mini / cổng chưa chốt (D4)", toggle),
      chipNode(this.chip()),
      h("p", { class: "device-desc" }, "Bật/tắt và chỉnh tốc độ gió 0 – 100%. Tốc độ áp dụng khi quạt quay."),
      h(
        "div",
        { class: "device-control" },
        h("span", { class: "caps device-control-label" }, "Tốc độ quay", label),
        range,
      ),
      this.noteNode(),
      h(
        "div",
        { class: "device-foot" },
        h("span", null, "Trạng thái: ", h("strong", null, state.on ? "ĐANG QUAY" : "ĐÃ TẮT")),
        h("span", { class: "accent" }, this.latencyText()),
      ),
    ];
  }
}

class DoorCard extends DeviceCard {
  constructor(relockSeconds) {
    super("door");
    this.title = "Khóa cửa điện";
    this.relockSeconds = relockSeconds;
    this.relockAt = null;
  }

  load(view) {
    this.trackRelock(view);
    super.load(view);
  }

  onEvent(view) {
    this.trackRelock(view);
    super.onEvent(view);
  }

  // Dem nguoc theo dong ho trinh duyet, bat dau tu so giay may chu bao
  trackRelock(view) {
    this.relockAt = view.relock_in === null ? null : performance.now() + view.relock_in * 1000;
  }

  secondsLeft() {
    if (this.relockAt === null) return null;
    return Math.max(0, Math.ceil((this.relockAt - performance.now()) / 1000));
  }

  tick() {
    if (this.relockAt !== null && !this.busy()) this.render();
  }

  matches(view) {
    return view.locked === (this.request.action === "lock");
  }

  chip() {
    const unlocking = this.request && this.request.action === "unlock";
    if (this.busy()) return ["chip-warn", unlocking ? "Đang mở khóa" : "Đang khóa"];
    if (this.phase === "failed" || this.phase === "timeout") {
      return ["chip-danger", unlocking ? "Mở khóa thất bại" : "Khóa thất bại"];
    }
    return this.confirmed.locked ? ["chip-danger", "Đang khóa"] : ["chip-ok", "Đã mở khóa"];
  }

  note() {
    const unlocking = this.request && this.request.action === "unlock";
    if (this.busy()) return ["tone-warn", "Giữ nguyên trạng thái cho đến khi nhận phản hồi.", null];
    if (this.phase === "failed") return ["tone-danger", "Không gửi được lệnh. " + this.error, null];
    if (this.phase === "timeout") return ["tone-danger", "Không nhận được phản hồi từ khóa cửa. Kiểm tra kết nối thiết bị.", null];
    if (!this.confirmed.locked) return ["tone-ok", "Cửa đang mở khóa. Hệ thống tự khóa khi hết thời gian.", null];
    if (this.phase === "done" && !unlocking) return ["tone-ok", "Thiết bị đã xác nhận khóa cửa.", null];
    return ["", "Trạng thái cửa chỉ cập nhật từ phản hồi thiết bị.", null];
  }

  bigLine() {
    const unlocking = this.request && this.request.action === "unlock";
    if (this.busy()) return h("p", { class: "door-big" }, unlocking ? "Đang gửi lệnh mở cửa" : "Đang gửi lệnh khóa cửa");
    if (this.phase === "failed" || this.phase === "timeout") {
      return h("p", { class: "door-big" }, unlocking ? "Chưa xác nhận mở khóa" : "Chưa xác nhận khóa cửa");
    }
    const left = this.secondsLeft();
    if (!this.confirmed.locked && left !== null) {
      return h("p", null, h("span", { class: "door-count" }, String(left).padStart(2, "0")), h("span", { class: "device-sub" }, " giây nữa tự khóa"));
    }
    return h("p", { class: "door-big" }, this.confirmed.locked ? "Cửa đang khóa" : "Cửa đã được mở khóa");
  }

  action() {
    const unlocking = this.request && this.request.action === "unlock";
    if (this.busy()) {
      return h("button", { class: "device-action is-primary", type: "button", disabled: true, "aria-busy": "true" }, unlocking ? "Đang mở…" : "Đang khóa…");
    }
    if (this.phase === "timeout") {
      return h("button", { class: "device-action", type: "button", disabled: this.offline, onclick: () => this.refresh() }, "Kiểm tra trạng thái");
    }
    if (this.phase === "failed") {
      return h("button", { class: "device-action", type: "button", disabled: this.offline, onclick: () => this.retry() }, "Thử lại");
    }
    if (!this.confirmed.locked) {
      return h("button", { class: "device-action is-primary", type: "button", disabled: this.offline, onclick: () => this.send({ action: "lock" }) }, "Khóa ngay");
    }
    // Nut mo tay luon bam duoc, ke ca khi nhan dien khuon mat that bai (CLAUDE.md)
    return h("button", { class: "device-action", type: "button", disabled: this.offline, onclick: () => this.send({ action: "unlock" }) }, "Mở khóa bằng tay");
  }

  body() {
    const state = this.confirmed;
    const [tone, text] = this.chip();
    const [noteTone, noteText] = this.note();
    return [
      head(state.locked ? "img/icon-lock.svg" : "img/icon-unlock.svg", this.title, "Servo / cổng chưa chốt (D4)", h("span", { class: "chip " + tone }, text.toUpperCase())),
      h("p", { class: "device-desc" }, "Servo xoay 0° (đóng) – 90° (mở). Tự khóa sau " + this.relockSeconds + " giây. Luôn mở được bằng tay khi nhận diện khuôn mặt lỗi."),
      this.bigLine(),
      this.action(),
      h("div", { class: "device-note " + noteTone, role: "status" }, h("span", null, noteText)),
      h(
        "div",
        { class: "device-foot" },
        h("span", null, "Góc servo: ", h("strong", null, state.locked ? "0°" : "90°")),
        h("span", { class: "accent" }, this.latencyText()),
      ),
    ];
  }
}

function placeholder(title, why) {
  return h("article", { class: "card placeholder-card" }, h("strong", null, title), h("span", null, why));
}

export class Devices {
  constructor(container) {
    this.container = container;
    this.cards = {};
  }

  load(state) {
    if (!state.features.devices) {
      this.cards = {};
      const why = "Chưa nối thiết bị thật: cần PROTOCOL.md v0.2.0 (Gate 2) cho feed den, quat, cua.";
      this.container.replaceChildren(
        placeholder("Đèn LED RGB", why),
        placeholder("Quạt làm mát", why),
        placeholder("Khóa cửa điện", why),
      );
      return;
    }
    if (!this.cards.light) {
      this.container.replaceChildren();
      this.cards = {
        light: new LightCard(state.colors),
        fan: new FanCard(),
        door: new DoorCard(state.door_relock),
      };
      for (const name in this.cards) {
        this.cards[name].confirmed = state.devices[name];
        this.cards[name].mount(this.container);
      }
    }
    for (const name in this.cards) this.cards[name].load(state.devices[name]);
  }

  onEvent(view) {
    const card = this.cards[view.device];
    if (card) card.onEvent(view);
  }

  setOffline(offline) {
    for (const name in this.cards) this.cards[name].setOffline(offline);
  }

  tick() {
    if (this.cards.door) this.cards.door.tick();
  }
}
