type StoreOptions = { keychainService: string };
export type CredentialAdapter = {
  getItemAsync: (key: string, options?: StoreOptions) => Promise<string | null>;
  setItemAsync: (
    key: string,
    value: string,
    options?: StoreOptions,
  ) => Promise<void>;
  deleteItemAsync: (key: string, options?: StoreOptions) => Promise<void>;
};

function isKeyStoreFailure(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  const code =
    error && typeof error === "object" && "code" in error
      ? String(error.code)
      : "";
  return /securestore|keystore|keychain|decrypt|encrypt|key.*invalidated/i.test(
    `${code} ${message}`,
  );
}

export function createCredentialStore(
  adapter: CredentialAdapter,
  policy: { allowMemoryFallback?: boolean; onMemoryFallback?: () => void } = {},
) {
  const options = { keychainService: "com.pixel.credentials.v2" };
  const memory = new Map<string, string>();
  const cleared = new Set<string>();
  let memoryOnly = false;

  async function remove(key: string, scoped: boolean) {
    try {
      await adapter.deleteItemAsync(key, scoped ? options : undefined);
    } catch {
      /* Best effort: no global keystore reset or other projects' keys. */
    }
  }

  async function write(key: string, value: string) {
    if (memoryOnly) {
      cleared.delete(key);
      memory.set(key, value);
      return;
    }
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        await adapter.setItemAsync(key, value, options);
        if ((await adapter.getItemAsync(key, options)) !== value) {
          throw new Error("SecureStore could not verify the encrypted write.");
        }
        cleared.delete(key);
        memory.delete(key);
        await remove(key, false); // Migrate away from the old default alias.
        return;
      } catch (error) {
        if (!isKeyStoreFailure(error)) throw error;
        await remove(key, true);
      }
    }
    if (!policy.allowMemoryFallback) {
      throw new Error(
        "PIXEL could not securely save your sign-in on this device. Restart your phone and try again.",
      );
    }
    // Explicitly enabled only for development in Expo Go. Never write plaintext
    // credentials to AsyncStorage, preferences, files, logs or browser storage.
    memoryOnly = true;
    cleared.delete(key);
    memory.set(key, value);
    policy.onMemoryFallback?.();
  }

  async function read(key: string): Promise<string | null> {
    if (cleared.has(key)) return null;
    if (memoryOnly) return memory.get(key) ?? null;
    try {
      const value = await adapter.getItemAsync(key, options);
      if (value !== null) return value;
    } catch (error) {
      if (!isKeyStoreFailure(error)) throw error;
      await remove(key, true);
    }
    let legacy: string | null;
    try {
      legacy = await adapter.getItemAsync(key);
    } catch (error) {
      if (!isKeyStoreFailure(error)) throw error;
      await remove(key, false);
      return null; // An unreadable old token must not block the sign-in screen.
    }
    if (legacy !== null) await write(key, legacy);
    return legacy;
  }

  async function clear(key: string) {
    cleared.add(key);
    memory.delete(key);
    await remove(key, true);
    await remove(key, false);
    if (!memory.size) memoryOnly = false;
  }

  return { read, write, clear, isMemoryOnly: () => memoryOnly };
}
