// Activate preloaded stylesheets without inline event handlers
['font-inter', 'font-orbitron', 'css-loc-modal'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.rel = 'stylesheet';
});

document.addEventListener("DOMContentLoaded", () => {
  const popupMenu = document.getElementById("popupMenu");
  const closeMenu = document.getElementById("closeMenu");

  // Guard: only run if these elements exist on the current page
  if (!popupMenu || !closeMenu) return;

  document.addEventListener("keydown", (e) => {
    if (e.key === "m") {
      popupMenu.classList.add("active");
    }
  });

  closeMenu.addEventListener("click", () => {
    popupMenu.classList.remove("active");
  });

  window.addEventListener("click", (e) => {
    if (e.target === popupMenu) {
      popupMenu.classList.remove("active");
    }
  });
});
