const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const ts = require("typescript");
const code = ts.transpileModule(
  fs.readFileSync(
    path.join(__dirname, "../src/community/postFrame.ts"),
    "utf8",
  ),
  { compilerOptions: { module: ts.ModuleKind.CommonJS } },
).outputText;
const output = {};
new Function("exports", code)(output);
const { postFrame } = output;

test("single photos follow their original landscape and portrait proportions", () => {
  assert.deepEqual(postFrame(360, [{ width: 1200, height: 800 }]), {
    height: 240,
    scale: 0.3,
  });
  assert.deepEqual(postFrame(360, [{ width: 800, height: 1200 }]), {
    height: 540,
    scale: 0.45,
  });
});
test("mixed albums use the widest width and tallest height with one proportional scale", () => {
  const portrait = { width: 1600, height: 2400 },
    landscape = { width: 3200, height: 1800 };
  const frame = postFrame(320, [portrait, landscape]);
  assert.deepEqual(frame, { height: 240, scale: 0.1 });
  assert.equal(portrait.width * frame.scale, 160);
  assert.equal(landscape.height * frame.scale, 180);
});
test("small originals are centered without being enlarged", () => {
  assert.deepEqual(postFrame(400, [{ width: 100, height: 200 }]), {
    height: 200,
    scale: 1,
  });
});
test("missing or invalid sizes have a finite placeholder frame", () => {
  assert.deepEqual(postFrame(320, [undefined, { width: 0, height: 200 }]), {
    height: 320,
    scale: 1,
  });
});
