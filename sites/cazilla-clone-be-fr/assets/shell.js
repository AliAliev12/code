(function () {
  const hamburger = document.getElementById("hamburger");
  const mainNav = document.getElementById("mainNav");
  const year = document.getElementById("year");

  if (year) year.textContent = String(new Date().getFullYear());

  try {
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  } catch (_) {}

  function forceTopIfNoHash() {
    if (window.location.hash) return;
    try {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    } catch (_) {
      window.scrollTo(0, 0);
    }
  }

  window.addEventListener("load", forceTopIfNoHash);
  window.addEventListener("pageshow", forceTopIfNoHash);

  if (hamburger && mainNav) {
    hamburger.addEventListener("click", function () {
      const isOpen = mainNav.dataset.open === "true";
      mainNav.dataset.open = isOpen ? "false" : "true";
    });
  }
})();

