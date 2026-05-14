(function () {
  "use strict";

  var AGE_COOKIE = "cazilla_review_ie_age_ok";
  var COOKIE_CHOICE = "cazilla_review_ie_cookie";
  var AGE_MAX_AGE = 3 * 24 * 60 * 60;

  var minAge = 18;
  try {
    var da = document.documentElement.getAttribute("data-min-gambling-age");
    if (da && !isNaN(parseInt(da, 10))) {
      minAge = parseInt(da, 10);
    }
  } catch (_) {}

  var hamburger = document.getElementById("hamburger");
  var mainNav = document.getElementById("mainNav");
  var year = document.getElementById("year");

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
      name +
      "=" +
      encodeURIComponent(value) +
      ";path=/;max-age=" +
      String(maxAgeSec) +
      ";SameSite=Lax";
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
    if (!siteContent) return;
    siteContent.classList.toggle("isBlurred", !!on);
  }

  function setScrollLock(on) {
    document.documentElement.classList.toggle("complianceNoScroll", !!on);
  }

  function syncAgeCopy() {
    var t = document.getElementById("ageTitle");
    if (t) t.textContent = "Confirm you are " + minAge + " or over";
    if (ageUnder) ageUnder.textContent = "I am under " + minAge;
    if (ageOk) ageOk.textContent = "I am " + minAge + " or over";
    var ps = ageGate ? ageGate.getElementsByTagName("p") : [];
    if (ps.length) {
      var geo = document.documentElement.getAttribute("lang") || "";
      ps[0].textContent =
        "This site discusses regulated gambling topics. You must be at least " +
        minAge +
        " to continue. (Locale " +
        geo +
        ".)";
    }
  }

  function openCookieIfNeeded() {
    if (getCookie(COOKIE_CHOICE)) {
      hide(cookieGate);
      return;
    }
    show(cookieGate);
  }

  function initCompliance() {
    if (!ageGate) return;
    syncAgeCopy();

    if (getCookie(AGE_COOKIE) === "1") {
      hide(ageGate);
      setBlur(false);
      setScrollLock(false);
      openCookieIfNeeded();
      return;
    }

    show(ageGate);
    hide(cookieGate);
    setBlur(false);
    setScrollLock(false);
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

  initCompliance();
})();
