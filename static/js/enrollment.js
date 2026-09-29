/* ── Close all dropdowns ── */
function closeAll() {
  ["gender", "plan", "trainer"].forEach((id) => {
    document.getElementById(id + "Dropdown")?.classList.remove("open");
    document.getElementById(id + "Btn")?.classList.remove("open");
  });
}

/* ── Toggle dropdown ── */
function toggleDropdown(id) {
  const menu = document.getElementById(id + "Dropdown");
  const btn = document.getElementById(id + "Btn");
  const isOpen = menu.classList.contains("open");
  closeAll();
  if (!isOpen) {
    menu.classList.add("open");
    btn.classList.add("open");
  }
}

/* ── Outside click closes dropdowns ── */
document.addEventListener("click", function (e) {
  if (!e.target.closest(".dropdown-wrap")) closeAll();
});

/* ── Plan select ── */
function selectPlan(id, name, price) {
  const label = document.getElementById("selectedPlan");
  label.innerText = name + " - ₹" + price;
  label.classList.remove("placeholder");
  document.getElementById("planInput").value = id;
  closeAll();
}

/* ── Trainer select ── */
function selectTrainer(id, name) {
  const label = document.getElementById("selectedTrainer");
  label.innerText = name;
  label.classList.remove("placeholder");
  document.getElementById("trainerInput").value = id;
  closeAll();
}

/* ── DOM Ready ── */
document.addEventListener("DOMContentLoaded", () => {
  /* ── Dropdown button bindings ── */
  document
    .getElementById("genderBtn")
    .addEventListener("click", () => toggleDropdown("gender"));
  document
    .getElementById("planBtn")
    .addEventListener("click", () => toggleDropdown("plan"));
  document
    .getElementById("trainerBtn")
    .addEventListener("click", () => toggleDropdown("trainer"));

  /* ── Gender select ── */
  document
    .querySelectorAll("#genderDropdown .dropdown-item")
    .forEach((item) => {
      item.addEventListener("click", () => {
        const val = item.dataset.value;
        const label = document.getElementById("selectedGender");
        label.textContent = val === "M" ? "Male" : "Female";
        label.classList.remove("placeholder");
        document.getElementById("genderInput").value = val;
        closeAll();
      });
    });

  /* ── Plan select via delegation ── */
  document
    .getElementById("planDropdown")
    .addEventListener("click", function (e) {
      const item = e.target.closest(".dropdown-item");
      if (!item) return;
      selectPlan(item.dataset.id, item.dataset.name, item.dataset.price);
    });

  /* ── Trainer select via delegation ── */
  document
    .getElementById("trainerDropdown")
    .addEventListener("click", function (e) {
      const item = e.target.closest(".dropdown-item");
      if (!item) return;
      selectTrainer(item.dataset.id, item.dataset.name);
    });

  /* ── Date of Birth ── */
  const dobInput = document.getElementById("dobInput");
  if (dobInput) {
    const today = new Date().toISOString().split("T")[0];
    dobInput.setAttribute("max", today);
    const minYear = new Date();
    minYear.setFullYear(minYear.getFullYear() - 100);
    dobInput.setAttribute("min", minYear.toISOString().split("T")[0]);

    dobInput.addEventListener("click", function () {
      this.showPicker && this.showPicker();
    });
  }

  /* ── Submit loading state ── */
  document.getElementById("enrollForm").addEventListener("submit", function () {
    const btn = document.getElementById("enrollBtn");
    if (this.checkValidity()) {
      btn.textContent = "Processing...";
      btn.disabled = true;
    }
  });
});
