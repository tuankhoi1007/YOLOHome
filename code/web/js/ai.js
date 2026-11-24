// Muc 03: khuon mat (nut Quet mat, /api/face/scan) va giong noi (Figma 11:796, 11:831).
// Giong noi van o Phase 7 (D8). Nut micro goi /api/sim/voice.

import { api } from "./api.js";
import { byId, h } from "./dom.js";
import { clock } from "./format.js";

const ENROLL_STEPS = [
  "Nhìn thẳng vào webcam",
  "Quay đầu sang trái một chút",
  "Quay đầu sang phải một chút",
  "Lùi xa, nhìn thẳng",
  "Đổi kính rồi nhìn thẳng. Không đeo kính thì bấm Bỏ qua bước",
];

function placeholder(title, why) {
  return h("article", { class: "card placeholder-card" }, h("strong", null, title), h("span", null, why));
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export class Ai {
  constructor(container, notify) {
    this.container = container;
    this.notify = notify;
    this.voice = null;
    this.face = null;
    this.features = null;
    this.faceCard = null;
    this.voiceCard = null;
    this.serverUp = true;
    this.scanning = false;
    this.scanTimer = null;
    this.enrolling = false;
    this.enrollTimer = null;
    this.enrollNote = "";
    this.cameraDismissed = false;
    this.dialog = byId("face-dialog");
    this.enrollDialog = byId("enroll-dialog");
    byId("face-dialog-close").addEventListener("click", () => this.dismissCamera());
    this.dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.dismissCamera();
    });
    byId("enroll-form").addEventListener("submit", (event) => this.submitEnroll(event));
    byId("enroll-dialog-close").addEventListener("click", () => this.closeEnroll());
    byId("enroll-cancel").addEventListener("click", () => this.closeEnroll());
    this.enrollDialog.addEventListener("close", () => {
      byId("enroll-password").value = "";
      byId("enroll-start").disabled = false;
    });
  }

  load(state) {
    this.features = state.features;
    this.voice = state.voice;
    this.face = state.face;
    this.commands = state.voice_commands;
    this.scanning = false;
    clearTimeout(this.scanTimer);
    this.faceCard = this.features.face
      ? h("article", { class: "card ai-card", "aria-label": "Xác thực khuôn mặt" })
      : placeholder(
          "Xác thực khuôn mặt (FaceAI)",
          "Chạy web với WEB_DATA=gateway và FACE_ENABLE=1. Cửa vẫn mở được bằng nút Khóa cửa.",
        );
    this.voiceCard = this.features.voice
      ? h("article", { class: "card ai-card", "aria-label": "Điều khiển giọng nói" })
      : placeholder("Điều khiển giọng nói", "Làm ở Phase 7 (D8): micro laptop, bộ lệnh cố định cho đèn và quạt.");
    this.container.replaceChildren(this.faceCard, this.voiceCard);
    this.render();
  }

  setServerUp(up) {
    this.serverUp = up;
    this.render();
  }

  onVoice(voice) {
    this.voice = voice;
    this.renderVoice();
  }

  onEnroll(result) {
    this.enrolling = false;
    clearTimeout(this.enrollTimer);
    this.enrollNote = result.detail || "";
    this.renderFace();
    this.notify({
      title: result.ok ? "Đã đăng ký " + (result.name || "") : "Không lưu mẫu",
      text: result.detail || "",
      tone: result.ok ? "ok" : "danger",
    });
  }

  onFace(face) {
    this.face = face;
    this.scanning = false;
    clearTimeout(this.scanTimer);
    this.renderFace();
    if (face.ok) {
      const opened = !face.detail || face.detail === "Cửa đang mở.";
      this.notify({
        title: "Đã nhận " + (face.name || "thành viên"),
        text: opened ? "Cửa đang mở." : face.detail,
        tone: opened ? "ok" : "danger",
      });
    } else {
      this.notify({ title: "Không mở cửa", text: face.detail || "Không nhận diện được. Vẫn mở được bằng nút Khóa cửa.", tone: "danger" });
    }
  }

  render() {
    this.renderFace();
    this.renderVoice();
  }

  async scan() {
    this.scanning = true;
    this.cameraDismissed = false;
    this.renderFace();
    try {
      await api.scanFace();
      clearTimeout(this.scanTimer);
      // Quet toi da vai giay. Het gio ma khong co su kien thi mo nut lai.
      this.scanTimer = setTimeout(() => {
        if (!this.scanning) return;
        this.scanning = false;
        this.renderFace();
        this.notify({ title: "Không có kết quả", text: "Lần quét không trả lời. Bấm Quét mặt lại.", tone: "danger" });
      }, 15000);
    } catch (err) {
      this.scanning = false;
      clearTimeout(this.scanTimer);
      this.renderFace();
      this.notify({ title: "Không quét được", text: err.message, tone: "danger" });
    }
  }

  async faceControl(action) {
    try {
      await api.faceControl(action);
    } catch (err) {
      this.notify({ title: "Không điều khiển được", text: err.message, tone: "danger" });
    }
  }

  openEnroll() {
    if (!this.serverUp || this.scanning || this.enrolling) return;
    this.showEnrollError("");
    byId("enroll-name").value = "";
    byId("enroll-password").value = "";
    if (!this.enrollDialog.open) this.enrollDialog.showModal();
    byId("enroll-name").focus();
  }

  closeEnroll() {
    if (this.enrollDialog.open) this.enrollDialog.close();
  }

  showEnrollError(text) {
    const node = byId("enroll-error");
    node.hidden = !text;
    node.textContent = text || "";
  }

  async submitEnroll(event) {
    event.preventDefault();
    const name = byId("enroll-name").value.trim();
    const passwordNode = byId("enroll-password");
    const password = passwordNode.value;
    passwordNode.value = "";
    if (!name || !password) {
      this.showEnrollError("Nhập tên và mật khẩu chủ nhà.");
      return;
    }
    const start = byId("enroll-start");
    start.disabled = true;
    this.showEnrollError("");
    try {
      await api.enrollFace(name, password);
    } catch (err) {
      start.disabled = false;
      this.showEnrollError(err.message);
      return;
    }
    this.closeEnroll();
    this.beginEnroll();
  }

  beginEnroll() {
    this.enrolling = true;
    this.cameraDismissed = false;
    this.enrollNote = "Đang đăng ký. Làm lần lượt các bước trong cửa sổ.";
    this.renderFace();
    clearTimeout(this.enrollTimer);
    this.enrollTimer = setTimeout(() => {
      if (!this.enrolling) return;
      this.enrolling = false;
      this.enrollNote = "";
      this.renderFace();
      this.notify({ title: "Chưa có kết quả đăng ký", text: "Nếu cửa sổ webcam đã đóng, bấm Đăng ký mới lại.", tone: "danger" });
    }, 150000);
  }

  dismissCamera() {
    this.cameraDismissed = true;
    if (this.enrolling) this.faceControl("cancel");
    this.stopVideo();
    if (this.dialog.open) this.dialog.close();
    this.renderFace();
  }

  stopVideo() {
    const camera = byId("face-dialog-camera");
    if (camera) camera.replaceChildren();
  }

  syncDialog() {
    const busy = this.scanning || this.enrolling;
    if (!busy || this.cameraDismissed) {
      this.stopVideo();
      if (this.dialog.open) this.dialog.close();
      return;
    }
    byId("face-dialog-kicker").textContent = this.enrolling ? "Đăng ký khuôn mặt" : "Quét mặt";
    byId("face-dialog-title").textContent = this.enrolling ? "Làm lần lượt các bước" : "Nhìn thẳng vào webcam";
    byId("face-dialog-note").textContent = this.enrolling
      ? "Làm lần lượt các bước bên cạnh. Chữ trên hình là bước đang chụp. Không đeo kính thì bấm Bỏ qua bước ở bước cuối."
      : "Nhìn thẳng vào webcam. Đúng người thì cửa mở.";
    const steps = byId("face-dialog-steps");
    steps.hidden = !this.enrolling;
    steps.replaceChildren(...ENROLL_STEPS.map((text) => h("li", null, text)));
    const actions = byId("face-dialog-actions");
    actions.replaceChildren(
      ...(this.enrolling
        ? [
            h("button", { class: "btn-outline", type: "button", onclick: () => this.faceControl("skip") }, "Bỏ qua bước"),
            h("button", { class: "btn-outline", type: "button", onclick: () => this.faceControl("cancel") }, "Hủy"),
          ]
        : []),
    );
    const camera = byId("face-dialog-camera");
    if (!camera.querySelector("img")) {
      camera.replaceChildren(h("img", { class: "camera-live", src: "/api/face/video", alt: "Webcam laptop" }));
    }
    if (!this.dialog.open) this.dialog.showModal();
  }

  renderFace() {
    if (!this.features || !this.features.face) return;
    const face = this.face;
    const scanning = this.scanning;
    const enrolling = this.enrolling;
    const busy = scanning || enrolling;
    this.syncDialog();
    let status = "Quét mặt để mở cửa, hoặc đăng ký thành viên mới.";
    if (enrolling) status = this.enrollNote;
    else if (busy) status = this.cameraDismissed ? "Đã đóng cửa sổ webcam." : "Webcam đang mở trong cửa sổ.";
    else if (face) {
      const opened = face.ok && (!face.detail || face.detail === "Cửa đang mở.");
      status = opened
        ? (face.name || "Thành viên") + " · Cửa đang mở."
        : (face.detail || "Không nhận ra. Cửa vẫn đóng.");
    }
    const chip = enrolling ? "Đang đăng ký" : scanning ? "Đang quét" : this.serverUp ? "Sẵn sàng" : "Mất kết nối";
    this.faceCard.replaceChildren(
      h(
        "div",
        { class: "ai-head" },
        h(
          "div",
          null,
          h("h3", { class: "ai-title" }, "Xác Thực Khuôn Mặt"),
          h("p", { class: "ai-sub" }, "Đúng người thì cửa mở."),
        ),
        h("span", { class: "cam-chip" }, chip),
      ),
      h("p", { class: "face-status", "aria-live": "polite" }, status),
      h(
        "div",
        { class: "face-actions" },
        h(
          "button",
          {
            class: "sim-btn is-primary",
            type: "button",
            disabled: !this.serverUp || busy,
            onclick: () => this.scan(),
          },
          scanning ? "Đang quét…" : "Quét mặt mở cửa",
        ),
        h(
          "button",
          {
            class: "sim-btn",
            type: "button",
            disabled: !this.serverUp || busy,
            onclick: () => this.openEnroll(),
          },
          enrolling ? "Đang đăng ký…" : "Đăng ký mới",
        ),
      ),
      h(
        "div",
        { class: "ai-foot" },
        h("span", null, "Cửa vẫn mở được bằng nút Khóa cửa"),
      ),
    );
  }

  async simulate(kind) {
    try {
      await api.simulate(kind);
    } catch (err) {
      this.notify({ title: "Không mô phỏng được", text: err.message, tone: "danger" });
    }
  }

  renderVoice() {
    if (!this.features || !this.features.voice) return;
    const voice = this.voice;
    const mic = h(
      "button",
      {
        class: "mic-btn",
        type: "button",
        "aria-label": "Mô phỏng một câu lệnh giọng nói",
        disabled: !this.serverUp || !this.features.simulate,
        onclick: () => this.simulate("voice"),
      },
      h("img", { src: "img/icon-mic.svg", width: 28, height: 28, alt: "" }),
    );
    this.voiceCard.replaceChildren(
      h(
        "div",
        { class: "ai-head" },
        h(
          "div",
          null,
          h("h3", { class: "ai-title" }, "Điều Khiển Giọng Nói"),
          h("p", { class: "ai-sub" }, "Khẩu lệnh tiếng Việt qua micro laptop (Gateway)."),
        ),
        h("span", { class: "mic-pill" }, h("span", { class: "dot " + (this.serverUp ? "is-on" : "is-off") }), this.serverUp ? "Sẵn sàng" : "Mất kết nối"),
      ),
      h(
        "div",
        { class: "voice-box" },
        mic,
        h("p", { class: "voice-hint" }, "Bấm micro để mô phỏng một câu lệnh (micro thật ở Gateway)"),
        h("p", { class: "voice-said", "aria-live": "polite" }, voice ? "“" + capitalize(voice.text) + "”" : ""),
        voice ? h("p", { class: "voice-feedback" }, "Hệ thống: đã nhận lệnh “" + voice.text + "” lúc " + clock(voice.at)) : null,
      ),
      h(
        "div",
        { class: "voice-commands" },
        h("p", { class: "caps device-control-label" }, "Tập lệnh cố định được hỗ trợ:"),
        h(
          "ul",
          { class: "voice-commands-list", role: "list" },
          this.commands.map((text) => h("li", { class: "voice-command" }, "• “" + text + "”")),
        ),
      ),
      h("div", { class: "ai-foot" }, h("span", null, "Ngôn ngữ: Tiếng Việt (vi-VN)"), h("span", null, "Bộ nhận dạng: chưa chốt (D8)")),
    );
  }
}
