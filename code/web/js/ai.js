// Muc 03: nhan dien khuon mat va giong noi (Figma 11:796, 11:831).
// AI chay tren laptop Gateway, khong chay tren trinh duyet va khong chay tren board.
// Ban gia lap: nut "Mo phong" va nut micro goi /api/sim/*. Ban that lam o Phase 6 (D7) va Phase 7 (D8).

import { api } from "./api.js";
import { h } from "./dom.js";
import { clock, num } from "./format.js";

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
    this.faceCard = this.features.face
      ? h("article", { class: "card ai-card", "aria-label": "Xác thực khuôn mặt" })
      : placeholder("Xác thực khuôn mặt (FaceAI)", "Làm ở Phase 6 (D7): webcam laptop, đúng thành viên thì mở cửa.");
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
    this.face = face;
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
    let view;
    if (!face) {
      view = h("span", null, "Chưa có lần nhận diện nào");
    } else {
      const label = face.ok ? "ID: " + face.name + " (" + num(face.confidence) + "%)" : "Không xác định (" + num(face.confidence) + "%)";
      view = h(
        "div",
        { class: "face-box" + (face.ok ? "" : " is-reject") },
        h("span", { class: "face-label" }, label),
        h("span", { class: "face-shape", "aria-hidden": "true" }),
        h("span", { class: "face-verdict" }, face.ok ? "Khớp thành viên" : "Từ chối"),
      );
    }
    let notice;
    if (!face) {
      notice = h("div", { class: "ai-notice" }, h("span", null, "Chưa có kết quả nhận diện."), h("span", { class: "tone-neutral" }, "–"));
    } else if (face.ok) {
      notice = h(
        "div",
        { class: "ai-notice" },
        h("span", null, "Nhận diện hợp lệ lúc " + clock(face.at) + " → đã gửi lệnh mở cửa."),
        h("strong", { class: "tone-ok" }, "Chấp nhận"),
      );
    } else {
      notice = h(
        "div",
        { class: "ai-notice" },
        h("span", null, "Khuôn mặt không khớp lúc " + clock(face.at) + " → cửa giữ nguyên. Vẫn mở được bằng tay ở thẻ Khóa cửa."),
        h("strong", { class: "tone-danger" }, "Từ chối"),
      );
    }
    const buttons = this.features.simulate
      ? h(
          "div",
          { class: "ai-foot" },
          h("button", { class: "sim-btn is-primary", type: "button", disabled: !this.serverUp, onclick: () => this.simulate("face_owner") }, "Mô phỏng quét chủ nhà"),
          h("button", { class: "sim-btn", type: "button", disabled: !this.serverUp, onclick: () => this.simulate("face_stranger") }, "Mô phỏng người lạ (từ chối)"),
        )
      : null;
    this.faceCard.replaceChildren(
      h(
        "div",
        { class: "ai-head" },
        h(
          "div",
          null,
          h("h3", { class: "ai-title" }, "Xác Thực Khuôn Mặt (FaceAI)"),
          h("p", { class: "ai-sub" }, "Suy luận trên laptop Gateway, không chạy trên chip Yolo:Bit."),
        ),
        h("span", { class: "cam-chip" }, this.features.simulate ? "Camera: giả lập" : "Camera: laptop"),
      ),
      h(
        "div",
        { class: "camera", role: "img", "aria-label": face ? (face.ok ? "Khớp thành viên" : "Từ chối") : "Chưa có kết quả" },
        view,
        h("span", { class: "camera-watermark" }, "Dữ liệu giả lập • chưa nối webcam (D7)"),
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
