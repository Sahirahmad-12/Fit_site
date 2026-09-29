document.addEventListener("DOMContentLoaded", () => {
  const hero = document.getElementById("heroContent");

  setTimeout(() => {
    hero.classList.remove("opacity-0");
    hero.classList.add("hero-animate");
  }, 200); // small delay for smooth start
});
