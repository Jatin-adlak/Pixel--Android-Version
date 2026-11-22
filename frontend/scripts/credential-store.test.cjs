const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const ts = require("typescript");

// Exercise the same dependency-free storage policy used by the native adapter,
// without loading native Expo modules or touching a user's stored credentials.
const source = fs.readFileSync(
  path.join(__dirname, "../src/auth/credentialStore.ts"),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const core = {};
new Function("exports", compiled)(core);
const { createCredentialStore } = core;
const key = "pixel.refresh";
const service = "com.pixel.credentials.v2";

function adapter() {
  const data = new Map();
  const calls = [];
  return {
    data,
    calls,
    async getItemAsync(name, options) {
      calls.push(["read", options?.keychainService]);
      return (
        data.get(`${options?.keychainService || "legacy"}:${name}`) ?? null
      );
    },
    async setItemAsync(name, value, options) {
      calls.push(["write", options?.keychainService]);
      data.set(`${options?.keychainService || "legacy"}:${name}`, value);
    },
    async deleteItemAsync(name, options) {
      calls.push(["delete", options?.keychainService]);
      data.delete(`${options?.keychainService || "legacy"}:${name}`);
    },
  };
}

test("uses the same PIXEL-specific encrypted service to write and read", async () => {
  const native = adapter();
  const store = createCredentialStore(native);
  await store.write(key, "test-refresh");
  assert.equal(await store.read(key), "test-refresh");
  assert.equal(native.data.get(`${service}:${key}`), "test-refresh");
  assert.equal(native.calls.filter(([action]) => action === "write").length, 1);
  assert.equal(store.isMemoryOnly(), false);
});

test("migrates an existing legacy token only after verifying the scoped write", async () => {
  const native = adapter();
  native.data.set(`legacy:${key}`, "old-refresh");
  const store = createCredentialStore(native);
  assert.equal(await store.read(key), "old-refresh");
  assert.equal(native.data.has(`legacy:${key}`), false);
  assert.equal(native.data.get(`${service}:${key}`), "old-refresh");
});

test("recovers a transient keystore write failure with one bounded retry", async () => {
  const native = adapter();
  const set = native.setItemAsync;
  let attempts = 0;
  native.setItemAsync = async (...args) => {
    if (++attempts === 1) throw new Error("Keystore operation failed");
    return set(...args);
  };
  const store = createCredentialStore(native);
  await store.write(key, "retry-refresh");
  assert.equal(attempts, 2);
  assert.equal(await store.read(key), "retry-refresh");
});

test("unreadable scoped and old entries do not block reaching the sign-in screen", async () => {
  const native = adapter();
  native.getItemAsync = async () => {
    throw new Error("SecureStore decryption failed");
  };
  assert.equal(await createCredentialStore(native).read(key), null);
});

test("normal builds fail closed when encrypted storage cannot write", async () => {
  const native = adapter();
  let attempts = 0;
  native.setItemAsync = async () => {
    attempts++;
    throw new Error("Keystore operation failed");
  };
  const store = createCredentialStore(native);
  await assert.rejects(
    store.write(key, "private-refresh"),
    /could not securely save/,
  );
  assert.equal(attempts, 2);
  assert.equal(store.isMemoryOnly(), false);
  assert.equal(await store.read(key), null);
  assert.equal(native.data.size, 0);
});

test("explicit development fallback stays in memory, reports once, and does not survive restart", async () => {
  const native = adapter();
  native.setItemAsync = async () => {
    throw new Error("Keystore operation failed");
  };
  let notices = 0;
  const store = createCredentialStore(native, {
    allowMemoryFallback: true,
    onMemoryFallback: () => notices++,
  });
  await store.write(key, "session-refresh");
  await store.write(key, "rotated-refresh");
  assert.equal(await store.read(key), "rotated-refresh");
  assert.equal(notices, 1);
  assert.equal(native.data.size, 0);
  assert.equal(await createCredentialStore(native).read(key), null);
  await store.clear(key);
  assert.equal(await store.read(key), null);
});

test("clearing a session blocks local reuse even when the device cannot delete its old entry", async () => {
  const native = adapter();
  native.data.set(`${service}:${key}`, "old-refresh");
  native.deleteItemAsync = async () => {
    throw new Error("Keystore unavailable");
  };
  const store = createCredentialStore(native);
  await store.clear(key);
  assert.equal(await store.read(key), null);
});

test("a failed read-back cannot silently be treated as a saved session", async () => {
  const native = adapter();
  native.getItemAsync = async () => null;
  await assert.rejects(
    createCredentialStore(native).write(key, "test-refresh"),
    /could not securely save/,
  );
  assert.equal(native.data.size, 0);
});

test("programming errors do not activate the memory fallback", async () => {
  const native = adapter();
  native.setItemAsync = async () => {
    throw new TypeError("Invalid argument");
  };
  const store = createCredentialStore(native, { allowMemoryFallback: true });
  await assert.rejects(store.write(key, "test-refresh"), /Invalid argument/);
  assert.equal(store.isMemoryOnly(), false);
});

test("the native adapter permits fallback only in development Expo Go", async () => {
  const storageSource = fs.readFileSync(
    path.join(__dirname, "../src/auth/storage.ts"),
    "utf8",
  );
  const storageCode = ts.transpileModule(storageSource, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  for (const [development, expoGo] of [
    [false, true],
    [true, false],
    [true, true],
  ]) {
    const native = adapter();
    native.setItemAsync = async () => {
      throw new Error("Keystore operation failed");
    };
    let notices = 0;
    const modules = {
      "expo-secure-store": native,
      expo: { isRunningInExpoGo: () => expoGo },
      "react-native": { Alert: { alert: () => notices++ } },
      "./credentialStore": core,
    };
    const storage = {};
    new Function("exports", "require", "__DEV__", storageCode)(
      storage,
      (name) => {
        assert.ok(name in modules, `Unexpected native import: ${name}`);
        return modules[name];
      },
      development,
    );
    if (development && expoGo) {
      await storage.writeRefresh("test-refresh");
      assert.equal(await storage.readRefresh(), "test-refresh");
      assert.equal(notices, 1);
    } else {
      await assert.rejects(
        storage.writeRefresh("test-refresh"),
        /could not securely save/,
      );
      assert.equal(notices, 0);
    }
    assert.equal(native.data.size, 0);
  }
});
