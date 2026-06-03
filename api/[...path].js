const { handleRequest } = require("../server");

module.exports = async function handler(request, response) {
  return handleRequest(request, response);
};
