document.addEventListener("DOMContentLoaded", () => {
  const messages = document.querySelectorAll(".flash-message");

  messages.forEach((msg, index) => {
    // ===== ENTRY ANIMATION =====
    msg.style.opacity = "0";
    msg.style.transform = "translateY(-10px)";

    setTimeout(() => {
      msg.style.transition = "all 0.4s ease";
      msg.style.opacity = "1";
      msg.style.transform = "translateY(0)";
    }, index * 150); // stagger effect

    // ===== AUTO REMOVE =====
    setTimeout(
      () => {
        removeMessage(msg);
      },
      4000 + index * 200,
    ); // delay per message

    // ===== CLOSE BUTTON =====
    const closeBtn = msg.querySelector(".close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        removeMessage(msg);
      });
    }
  });

  function removeMessage(msg) {
    msg.style.transition = "all 0.3s ease";
    msg.style.opacity = "0";
    msg.style.transform = "translateY(-10px)";

    setTimeout(() => {
      msg.remove();
    }, 300);
  }
});
