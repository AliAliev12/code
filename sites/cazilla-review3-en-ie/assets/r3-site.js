(function () {
  "use strict";

  var AGE_COOKIE = "cazilla_review3_player_age_ok";
  var COOKIE_CHOICE = "cazilla_review3_player_cookie";
  var AGE_MAX_AGE = 3 * 24 * 60 * 60;

  var minAge = 18;
  try {
    var da = document.documentElement.getAttribute("data-min-gambling-age");
    if (da && !isNaN(parseInt(da, 10))) minAge = parseInt(da, 10);
  } catch (_) {}

  var hamburger = document.getElementById("hamburger");
  var mainNav = document.getElementById("mainNav");
  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  if (hamburger && mainNav) {
    hamburger.addEventListener("click", function () {
      var isOpen = mainNav.dataset.open === "true";
      mainNav.dataset.open = isOpen ? "false" : "true";
    });
  }

  function getCookie(name) {
    var m = document.cookie.match(
      new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1") + "=([^;]*)")
    );
    return m ? decodeURIComponent(m[1]) : "";
  }

  function setCookie(name, value, maxAgeSec) {
    document.cookie =
      name + "=" + encodeURIComponent(value) + ";path=/;max-age=" + String(maxAgeSec) + ";SameSite=Lax";
  }

  var ageGate = document.getElementById("ageGate");
  var cookieGate = document.getElementById("cookieGate");
  var siteContent = document.getElementById("siteContent");
  var ageUnder = document.getElementById("ageUnder");
  var ageOk = document.getElementById("ageOk");
  var cookieAccept = document.getElementById("cookieAccept");
  var cookieReject = document.getElementById("cookieReject");

  function show(el) {
    if (!el) return;
    el.removeAttribute("hidden");
    el.setAttribute("aria-hidden", "false");
  }

  function hide(el) {
    if (!el) return;
    el.setAttribute("hidden", "hidden");
    el.setAttribute("aria-hidden", "true");
  }

  function setBlur(on) {
    if (siteContent) siteContent.classList.toggle("isBlurred", !!on);
  }

  function setScrollLock(on) {
    document.documentElement.classList.toggle("complianceNoScroll", !!on);
  }

  if (ageUnder) {
    ageUnder.addEventListener("click", function () {
      hide(ageGate);
      setBlur(true);
      setScrollLock(true);
    });
  }

  if (ageOk) {
    ageOk.addEventListener("click", function () {
      setCookie(AGE_COOKIE, "1", AGE_MAX_AGE);
      hide(ageGate);
      setBlur(false);
      setScrollLock(false);
      show(cookieGate);
    });
  }

  function closeCookieChoice(val) {
    setCookie(COOKIE_CHOICE, val, 365 * 24 * 60 * 60);
    hide(cookieGate);
  }

  if (cookieAccept) cookieAccept.addEventListener("click", function () { closeCookieChoice("accept"); });
  if (cookieReject) cookieReject.addEventListener("click", function () { closeCookieChoice("reject"); });

  if (getCookie(AGE_COOKIE) === "1") {
    hide(ageGate);
    setBlur(false);
    if (!getCookie(COOKIE_CHOICE)) show(cookieGate);
    else hide(cookieGate);
  } else {
    show(ageGate);
    hide(cookieGate);
  }
})();
