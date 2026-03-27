(function () {
  var root = document.documentElement;
  var storageKey = "privateViewUnlocked";
  var privateViewHash = "6aae4db98aa4d193f32bcdbdb6372110905d77262cb23b957b2c2ae8097465eb";

  function persist(value) {
    try {
      localStorage.setItem(storageKey, value ? "true" : "false");
    } catch (error) {
      return;
    }
  }

  function applyState(unlocked) {
    var button = document.querySelector(".private-view-toggle");
    var icon = button ? button.querySelector(".private-view-icon") : null;
    var text = button ? button.querySelector(".private-view-text") : null;

    if (unlocked) {
      root.setAttribute("data-private-view", "enabled");
    } else {
      root.removeAttribute("data-private-view");
    }

    if (!button) {
      return;
    }

    button.setAttribute("aria-pressed", unlocked ? "true" : "false");
    button.setAttribute("aria-label", unlocked ? "Lock private view" : "Unlock private view");
    button.setAttribute("title", unlocked ? "Lock private view" : "Unlock private view");

    if (icon) {
      icon.innerHTML = unlocked ? "&#128275;" : "&#128274;";
    }

    if (text) {
      text.textContent = unlocked ? "Unlocked" : "Private";
    }
  }

  async function sha256(text) {
    if (!window.crypto || !window.crypto.subtle || !window.TextEncoder) {
      return "";
    }

    var bytes = new TextEncoder().encode(text);
    var hashBuffer = await window.crypto.subtle.digest("SHA-256", bytes);
    var hashArray = Array.prototype.slice.call(new Uint8Array(hashBuffer));

    return hashArray.map(function (b) {
      return b.toString(16).padStart(2, "0");
    }).join("");
  }

  async function handleToggle() {
    var isUnlocked = root.getAttribute("data-private-view") === "enabled";

    if (isUnlocked) {
      persist(false);
      applyState(false);
      return;
    }

    var input = window.prompt("Enter your private-view passphrase:");

    if (!input) {
      return;
    }

    var hashed = await sha256(input.trim());

    if (hashed === privateViewHash) {
      persist(true);
      applyState(true);
      return;
    }

    window.alert("Passphrase incorrect. Public view stays on.");
  }

  function init() {
    var button = document.querySelector(".private-view-toggle");
    var unlocked = root.getAttribute("data-private-view") === "enabled";

    applyState(unlocked);

    if (!button) {
      return;
    }

    button.addEventListener("click", function () {
      handleToggle();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
