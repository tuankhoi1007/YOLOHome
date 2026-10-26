// Trang nhat ky (Figma 7:97): loc theo loai, ngay, chu; 10 dong mot trang.
// Su kien moi den qua SSE thi tai lai trang dang xem.

import { api, listen } from "./api.js";
import { byId, h } from "./dom.js";
import { logTable } from "./logview.js";

const PILLS = [
  ["all", "Tất cả"],
  ["sensor", "Cảm biến"],
  ["control", "Điều khiển thiết bị"],
  ["alert", "Cảnh báo vượt ngưỡng"],
  ["face", "Nhận diện FaceAI"],
  ["voice", "Giọng nói"],
];

const filters = { type: "all", date: "", q: "", page: 1 };
let reloadTimer = null;

const pills = byId("log-pills");
pills.replaceChildren(
  ...PILLS.map(([kind, label]) =>
    h("button", { class: "pill", type: "button", role: "tab", "data-kind": kind, "aria-selected": kind === filters.type ? "true" : "false", onclick: () => selectType(kind) }, label),
  ),
);

function selectType(kind) {
  filters.type = kind;
  filters.page = 1;
  for (const pill of pills.children) pill.setAttribute("aria-selected", pill.dataset.kind === kind ? "true" : "false");
  load();
}

// Danh sach so trang: 1 2 3 … 13, quanh trang hien tai
function pageNumbers(page, pages) {
  const wanted = new Set([1, pages, page - 1, page, page + 1]);
  if (page <= 3) [2, 3].forEach((n) => wanted.add(n));
  const list = [...wanted].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  const out = [];
  list.forEach((n, index) => {
    if (index > 0 && n - list[index - 1] > 1) out.push("…");
    out.push(n);
  });
  return out;
}

function renderPager(data) {
  const first = data.total === 0 ? 0 : (data.page - 1) * data.page_size + 1;
  const last = Math.min(data.total, data.page * data.page_size);
  byId("log-count").replaceChildren("Hiển thị ", h("strong", null, first + "–" + last), " của ", h("strong", null, String(data.total)), " bản ghi");
  const go = (page) => {
    filters.page = page;
    load();
  };
  const buttons = [
    h("button", { class: "page-btn", type: "button", "aria-label": "Trang trước", disabled: data.page <= 1, onclick: () => go(data.page - 1) }, h("img", { src: "img/icon-chevron-left.svg", width: 16, height: 16, alt: "" })),
  ];
  for (const item of pageNumbers(data.page, data.pages)) {
    if (item === "…") {
      buttons.push(h("span", { class: "page-gap" }, "…"));
    } else {
      buttons.push(h("button", { class: "page-btn", type: "button", "aria-current": item === data.page ? "page" : null, onclick: () => go(item) }, String(item)));
    }
  }
  buttons.push(h("button", { class: "page-btn", type: "button", "aria-label": "Trang sau", disabled: data.page >= data.pages, onclick: () => go(data.page + 1) }, h("img", { src: "img/icon-chevron-right.svg", width: 16, height: 16, alt: "" })));
  byId("log-pager").replaceChildren(...buttons);
}

async function load() {
  try {
    const data = await api.log(filters);
    filters.page = data.page;
    byId("log-table").replaceChildren(logTable(data.items, "page"));
    renderPager(data);
  } catch (err) {
    byId("log-table").replaceChildren(h("p", { class: "table-empty" }, "Không tải được nhật ký: " + err.message));
  }
}

function loadSoon() {
  clearTimeout(reloadTimer);
  reloadTimer = setTimeout(load, 300);
}

byId("log-date").addEventListener("change", (event) => {
  filters.date = event.target.value;
  filters.page = 1;
  load();
});

byId("log-search").addEventListener("input", (event) => {
  filters.q = event.target.value;
  filters.page = 1;
  loadSoon();
});

byId("logout").addEventListener("click", async () => {
  try {
    await api.logout();
  } finally {
    location.href = "/login.html";
  }
});

load();

listen({
  // Noi lai sau khi mat ket noi: tai lai cho du
  open: load,
  // Chi tai lai khi dang o trang 1, de khong lam nhay trang nguoi dung dang doc
  log: () => {
    if (filters.page === 1) loadSoon();
  },
});
