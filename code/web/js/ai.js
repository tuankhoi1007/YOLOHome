// Muc 03: nhan dien khuon mat va giong noi (Figma 11:796, 11:831).
// AI chay tren laptop Gateway, khong chay tren trinh duyet va khong chay tren board.
// Ban gia lap: nut "Mo phong" va nut micro goi /api/sim/*. Ban that: webcam laptop khi WEB_DATA=gateway va FACE_ENABLE=1. Giong noi van o Phase 7 (D8).

import { api } from "./api.js";
import { h } from "./dom.js";
import { clock, num } from "./format.js";

function scoreText(face) {
  if (!face || face.score === undefined || face.score === null) return num(face ? face.confidence : null) + "%";
  const prefix = face.metric === "lbph" ? "d=" : "s=";
  let text = prefix + Number(face.score).toFixed(2);
  if (face.threshold !== undefined && face.threshold !== null) text += " / ngưỡng " + Number(face.threshold).toFixed(2);
  return text;
}

function modelName(runtime) {
  if (!runtime || !runtime.model) return "chưa có model";
  if (runtime.model === "sface") return "YuNet + SFace";
  if (runtime.model === "lbph") return "YuNet + LBPH";
  return runtime.model;
}

function doorText(door) {
  if (!door) return "Cửa: chưa có trạng thái";
  return door.locked ? "Cửa: đang khóa" : "Cửa: đang mở";
}

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
    this.face = null;
    this.voice = null;
    this.features = null;
    this.faceCard = null;
    this.voiceCard = null;
    this.serverUp = true;
  }

  load(state) {
    this.features = state.features;
    this.face = state.face;
    this.voice = state.voice;
    this.commands = state.voice_commands;
    this.runtime = state.face_runtime || null;
    this.door = state.devices && state.devices.door ? state.devices.door : null;
    this.faceCard = this.features.face
      ? h("article", { class: "card ai-card", "aria-label": "Xác thực khuôn mặt" })
      : placeholder(
          "Xác thực khuôn mặt (FaceAI)",
          "Chạy WEB_DATA=gateway sau khi huấn luyện, hoặc để gateway.py chạy rồi tải lại trang.",
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

  onFace(face) {
    if (!face) {
      this.face = null;
    } else {
      if (face.runtime) this.runtime = face.runtime;
      if (face.ok === true || face.ok === false) this.face = face;
    }
    this.renderFace();
  }

  onDoor(door) {
    this.door = door;
    this.renderFace();
  }

  onVoice(voice) {
    this.voice = voice;
    this.renderVoice();
  }

  render() {
    this.renderFace();
    this.renderVoice();
  }

  async simulate(kind) {
    try {
      await api.simulate(kind);
    } catch (err) {
      this.notify({ title: "Không mô phỏng được", text: err.message, tone: "danger" });
    }
  }

  renderFace() {
    if (!this.features || !this.features.face) return;
    const face = this.face;
    const simulated = this.features.simulate;
    let view;
    if (!face) {
      view = h("span", null, "Chưa có lần nhận diện nào");
    } else {
      const label = face.ok
        ? "ID: " + face.name + " (" + scoreText(face) + ")"
        : "Không xác định (" + scoreText(face) + ")";
      view = h(
        "div",
        { class: "face-box" + (face.ok ? "" : " is-reject") },
        h("span", { class: "face-label" }, label),
        h("span", { class: "face-shape", "aria-hidden": "true" }),
        h("span", { class: "face-verdict" }, face.ok ? "Khớp thành viên" : "Từ chối"),
      );
    }
    let notice;
    const waiting = !simulated && this.runtime && !this.runtime.ready && this.runtime.message && !face;
    if (waiting) {
      notice = h(
        "div",
        { class: "ai-notice" },
        h("span", null, this.runtime.message),
        h("strong", { class: "tone-neutral" }, "Chưa sẵn sàng"),
      );
    } else if (!face) {
      const idle = simulated
        ? "Chưa có kết quả nhận diện."
        : "Đưa mặt vào webcam laptop. Cửa vẫn mở được bằng nút ở thẻ Khóa cửa.";
      notice = h("div", { class: "ai-notice" }, h("span", null, idle), h("span", { class: "tone-neutral" }, "–"));
    } else if (face.ok) {
      notice = h(
        "div",
        { class: "ai-notice" },
        h("span", null, "Nhận diện " + face.name + " lúc " + clock(face.at) + " (" + scoreText(face) + ") → đã gửi lệnh mở cửa."),
        h("strong", { class: "tone-ok" }, "Chấp nhận"),
      );
    } else {
      notice = h(
        "div",
        { class: "ai-notice" },
        h("span", null, "Không đủ ngưỡng lúc " + clock(face.at) + " (" + scoreText(face) + ") → cửa giữ nguyên. Vẫn mở được bằng tay ở thẻ Khóa cửa."),
        h("strong", { class: "tone-danger" }, "Từ chối"),
      );
    }
    const buttons = simulated
      ? h(
          "div",
          { class: "ai-foot" },
          h("button", { class: "sim-btn is-primary", type: "button", disabled: !this.serverUp, onclick: () => this.simulate("face_owner") }, "Mô phỏng quét chủ nhà"),
          h("button", { class: "sim-btn", type: "button", disabled: !this.serverUp, onclick: () => this.simulate("face_stranger") }, "Mô phỏng người lạ (từ chối)"),
        )
      : h(
          "div",
          { class: "ai-foot" },
          h("span", null, doorText(this.door)),
          h("span", null, "Model: " + modelName(this.runtime)),
        );
    let watermark = "Dữ liệu giả lập • chưa nối webcam";
    let camera = "Camera: giả lập";
    if (!simulated) {
      const ready = this.runtime && this.runtime.ready;
      watermark = ready ? "Camera laptop • " + modelName(this.runtime) : "Camera laptop • chưa sẵn sàng";
      camera = ready ? "Camera: laptop" : "Camera: chưa sẵn sàng";
    }
    const how = simulated
      ? "Suy luận trên laptop Gateway, không chạy trên chip Yolo:Bit."
      : "Suy luận trên laptop (" + modelName(this.runtime) + "), không chạy trên chip Yolo:Bit.";
    this.faceCard.replaceChildren(
      h(
        "div",
        { class: "ai-head" },
        h("div", null, h("h3", { class: "ai-title" }, "Xác Thực Khuôn Mặt (FaceAI)"), h("p", { class: "ai-sub" }, how)),
        h("span", { class: "cam-chip" }, camera),
      ),
      h(
        "div",
        { class: "camera", role: "img", "aria-label": face ? (face.ok ? "Khớp thành viên" : "Từ chối") : "Chưa có kết quả" },
        view,
        h("span", { class: "camera-watermark" }, watermark),
      ),
      notice,
      buttons,
    );
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
