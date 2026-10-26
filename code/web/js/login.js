// Dang nhap bang mat khau chung (D10). Dung thi may chu dat cookie, chuyen ve dashboard.
import { api } from "./api.js";

const form = document.getElementById("login-form");
const input = document.getElementById("password");
const error = document.getElementById("login-error");
const errorText = document.getElementById("login-error-text");
const submit = document.getElementById("login-submit");
const eye = document.getElementById("toggle-password");

function showError(message) {
  errorText.textContent = message;
  error.hidden = false;
}

eye.addEventListener("click", () => {
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  eye.setAttribute("aria-pressed", show ? "true" : "false");
  eye.setAttribute("aria-label", show ? "Ẩn mật khẩu" : "Hiện mật khẩu");
  input.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.hidden = true;
  if (!input.value) {
    showError("Nhập mật khẩu");
    input.focus();
    return;
  }
  submit.setAttribute("aria-busy", "true");
  submit.disabled = true;
  submit.textContent = "Đang đăng nhập…";
  try {
    await api.login(input.value);
    location.href = "/";
  } catch (err) {
    showError(err.message);
    input.select();
    submit.removeAttribute("aria-busy");
    submit.disabled = false;
    submit.textContent = "Đăng nhập";
  }
});
