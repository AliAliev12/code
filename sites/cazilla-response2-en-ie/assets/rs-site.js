(function () {
  "use strict";
  var AGE_COOKIE = "cazilla_response_skin_age_ok";
  var COOKIE_CHOICE = "cazilla_response_skin_cookie";
  var AGE_MAX_AGE = 3 * 24 * 60 * 60;
  var hamburger = document.getElementById("hamburger");
  var mainNav = document.getElementById("mainNav");
  var sidebar = document.getElementById("rsSidebar");
  var sidebarToggle = document.getElementById("sidebarToggle");
  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
  if (hamburger && mainNav) {
    hamburger.addEventListener("click", function () {
      mainNav.dataset.open = mainNav.dataset.open === "true" ? "false" : "true";
    });
  }
  function setSidebar(open) {
    if (!sidebar) return;
    sidebar.dataset.open = open ? "true" : "false";
    document.body.classList.toggle("rs-sidebar-open", !!open);
  }
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
      setSidebar(sidebar.dataset.open !== "true");
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
  var viewport = document.getElementById("galleryViewport");
  var prev = document.getElementById("galleryPrev");
  var next = document.getElementById("galleryNext");
  var dots = document.getElementById("galleryDots");
  if (viewport) {
    var slides = Array.prototype.slice.call(viewport.querySelectorAll("img[data-slide]"));
    var idx = 0;
    function showSlide(i) {
      if (!slides.length) return;
      idx = (i + slides.length) % slides.length;
      slides.forEach(function (img, n) {
        img.classList.toggle("is-active", n === idx);
      });
      if (dots) {
        Array.prototype.forEach.call(dots.querySelectorAll("button"), function (btn, n) {
          btn.classList.toggle("is-active", n === idx);
        });
      }
    }
    if (prev) prev.addEventListener("click", function () { showSlide(idx - 1); });
    if (next) next.addEventListener("click", function () { showSlide(idx + 1); });
    if (dots) {
      dots.addEventListener("click", function (e) {
        var t = e.target;
        if (t && t.getAttribute("data-goto") != null) {
          showSlide(parseInt(t.getAttribute("data-goto"), 10));
        }
      });
    }
    showSlide(0);
  }
})();