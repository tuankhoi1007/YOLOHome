// Moi trang lay du lieu qua file nay, khong goi fetch hay EventSource o noi khac.
// Doi tu du lieu gia lap sang du lieu that (ROADMAP 5.6) chi doi may chu, file nay giu nguyen.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function goToLogin() {
  if (location.pathname !== "/login.html") {
    location.href = "/login.html";
  }
}

async function request(method, path, body) {
  const options = { method: method, headers: {}, credentials: "same-origin" };
  if (body !== undefined) {
    // May chu chi nhan application/json (chong form gia tu trang khac)
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (err) {
    throw new ApiError(0, "Không kết nối được máy chủ web");
  }
  let data = null;
  try {
    data = await response.json();
  } catch (err) {
    data = null;
  }
  if (response.status === 401 && path !== "/api/login") {
    goToLogin();
  }
  if (!response.ok) {
    const message = data && data.error ? data.error : "Lỗi " + response.status;
    throw new ApiError(response.status, message);
  }
  return data;
}

export const api = {
  state: () => request("GET", "/api/state"),
  log: (filters) => request("GET", "/api/log?" + new URLSearchParams(filters)),
  login: (password) => request("POST", "/api/login", { password: password }),
  logout: () => request("POST", "/api/logout", {}),
  setThresholds: (values) => request("POST", "/api/thresholds", values),
  // Tra ve ngay khi lenh da gui; xac nhan cua thiet bi den sau qua su kien "device"
  command: (device, body) => request("POST", "/api/devices/" + device, body),
  simulate: (kind) => request("POST", "/api/sim/" + kind, {}),
};

const EVENT_KINDS = ["sensors", "alert", "thresholds", "device", "gateway", "face", "voice", "log"];

// Nghe su kien SSE. handlers co the co: sensors, alert, ..., open (vua noi, nen tai lai api.state()),
// lost (mat ket noi toi may chu web). Tra ve ham de dung nghe.
export function listen(handlers) {
  let source = null;
  let retry = null;

  function connect() {
    source = new EventSource("/api/events");
    source.onopen = () => {
      if (handlers.open) handlers.open();
    };
    source.onerror = () => {
      if (handlers.lost) handlers.lost();
      // Mat mang thi EventSource tu noi lai. May chu tra 401/404 thi no dong han:
      // hoi api.state() (401 se chuyen ve trang dang nhap) roi tu noi lai sau 3 giay.
      if (source.readyState === EventSource.CLOSED) {
        source = null;
        clearTimeout(retry);
        retry = setTimeout(async () => {
          try {
            await api.state();
          } catch (err) {
            // da xu ly trong request()
          }
          connect();
        }, 3000);
      }
    };
    for (const kind of EVENT_KINDS) {
      source.addEventListener(kind, (event) => {
        if (handlers[kind]) handlers[kind](JSON.parse(event.data));
      });
    }
  }

  connect();
  return () => {
    clearTimeout(retry);
    if (source) source.close();
  };
}
