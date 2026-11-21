// Muc 03: cho khuon mat (Phase 6, ban trong nhom lam) va giong noi (Figma 11:796, 11:831).
// Giong noi van o Phase 7 (D8). Nut micro goi /api/sim/voice.

import { api } from "./api.js";
import { h } from "./dom.js";
import { clock } from "./format.js";

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
    this.features = null;
    this.faceCard = null;
    this.voiceCard = null;
    this.serverUp = true;
  }

  load(state) {
    this.features = state.features;
    this.voice = state.voice;
    this.commands = state.voice_commands;
    this.faceCard = placeholder(
      "Xác thực khuôn mặt (FaceAI)",
      "Làm ở Phase 6. Cửa vẫn mở được bằng nút Khóa cửa.",
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

  render() {
    this.renderVoice();
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
