/**
 * attendance_heatmap.js
 * Shows only previous month + current month attendance heatmap
 */

(function () {

  const dateSet = new Set(ATTENDED_DATES || []);

  /* ---------- Helpers ---------- */
  function toKey(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function addDays(date, days) {
    const newDate = new Date(date);
    newDate.setDate(newDate.getDate() + days);
    return newDate;
  }

  const MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec"
  ];

  /* ---------- Current Date ---------- */
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const currentMonth = today.getMonth();
  const currentYear = today.getFullYear();

  /* ---------- Previous Month ---------- */
  let previousMonth = currentMonth - 1;
  let previousYear = currentYear;

  if (previousMonth < 0) {
    previousMonth = 11;
    previousYear--;
  }

  /* ---------- Start & End Range ---------- */
  const gridStart = new Date(previousYear, previousMonth, 1);
  const gridEnd = today;

  const totalDays = Math.ceil(
    (gridEnd - gridStart) / (1000 * 60 * 60 * 24)
  ) + 1;

  const totalWeeks = Math.ceil(totalDays / 7);

  /* ---------- Streak Calculation ---------- */
  let streak = 0;
  let cursor = new Date(today);

  while (dateSet.has(toKey(cursor))) {
    streak++;
    cursor = addDays(cursor, -1);
  }

  const streakEl = document.getElementById("streak-val");
  const streakBar = document.getElementById("streak-bar");

  if (streakEl) {
    streakEl.textContent = streak;

    if (streakBar) {
      const percentage = Math.min(streak * 10, 100);
      streakBar.style.width = percentage + "%";
    }
  }

  /* ---------- Heatmap Rendering ---------- */
  const grid = document.getElementById("heatmap-grid");
  const monthsRow = document.getElementById("heatmap-months");

  if (!grid) return;

  grid.innerHTML = "";
  monthsRow.innerHTML = "";

  let lastRenderedMonth = -1;

  for (let week = 0; week < totalWeeks; week++) {
    const column = document.createElement("div");
    column.className = "heatmap-col";

    for (let day = 0; day < 7; day++) {
      const currentDate = addDays(gridStart, week * 7 + day);

      if (currentDate > gridEnd) break;

      const key = toKey(currentDate);
      const isPresent = dateSet.has(key);

      const cell = document.createElement("div");
      cell.className = "heatmap-cell";

      if (isPresent) {
        if (currentDate.toDateString() === today.toDateString()) {
          cell.classList.add("l2");
        } else {
          cell.classList.add("l1");
        }
      }

      const formattedDate = currentDate.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric"
      });

      cell.title = `${formattedDate} ${
        isPresent ? "• PRESENT" : "• ABSENT"
      }`;

      column.appendChild(cell);

      /* Month labels */
      if (day === 0) {
        const month = currentDate.getMonth();

        if (month !== lastRenderedMonth) {
          const span = document.createElement("span");
          span.textContent = MONTH_NAMES[month];
          span.style.marginRight = "40px";
          monthsRow.appendChild(span);

          lastRenderedMonth = month;
        }
      }
    }

    grid.appendChild(column);
  }

  /* ---------- Animate Stat Bars ---------- */
  document.querySelectorAll(".stat-bar-fill").forEach((bar) => {
    const targetWidth = bar.style.width;
    bar.style.width = "0";

    setTimeout(() => {
      bar.style.width = targetWidth;
    }, 300);
  });

})();