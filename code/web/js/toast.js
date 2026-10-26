// Thong bao goc phai (Figma 11:1014). Tu tat sau 6 giay, bam de tat ngay.

import { byId, h } from "./dom.js";

const SHOW_MS = 6000;
const MAX = 3;

export function toast({ title, text, tone }) {
  const box = byId("toasts");
  if (!box) return;
  const ok = tone === "ok";
  const node = h(
    "div",
    { class: "toast" + (ok ? " toast-ok" : ""), role: ok ? "status" : "alert" },
    h("span", { class: "toast-icon", "aria-hidden": "true" }, ok ? "✓" : "⚠"),
    h("div", { class: "toast-body" }, h("p", { class: "toast-title" }, title), h("p", { class: "toast-text" }, text)),
    h("span", { class: "toast-time" }, "vừa xong"),
  );
  node.addEventListener("click", () => node.remove());
  box.prepend(node);
  while (box.children.length > MAX) box.lastElementChild.remove();
  setTimeout(() => node.remove(), SHOW_MS);
}
