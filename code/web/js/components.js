// Trang xem thanh phan: bam toggle de doi trang thai.
for (const toggle of document.querySelectorAll(".toggle:not(:disabled)")) {
  toggle.addEventListener("click", () => {
    const on = toggle.getAttribute("aria-checked") === "true";
    toggle.setAttribute("aria-checked", on ? "false" : "true");
    toggle.setAttribute("aria-label", on ? "Tắt" : "Bật");
  });
}
