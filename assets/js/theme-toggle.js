(function () {
  var storageKey = "theme";
  var root = document.documentElement;

  function getPreferredTheme() {
    var storedTheme = null;

    try {
      storedTheme = localStorage.getItem(storageKey);
    } catch (error) {
      storedTheme = null;
    }

    if (storedTheme === "dark" || storedTheme === "light") {
      return storedTheme;
    }

    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }

    return "light";
  }

  function persistTheme(theme) {
    try {
      localStorage.setItem(storageKey, theme);
    } catch (error) {
      return;
    }
  }

  function applyTheme(theme) {
    var toggle = document.querySelector(".theme-toggle");
    var icon = toggle ? toggle.querySelector(".theme-toggle-icon") : null;
    var text = toggle ? toggle.querySelector(".theme-toggle-text") : null;
    var isDark = theme === "dark";

    root.setAttribute("data-theme", theme);

    if (!toggle) {
      return;
    }

    toggle.setAttribute("aria-pressed", isDark ? "true" : "false");
    toggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
    toggle.setAttribute("title", isDark ? "Switch to light mode" : "Switch to dark mode");

    if (icon) {
      icon.innerHTML = isDark ? "&#9790;" : "&#9728;";
    }
  }

  function bindToggle() {
    var toggle = document.querySelector(".theme-toggle");
    var currentTheme = root.getAttribute("data-theme") || getPreferredTheme();

    applyTheme(currentTheme);

    if (!toggle) {
      return;
    }

    toggle.addEventListener("click", function () {
      currentTheme = currentTheme === "dark" ? "light" : "dark";
      applyTheme(currentTheme);
      persistTheme(currentTheme);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindToggle);
  } else {
    bindToggle();
  }
})();
