// Tao phan tu HTML bang textContent, khong dung innerHTML voi du lieu (tranh chen ma).

// h("span", { class: "chip" }, "Chu") -> <span class="chip">Chu</span>
// style la object: { style: { background: "#fff", "--fill": "40%" } }
export function h(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const name in attrs || {}) {
    const value = attrs[name];
    if (value === null || value === undefined || value === false) continue;
    if (name === "style") {
      // CSP chan thuoc tinh style="..."; dat qua node.style thi duoc phep
      for (const prop in value) node.style.setProperty(prop, value[prop]);
    } else if (name.startsWith("on") && typeof value === "function") {
      node.addEventListener(name.slice(2), value);
    } else if (value === true) {
      node.setAttribute(name, "");
    } else {
      node.setAttribute(name, value);
    }
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

export function byId(id) {
  return document.getElementById(id);
}

// Doi noi dung chu ma khong dung toi phan tu khac
export function setText(node, text) {
  if (node.textContent !== text) node.textContent = text;
}
