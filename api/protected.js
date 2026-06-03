const { handleRequest } = require("../server");

module.exports = async function handler(request, response) {
  const url = new URL(request.url, `https://${request.headers.host || "localhost"}`);
  const file = url.searchParams.get("file");

  if (!file || !/^(groups|mvp-history|predictions|semifinals|team)\.html$/.test(file)) {
    response.statusCode = 404;
    response.setHeader("Content-Type", "application/json; charset=utf-8");
    response.end(JSON.stringify({ error: "Protected page not found" }));
    return;
  }

  url.searchParams.delete("file");
  const query = url.searchParams.toString();
  request.url = `/${file}${query ? `?${query}` : ""}`;
  return handleRequest(request, response);
};
