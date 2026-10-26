// Modal cau hinh nguong (Figma 28:1829). Khoang hop le giong module2.Thresholds.

import { api } from "./api.js";
import { byId } from "./dom.js";

const LIMITS = {
  temp_max: [0, 80, "Ngưỡng nhiệt độ phải từ 0 đến 80"],
  humid_max: [0, 100, "Ngưỡng độ ẩm phải từ 0 đến 100"],
  light_min: [0, 100, "Ngưỡng ánh sáng phải từ 0 đến 100"],
};

// getThresholds(): nguong hien tai; canWrite(): web duoc ghi nguong khong;
// onSaved(values): sau khi may chu luu xong
export function setupThresholds(getThresholds, canWrite, onSaved) {
  const dialog = byId("thresholds-dialog");
  const form = byId("thresholds-form");
  const error = byId("thresholds-error");
  const save = byId("thresholds-save");

  function showError(message) {
    error.textContent = message;
    error.hidden = false;
  }

  function open() {
    const current = getThresholds();
    const writable = canWrite();
    for (const name in LIMITS) {
      form.elements[name].value = current[name];
      form.elements[name].disabled = !writable;
    }
    error.hidden = true;
    save.hidden = !writable;
    save.disabled = false;
    save.textContent = "Lưu cấu hình";
    if (!writable) {
      // Ban that: web chua duoc ghi feed nguong-* cho den khi PROTOCOL.md cho phep
      showError("Chỉ xem: đổi ngưỡng trên dashboard Adafruit (web chưa được ghi ngưỡng).");
    }
    dialog.showModal();
    if (writable) form.elements.temp_max.focus();
  }

  byId("open-thresholds").addEventListener("click", open);
  byId("thresholds-close").addEventListener("click", () => dialog.close());
  byId("thresholds-cancel").addEventListener("click", () => dialog.close());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    const values = {};
    for (const name in LIMITS) {
      const [low, high, message] = LIMITS[name];
      const raw = form.elements[name].value.trim();
      const value = Number(raw);
      if (raw === "" || !Number.isFinite(value) || value < low || value > high) {
        showError(message);
        form.elements[name].focus();
        return;
      }
      values[name] = value;
    }
    save.disabled = true;
    save.textContent = "Đang lưu…";
    try {
      const saved = await api.setThresholds(values);
      dialog.close();
      onSaved(saved);
    } catch (err) {
      showError(err.message);
      save.disabled = false;
      save.textContent = "Lưu cấu hình";
    }
  });

  return { open };
}
