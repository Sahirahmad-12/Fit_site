// PRICING ACCORDION (separate from other sections)
function togglePricing(card) {
  const desc = card.querySelector(".pricing-desc");

  // Close all other cards
  document.querySelectorAll(".pricing-desc").forEach((el) => {
    if (el !== desc) {
      el.style.maxHeight = null;
      el.style.opacity = 0;
    }
  });

  // Toggle current card
  if (desc.style.maxHeight) {
    desc.style.maxHeight = null;
    desc.style.opacity = 0;
  } else {
    desc.style.maxHeight = desc.scrollHeight + "px";
    desc.style.opacity = 1;
  }
}
