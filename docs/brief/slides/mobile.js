(function () {
  "use strict";
  var deck = document.querySelector(".deck");
  if (!deck) return;
  var startX = 0;
  var startY = 0;
  var tracking = false;

  function go(dir) {
    document.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: dir > 0 ? "ArrowRight" : "ArrowLeft",
        bubbles: true,
      })
    );
  }

  deck.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1) return;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      tracking = true;
    },
    { passive: true }
  );

  deck.addEventListener(
    "touchend",
    function (e) {
      if (!tracking) return;
      tracking = false;
      var t = e.changedTouches[0];
      var dx = t.clientX - startX;
      var dy = t.clientY - startY;
      if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
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
})();
