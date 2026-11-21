// Bang nhat ky dung chung cho dashboard (Figma 11:893) va trang nhat ky (7:97).

import { api } from "./api.js";
import { h } from "./dom.js";
import { clock, logType } from "./format.js";

const COLUMNS = ["Thời gian", "Phân loại", "Thiết bị / Nguồn", "Chi tiết sự kiện", "Trạng thái"];

// variant "dashboard": chip loai + chu trang thai mau. "page": chu loai dam + nhan trang thai in hoa.
export function logTable(items, variant) {
  const head = h("thead", null, h("tr", null, COLUMNS.map((name, index) => h("th", { class: index === 4 ? "col-status" : null, scope: "col" }, name))));
  if (!items.length) {
    return h("table", { class: "table" }, head, h("tbody", null, h("tr", null, h("td", { class: "table-empty", colspan: 5 }, "Không có sự kiện nào khớp bộ lọc."))));
  }
  const rows = items.map((entry) => {
    const type = logType(entry.type);
    let typeCell;
    let statusCell;
    if (variant === "page") {
      const danger = entry.tone === "danger";
      typeCell = h("span", { class: "log-type" + (danger ? " tone-danger" : "") }, type.label);
      statusCell = h("span", { class: "status-tag status-" + entry.tone }, entry.status);
    } else {
      typeCell = h("span", { class: "chip " + type.chip }, type.label);
      statusCell = h("span", { class: "tone-" + entry.tone }, entry.status);
    }
    return h(
      "tr",
      null,
      h("td", { class: "col-time" }, clock(entry.at)),
      h("td", null, typeCell),
      h("td", { class: "col-source" }, entry.source),
      h("td", null, entry.detail),
      h("td", { class: "col-status" }, statusCell),
    );
  });
  return h("table", { class: "table table-" + variant }, head, h("tbody", null, rows));
}

// Tab tren dashboard (11:879)
const TABS = [
  ["all", "Tất cả"],
  ["sensor", "Cảm biến"],
  ["control", "Điều khiển"],
  ["alert", "Cảnh báo"],
  ["face", "Khuôn mặt"],
];

const RECENT = 5;

// Muc 04 tren dashboard: 5 su kien moi nhat, cap nhat ngay khi co su kien "log"
export class RecentLog {
  constructor(tabs, container) {
    this.tabs = tabs;
    this.container = container;
    this.kind = "all";
    this.items = [];
    this.enabled = true;
    this.tabs.replaceChildren(
      ...TABS.map(([kind, label]) =>
        h("button", { class: "tab", type: "button", role: "tab", "data-kind": kind, "aria-selected": kind === this.kind ? "true" : "false", onclick: () => this.select(kind) }, label),
      ),
    );
  }

  select(kind) {
    this.kind = kind;
    for (const tab of this.tabs.children) {
      tab.setAttribute("aria-selected", tab.dataset.kind === kind ? "true" : "false");
    }
    this.reload();
  }

  async reload() {
    try {
      const data = await api.log({ type: this.kind, page: 1 });
      this.items = data.items.slice(0, RECENT);
      this.render();
    } catch (err) {
      this.container.replaceChildren(h("p", { class: "table-empty" }, "Không tải được nhật ký: " + err.message));
    }
  }

  onEntry(entry) {
    if (this.kind !== "all" && entry.type !== this.kind) return;
    this.items = [entry, ...this.items].slice(0, RECENT);
    this.render();
  }

  render() {
    this.container.replaceChildren(logTable(this.items, "dashboard"));
  }
}
