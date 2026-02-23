(() => {
  const THEMES = ["neon-dusk", "sunset-tape", "chrome-night"];
  const STORAGE_KEY = "bernban_theme";

  const parseThemeFromQuery = () => {
    const params = new URLSearchParams(window.location.search);
    const candidate = params.get("theme");
    return THEMES.includes(candidate) ? candidate : null;
  };

  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem(STORAGE_KEY, theme);
    const label = document.querySelector("[data-theme-current]");
    if (label) label.textContent = theme.replace("-", " ");
  };

  const chosenFromQuery = parseThemeFromQuery();
  const savedTheme = window.localStorage.getItem(STORAGE_KEY);
  const initialTheme = chosenFromQuery || (THEMES.includes(savedTheme) ? savedTheme : "neon-dusk");
  applyTheme(initialTheme);

  document.querySelectorAll("[data-theme-option]").forEach((btn) => {
    const theme = btn.getAttribute("data-theme-option");
    if (!THEMES.includes(theme)) return;

    if (theme === initialTheme) btn.setAttribute("aria-pressed", "true");

    btn.addEventListener("click", () => {
      applyTheme(theme);
      document.querySelectorAll("[data-theme-option]").forEach((other) => {
        other.setAttribute("aria-pressed", other === btn ? "true" : "false");
      });
      document.querySelectorAll("[data-theme-link]").forEach((link) => {
        const url = new URL(link.getAttribute("href"), window.location.origin);
        url.searchParams.set("theme", theme);
        link.setAttribute("href", url.pathname + url.search);
      });
    });
  });

  document.querySelectorAll("[data-theme-link]").forEach((link) => {
    const theme = document.documentElement.getAttribute("data-theme") || "neon-dusk";
    const url = new URL(link.getAttribute("href"), window.location.origin);
    url.searchParams.set("theme", theme);
    link.setAttribute("href", url.pathname + url.search);
  });
})();
