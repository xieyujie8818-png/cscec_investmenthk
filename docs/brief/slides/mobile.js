(function () {
  "use strict";

  var deck = document.querySelector(".deck");
  if (!deck) return;

  var slides = Array.from(deck.querySelectorAll(".slide"));
  var mobileHint = document.querySelector(".mobile-hint");
  var startX = 0;
  var startY = 0;
  var tracking = false;
  var scrollEl = null;

  function activeIndex() {
    if (window.htmlPpt && typeof window.htmlPpt.getIndex === "function") {
      return window.htmlPpt.getIndex();
    }
    for (var i = 0; i < slides.length; i++) {
      if (slides[i].classList.contains("is-active")) return i;
    }
    return 0;
  }

  function goTo(n) {
    if (window.htmlPpt && typeof window.htmlPpt.go === "function") {
      window.htmlPpt.go(n);
      return;
    }
    location.hash = "#/" + (n + 1);
  }

  function go(dir) {
    goTo(activeIndex() + dir);
  }

  function findScrollable(start) {
    var el = start;
    while (el && el !== document.body) {
      if (el.classList && el.classList.contains("slide-body")) return el;
      if (el.classList && el.classList.contains("slide-toc-scroll")) return el;
      var style = window.getComputedStyle(el);
      var oy = style.overflowY;
      if ((oy === "auto" || oy === "scroll") && el.scrollHeight > el.clientHeight + 2) {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  document.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1) return;
      scrollEl = findScrollable(e.target);
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      tracking = true;
    },
    { passive: true }
  );

  document.addEventListener(
    "touchmove",
    function (e) {
      if (!tracking || !scrollEl || e.touches.length !== 1) return;
      var dy = e.touches[0].clientY - startY;
      var dx = e.touches[0].clientX - startX;
      if (Math.abs(dy) > Math.abs(dx)) tracking = false;
    },
    { passive: true }
  );

  document.addEventListener(
    "touchend",
    function (e) {
      if (!tracking) return;
      tracking = false;
      var t = e.changedTouches[0];
      var dx = t.clientX - startX;
      var dy = t.clientY - startY;
      if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.2) return;
      go(dx < 0 ? 1 : -1);
    },
    { passive: true }
  );

  var zones = document.querySelector(".tap-zones");
  if (zones) {
    zones.addEventListener("click", function (e) {
      var el = e.target;
      if (!el || !el.dataset) return;
      if (el.dataset.nav === "prev") go(-1);
      if (el.dataset.nav === "next") go(1);
    });
  }

  function playTocFeedback(li, clientX, clientY, done) {
    li.classList.remove("is-toc-jump", "is-toc-press");
    void li.offsetWidth;
    li.classList.add("is-toc-press", "is-toc-jump");

    var oldRipple = li.querySelector(".toc-ripple");
    if (oldRipple) oldRipple.remove();

    var ripple = document.createElement("span");
    ripple.className = "toc-ripple";
    var rect = li.getBoundingClientRect();
    var size = Math.max(rect.width, 48) * 0.42;
    ripple.style.width = size + "px";
    ripple.style.height = size + "px";
    ripple.style.left = (clientX - rect.left - size / 2) + "px";
    ripple.style.top = (clientY - rect.top - size / 2) + "px";
    li.appendChild(ripple);

    ripple.addEventListener("animationend", function () {
      ripple.remove();
    });

    window.setTimeout(function () {
      li.classList.remove("is-toc-press");
      if (done) done();
    }, 240);
  }

  function updateTocActive(idx) {
    deck.querySelectorAll(".slide-toc li[data-goto]").forEach(function (li) {
      var n = parseInt(li.getAttribute("data-goto"), 10);
      li.classList.toggle("is-toc-active", !isNaN(n) && n === idx);
    });
  }

  deck.addEventListener("click", function (e) {
    if (document.body.classList.contains("slide-editing")) return;
    var li = e.target.closest(".slide-toc li[data-goto]");
    if (!li) return;
    e.stopPropagation();
    e.preventDefault();
    var n = parseInt(li.getAttribute("data-goto"), 10);
    if (isNaN(n)) return;
    playTocFeedback(li, e.clientX, e.clientY, function () {
      goTo(n);
    });
  });

  document.addEventListener("htmlppt:slide", function (ev) {
    var idx = ev.detail && typeof ev.detail.idx === "number" ? ev.detail.idx : activeIndex();
    requestAnimationFrame(function () {
      updateTocActive(idx);
    });
  });

  function updateScrollHints() {
    deck.querySelectorAll(".slide-article").forEach(function (slide) {
      var body = slide.querySelector(".slide-body");
      if (!body) return;
      var overflow = body.scrollHeight > body.clientHeight + 8;
      slide.classList.toggle("is-scrollable", overflow);
      var atBottom = !overflow || body.scrollTop + body.clientHeight >= body.scrollHeight - 16;
      slide.classList.toggle("is-scrolled-end", atBottom);

      var hint = slide.querySelector(".scroll-hint");
      if (overflow && !hint) {
        hint = document.createElement("div");
        hint.className = "scroll-hint";
        hint.setAttribute("aria-hidden", "true");
        hint.textContent = "↓ 上下滑動閱讀全文";
        slide.appendChild(hint);
      }
      if (hint) {
        hint.classList.toggle("is-hidden", !overflow || atBottom);
      }
    });
  }

  deck.querySelectorAll(".slide-body, .slide-toc-scroll").forEach(function (body) {
    body.addEventListener("scroll", updateScrollHints, { passive: true });
  });

  document.addEventListener("htmlppt:slide", function () {
    requestAnimationFrame(updateScrollHints);
  });

  function updateMobileHint() {
    if (!mobileHint) return;
    mobileHint.classList.toggle("is-hidden", activeIndex() !== 0);
  }

  document.addEventListener("htmlppt:slide", function () {
    requestAnimationFrame(updateMobileHint);
  });

  document.addEventListener("htmlppt:refresh", function () {
    slides = Array.from(deck.querySelectorAll(".slide"));
    requestAnimationFrame(updateScrollHints);
    requestAnimationFrame(updateMobileHint);
    requestAnimationFrame(function () {
      updateTocActive(activeIndex());
    });
  });

  requestAnimationFrame(function () {
    updateTocActive(activeIndex());
  });

  window.addEventListener("resize", updateScrollHints);
  requestAnimationFrame(updateScrollHints);
  requestAnimationFrame(updateMobileHint);
  window.updateSlideScrollHints = updateScrollHints;
})();
