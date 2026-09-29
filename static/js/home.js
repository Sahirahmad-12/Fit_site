document.addEventListener("DOMContentLoaded", () => {
  /* =========================
     RESET: no card open on load
  ========================= */
  document.querySelectorAll(".feature-card, .pricing-card").forEach((c) => {
    c.classList.remove("active");
  });

  /* =========================
     CARD CLICK HANDLERS
  ========================= */
  document.querySelectorAll(".feature-card").forEach((card) => {
    card.addEventListener("click", function () {
      toggleFeature(this);
    });
  });

  document.querySelectorAll(".pricing-card").forEach((card) => {
    card.addEventListener("click", function () {
      togglePricing(this);
    });
  });

  /* =========================
     MOBILE MENU
  ========================= */
  const menuBtn = document.getElementById("menuBtn");
  const mobileMenu = document.getElementById("mobileMenu");
  const closeMenu = document.getElementById("closeMenu");

  if (menuBtn && mobileMenu && closeMenu) {
    mobileMenu.classList.remove("active");

    const closeMobileMenu = () => {
      mobileMenu.classList.remove("active");
      menuBtn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    };

    menuBtn.addEventListener("click", () => {
      mobileMenu.classList.add("active");
      menuBtn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
    });

    closeMenu.addEventListener("click", closeMobileMenu);

    mobileMenu.addEventListener("click", (e) => {
      if (e.target === mobileMenu) {
        closeMobileMenu();
      }
    });

    mobileMenu.querySelectorAll("a, button").forEach((item) => {
      item.addEventListener("click", closeMobileMenu);
    });
  }

  /* =========================
     NOTIFICATION BAR
  ========================= */
  const notifBar = document.getElementById("notifBar");
  const notifClose = document.getElementById("notifClose");
  const navbar = document.getElementById("navbar");

  if (notifBar && notifClose && navbar) {
    notifClose.addEventListener("click", () => {
      notifBar.classList.add("hidden");
      navbar.classList.add("notif-hidden");
    });
  }

  /* =========================
     FLASH MESSAGES
  ========================= */
  const messages = document.querySelectorAll(".flash-message");

  messages.forEach((msg, i) => {
    msg.style.opacity = "0";
    msg.style.transform = "translateY(-10px)";

    setTimeout(() => {
      msg.style.transition = "all 0.4s ease";
      msg.style.opacity = "1";
      msg.style.transform = "translateY(0)";
    }, i * 150);

    setTimeout(() => removeMessage(msg), 4000 + i * 200);

    const closeBtn = msg.querySelector(".close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => removeMessage(msg));
    }
  });

  function removeMessage(msg) {
    if (!msg || !msg.isConnected) return;

    msg.style.transition = "all 0.3s ease";
    msg.style.opacity = "0";
    msg.style.transform = "translateY(-10px)";

    setTimeout(() => {
      if (msg.isConnected) {
        msg.remove();
      }
    }, 300);
  }

  /* =========================
     HERO COUNTERS
  ========================= */
  function animateCount(el, target) {
    if (!el) return;

    let current = 0;
    const duration = 1200;
    const stepTime = 16;
    const increment = Math.ceil(target / (duration / stepTime));

    const timer = setInterval(() => {
      current += increment;

      if (current >= target) {
        current = target;
        clearInterval(timer);
      }

      el.textContent = current;
    }, stepTime);
  }

  animateCount(document.getElementById("statExercise"), 20);
  animateCount(document.getElementById("statSatisfaction"), 92);

  /* =========================
     STATS API
  ========================= */
  window.addEventListener("load", () => {
    setTimeout(() => {
      fetch("/api/stats/")
        .then((res) => {
          if (!res.ok) throw new Error("API failed");
          return res.json();
        })
        .then((data) => {
          const users = data.total_users || 10;
          const display = users < 50 ? users : Math.ceil(users / 10) * 10 * 2;
          animateCount(document.getElementById("statUsers"), display);
        })
        .catch(() => {
          animateCount(document.getElementById("statUsers"), 10);
        });
    }, 2000);
  });

  /* =========================
     HERO ANIMATION
  ========================= */
  const animatedEls = document.querySelectorAll(".hero-animate");

  if (
    "IntersectionObserver" in window &&
    animatedEls.length &&
    window.innerWidth > 768
  ) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.style.animationPlayState = "running";
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 },
    );

    animatedEls.forEach((el) => {
      el.style.animationPlayState = "paused";
      observer.observe(el);
    });
  } else {
    animatedEls.forEach((el) => {
      el.style.opacity = "1";
      el.style.transform = "none";
    });
  }

  /* =========================
     SCROLL — NAVBAR BORDER
  ========================= */
  const navbarEl = document.getElementById("navbar");
  let ticking = false;

  function updateNavbar() {
    if (!navbarEl) return;
    if (window.scrollY > 10) {
      navbarEl.style.borderBottom = "1px solid rgba(249,115,22,0.25)";
    } else {
      navbarEl.style.borderBottom = "";
    }
    ticking = false;
  }

  window.addEventListener(
    "scroll",
    () => {
      if (!ticking) {
        requestAnimationFrame(updateNavbar);
        ticking = true;
      }
    },
    { passive: true },
  );

  /* =========================
     SMOOTH SCROLL
  ========================= */
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const target = document.querySelector(link.getAttribute("href"));
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
});

/* =========================
   FEATURE CARD TOGGLE
========================= */
function toggleFeature(card) {
  const isActive = card.classList.contains("active");

  document.querySelectorAll(".feature-card").forEach((c) => {
    c.classList.remove("active");
  });

  if (!isActive) {
    card.classList.add("active");

    setTimeout(() => {
      const rect = card.getBoundingClientRect();
      if (rect.bottom > window.innerHeight - 20) {
        window.scrollBy({
          top: rect.bottom - window.innerHeight + 40,
          behavior: "smooth",
        });
      }
    }, 400);
  }
}

/* =========================
   PRICING CARD TOGGLE
========================= */
function togglePricing(card) {
  const isActive = card.classList.contains("active");

  document.querySelectorAll(".pricing-card").forEach((c) => {
    c.classList.remove("active");
  });

  if (!isActive) {
    card.classList.add("active");

    setTimeout(() => {
      const rect = card.getBoundingClientRect();
      if (rect.bottom > window.innerHeight - 20) {
        window.scrollBy({
          top: rect.bottom - window.innerHeight + 40,
          behavior: "smooth",
        });
      }
    }, 400);
  }
}
