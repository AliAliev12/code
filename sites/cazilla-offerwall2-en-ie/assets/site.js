(function () {
  "use strict";

  var AGE_COOKIE = "cazilla_offerwall2_en_ie_age_ok";
  var COOKIE_CHOICE = "cazilla_offerwall2_en_ie_cookie";
  var AGE_MAX_AGE = 3 * 24 * 60 * 60;

  var menuToggle = document.getElementById("menuToggle");
  var sideDrawer = document.getElementById("sideDrawer");
  var drawerOverlay = document.getElementById("drawerOverlay");
  var drawerClose = document.getElementById("drawerClose");
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

  function setDrawerOpen(open) {
    if (!sideDrawer) return;
    sideDrawer.classList.toggle("is-open", !!open);
    if (drawerOverlay) {
      drawerOverlay.classList.toggle("is-open", !!open);
      if (open) drawerOverlay.removeAttribute("hidden");
      else drawerOverlay.setAttribute("hidden", "hidden");
    }
    if (menuToggle) {
      menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
    }
    sideDrawer.setAttribute("aria-hidden", open ? "false" : "true");
    document.documentElement.classList.toggle("ow-drawer-open", !!open);
  }

  function toggleDrawer() {
    if (!sideDrawer) return;
    setDrawerOpen(!sideDrawer.classList.contains("is-open"));
  }

  if (menuToggle && sideDrawer) {
    menuToggle.addEventListener("click", toggleDrawer);
  }
  if (drawerClose) {
    drawerClose.addEventListener("click", function () {
      setDrawerOpen(false);
    });
  }
  if (drawerOverlay) {
    drawerOverlay.addEventListener("click", function () {
      setDrawerOpen(false);
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setDrawerOpen(false);
  });

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

  function setScrollLock(on) {
    document.documentElement.classList.toggle("compliance-no-scroll", !!on);
  }

  function setBlur(on) {
    if (!siteContent) return;
    siteContent.classList.toggle("isBlurred", !!on);
    setScrollLock(!!on);
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
