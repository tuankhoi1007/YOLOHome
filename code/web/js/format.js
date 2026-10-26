// Dinh dang so, gio va nhan hien tren giao dien.

export function num(value) {
  if (value === null || value === undefined) return "–";
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

// Gio:phut:giay theo gio cua trinh duyet
export function clock(epochSeconds) {
  return new Date(epochSeconds * 1000).toLocaleTimeString("vi-VN", { hour12: false });
}

export function ago(seconds) {
  if (seconds < 2) return "vừa xong";
  if (seconds < 60) return Math.round(seconds) + " giây trước";
  if (seconds < 3600) return Math.round(seconds / 60) + " phút trước";
  return Math.round(seconds / 3600) + " giờ trước";
}

// Loai nhat ky -> chu va mau chip (Figma 11:872, 7:97)
export const LOG_TYPES = {
  sensor: { label: "Cảm biến", chip: "" },
  control: { label: "Điều khiển", chip: "chip-warn" },
  alert: { label: "Cảnh báo", chip: "chip-danger" },
  face: { label: "Nhận diện", chip: "" },
  voice: { label: "Giọng nói", chip: "" },
  system: { label: "Hệ thống", chip: "" },
};

export function logType(type) {
  return LOG_TYPES[type] || { label: type, chip: "" };
}
