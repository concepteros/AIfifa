const ACCESS_SESSION_KEY = "fifa2026AccessSession";

try {
  const session = JSON.parse(sessionStorage.getItem(ACCESS_SESSION_KEY) || "null");
  if (!session?.walletAddress || !session?.verifiedAt) {
    window.location.replace("./index.html");
  }
} catch {
  window.location.replace("./index.html");
}
