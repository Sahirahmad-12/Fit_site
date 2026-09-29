document.addEventListener("DOMContentLoaded", () => {
  const menuBtn = document.getElementById("menuBtn");
  const popupMenu = document.getElementById("popupMenu");
  const closeBtn = document.getElementById("closeMenu");
  const links = popupMenu.querySelectorAll("a");

  // =====================
  // OPEN MENU
  // =====================
  function openMenu() {
    popupMenu.classList.remove("opacity-0", "pointer-events-none");
    popupMenu.classList.add("opacity-100", "pointer-events-auto");
  }

  // =====================
  // CLOSE MENU
  // =====================
  function closeMenu() {
    popupMenu.classList.add("opacity-0", "pointer-events-none");
    popupMenu.classList.remove("opacity-100", "pointer-events-auto");
  }

  menuBtn.addEventListener("click", openMenu);
  closeBtn.addEventListener("click", closeMenu);

  links.forEach((link) => {
    link.addEventListener("click", closeMenu);
  });
});
