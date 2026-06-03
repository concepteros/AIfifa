(() => {
  const hasCookie = document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .some((cookie) => cookie.startsWith("fifa2026_frontend_access="));

  let hasLocalAccess = false;
  try {
    const access = JSON.parse(localStorage.getItem("fifa2026PremiumAccess") || "null");
    hasLocalAccess = Boolean(access?.walletAddress);
  } catch {}

  if (!hasCookie && !hasLocalAccess) {
    window.location.replace("./index.html");
  }
})();
