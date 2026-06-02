fetch("/api/auth/session", { headers: { Accept: "application/json" } })
  .then((response) => response.json())
  .then((session) => {
    if (!session.authorized) window.location.replace("./index.html");
  })
  .catch(() => window.location.replace("./index.html"));
