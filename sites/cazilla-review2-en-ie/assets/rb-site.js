(function () {
  "use strict";
  var AGE = "cazilla_review2_en_ie_age_ok";
  var COOKIE = "cazilla_review2_en_ie_cookie";
  function getCookie(n) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + n.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1") + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }
  function setCookie(n, v, max) {
    document.cookie = n + "=" + encodeURIComponent(v) + ";path=/;max-age=" + max + ";SameSite=Lax";
  }
  function show(el) { if (el) { el.removeAttribute("hidden"); el.setAttribute("aria-hidden", "false"); } }
  function hide(el) { if (el) { el.setAttribute("hidden", "hidden"); el.setAttribute("aria-hidden", "true"); } }
  var ageGate = document.getElementById("ageGate");
  var cookieGate = document.getElementById("cookieGate");
  var site = document.getElementById("siteContent");
  function blur(on) { if (site) site.classList.toggle("isBlurred", !!on); }
  function lock(on) { document.documentElement.classList.toggle("complianceNoScroll", !!on); }
  var ageOk = document.getElementById("ageOk");
  var ageUnder = document.getElementById("ageUnder");
  if (ageOk) ageOk.addEventListener("click", function () {
    setCookie(AGE, "1", 3 * 24 * 60 * 60);
    hide(ageGate); blur(false); lock(false);
    if (!getCookie(COOKIE)) show(cookieGate); else hide(cookieGate);
  });
  if (ageUnder) ageUnder.addEventListener("click", function () { hide(ageGate); blur(true); lock(true); });
  var ca = document.getElementById("cookieAccept");
  var cr = document.getElementById("cookieReject");
  if (ca) ca.addEventListener("click", function () { setCookie(COOKIE, "accept", 365 * 24 * 60 * 60); hide(cookieGate); });
  if (cr) cr.addEventListener("click", function () { setCookie(COOKIE, "reject", 365 * 24 * 60 * 60); hide(cookieGate); });
  if (getCookie(AGE) === "1") {
    hide(ageGate); blur(false); lock(false);
    if (!getCookie(COOKIE)) show(cookieGate); else hide(cookieGate);
  } else { show(ageGate); hide(cookieGate); lock(true); }
  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());
  var navToggle = document.getElementById("navToggle");
  var mainNav = document.getElementById("mainNav");
  if (navToggle && mainNav) {
    navToggle.addEventListener("click", function () {
      var open = mainNav.dataset.open === "true";
      mainNav.dataset.open = open ? "false" : "true";
      navToggle.setAttribute("aria-expanded", open ? "false" : "true");
      navToggle.setAttribute("aria-label", open ? "Open menu" : "Close menu");
    });
    document.addEventListener("click", function (ev) {
      if (mainNav.dataset.open !== "true") return;
      if (mainNav.contains(ev.target) || navToggle.contains(ev.target)) return;
      mainNav.dataset.open = "false";
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", "Open menu");
    });
  }
})();
