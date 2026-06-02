fetch("/api/auth/session", { headers: { Accept: "application/json" } })
  .then((response) => {
    if (!(response.headers.get("content-type") || "").includes("application/json")) {
      throw new Error("Wallet session API is unavailable");
    }
    return response.json();
  })
  .then((session) => {
    if (!session.authorized) window.location.replace("./index.html");
  })
  .catch(() => window.location.replace("./index.html"));
