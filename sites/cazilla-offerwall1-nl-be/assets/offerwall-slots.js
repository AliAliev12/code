(function () {
  "use strict";

  var moreBtn = document.getElementById("owSlotsLoadMore");
  var grid = document.getElementById("ow-slots-grid");
  if (moreBtn && grid) {
    moreBtn.addEventListener("click", function () {
      var hidden = grid.querySelectorAll(".ow-slotsCard.is-hidden");
      for (var i = 0; i < hidden.length; i++) {
        hidden[i].classList.remove("is-hidden");
      }
      if (!grid.querySelector(".ow-slotsCard.is-hidden")) {
        moreBtn.setAttribute("hidden", "hidden");
      }
    });
  }
})();
