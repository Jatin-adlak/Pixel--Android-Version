const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const ts = require("typescript");

function load(file, imports = {}, globals = {}) {
  const source = fs.readFileSync(
    path.join(__dirname, "../src/auth", file),
    "utf8",
  );
  const code = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const exports = {};
  new Function("exports", "require", ...Object.keys(globals), code)(
    exports,
    (name) => {
      if (!(name in imports)) throw new Error(`Unexpected import ${name}`);
      return imports[name];
    },
    ...Object.values(globals),
  );
  return exports;
}
const { apiOrigin } = load("apiOrigin.ts");
test("local browser previews use the same cookie host; native and public APIs keep their configured host", () => {
  assert.equal(
    apiOrigin("http://192.168.1.69:8001", "web", "localhost"),
    "http://localhost:8001",
  );
  assert.equal(
    apiOrigin("http://192.168.1.69:8001", "android", "localhost"),
    "http://192.168.1.69:8001",
  );
  assert.equal(
    apiOrigin("http://localhost:8001", "web", "192.168.1.69"),
    "http://192.168.1.69:8001",
  );
  assert.equal(
    apiOrigin("https://api.pixel.example", "web", "localhost"),
    "https://api.pixel.example",
  );
  assert.equal(
    apiOrigin("http://192.168.1.69:8001", "web", "evil.example"),
    "http://192.168.1.69:8001",
  );
});

function harness(responses) {
  const calls = [];
  const api = load(
    "api.ts",
    {
      "react-native": { Platform: { OS: "web" } },
      "./apiOrigin": { apiOrigin },
      "./storage": {
        clearRefresh: async () => {},
        readRefresh: async () => null,
        writeRefresh: async () => {},
      },
    },
    {
      fetch: async (url, options) => {
        calls.push({ url, options });
        const next = responses.shift();
        if (!next) throw new Error("Unexpected fetch");
        return new Response(JSON.stringify(next.body), { status: next.status });
      },
    },
  );
  return { ...api, calls };
}
test("refresh restores a rotated CSRF token once even when JWT retry is disabled", async () => {
  const app = harness([
    {
      status: 403,
      body: { code: "csrf_failed", detail: "Security check failed" },
    },
    { status: 200, body: { csrf_token: "fresh-token" } },
    { status: 200, body: { access: "access", user: { id: "test" } } },
  ]);
  const tokens = await app.refreshSession();
  assert.equal(tokens.access, "access");
  assert.equal(app.calls.length, 3);
  assert.equal(app.calls[2].options.headers["X-CSRFToken"], "fresh-token");
  assert.equal(app.calls[2].options.credentials, "include");
});
test("persistent CSRF rejection stays a failure after one retry", async () => {
  const app = harness([
    { status: 403, body: { code: "csrf_failed" } },
    { status: 200, body: { csrf_token: "fresh-token" } },
    { status: 403, body: { code: "csrf_failed" } },
  ]);
  await assert.rejects(
    app.api("/auth/login/", { method: "POST", body: "{}" }),
    (error) => error.status === 403,
  );
  assert.equal(app.calls.length, 3);
});
test("ordinary permission failures never refresh CSRF or retry a mutation", async () => {
  const app = harness([
    { status: 403, body: { detail: "Administrator required" } },
  ]);
  await assert.rejects(
    app.api("/management/publications/", { method: "POST", body: "{}" }),
    (error) => error.status === 403,
  );
  assert.equal(app.calls.length, 1);
});
