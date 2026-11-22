import * as Crypto from "expo-crypto";
import * as WebBrowser from "expo-web-browser";
import { isRunningInExpoGo } from "expo";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Platform } from "react-native";
import {
  api,
  clientType,
  dropSession,
  handleSessionExpiry,
  loadConfig,
  refreshSession,
  storeSession,
} from "./api";
import { clearVerifier, readVerifier, writeVerifier } from "./storage";
import type { AuthConfig, CampusUser, PolicyInput, Tokens } from "./types";

type AuthState = {
  user: CampusUser | null;
  config: AuthConfig | null;
  loading: boolean;
  connectionError: string;
  initialize: () => Promise<void>;
  login: (
    identifier: string,
    password: string,
    policy: PolicyInput,
  ) => Promise<void>;
  google: (policy: PolicyInput) => Promise<void>;
  completeGoogle: (ticket: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: CampusUser) => void;
};
const Context = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CampusUser | null>(null);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState("");
  const exchanges = useRef(new Map<string, Promise<void>>());
  useEffect(() => {
    handleSessionExpiry(() => setUser(null));
    return () => handleSessionExpiry(null);
  }, []);

  const initialize = useCallback(
    () =>
      loadConfig()
        .then(async (nextConfig) => {
          setConfig(nextConfig);
          setConnectionError("");
          try {
            const tokens = await refreshSession();
            setUser(tokens.user);
          } catch (error) {
            if (
              error instanceof Error &&
              "status" in error &&
              error.status === 401
            ) {
              await dropSession();
              setUser(null);
            } else throw error;
          }
        })
        .catch((error) => {
          setConnectionError(
            error instanceof Error ? error.message : "Cannot connect to PIXEL.",
          );
        })
        .finally(() => {
          setLoading(false);
        }),
    [],
  );
  useEffect(() => {
    void initialize();
  }, [initialize]);

  const login = useCallback(
    async (identifier: string, password: string, policy: PolicyInput) => {
      const tokens = await api<Tokens>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({
          identifier,
          password,
          client: clientType,
          ...policy,
        }),
      });
      setUser(await storeSession(tokens));
    },
    [],
  );

  const completeGoogle = useCallback((ticket: string) => {
    const existing = exchanges.current.get(ticket);
    if (existing) return existing;
    const exchange = (async () => {
      const verifier = await readVerifier();
      if (!verifier)
        throw new Error(
          "This Google login belongs to another tab or has expired. Please try again.",
        );
      const tokens = await api<Tokens>("/auth/google/exchange/", {
        method: "POST",
        body: JSON.stringify({ ticket, verifier, client: clientType }),
      });
      await clearVerifier();
      setUser(await storeSession(tokens));
    })();
    exchanges.current.set(ticket, exchange);
    return exchange;
  }, []);

  const google = useCallback(
    async (policy: PolicyInput) => {
      if (isRunningInExpoGo()) {
        throw new Error(
          "Google sign-in needs the PIXEL development build. In Expo Go, sign in with your username or college email and password.",
        );
      }
      const verifier = Array.from(
        await Crypto.getRandomBytesAsync(32),
        (byte) => byte.toString(16).padStart(2, "0"),
      ).join("");
      const hash = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        verifier,
        { encoding: Crypto.CryptoEncoding.BASE64 },
      );
      const challenge = hash
        .replaceAll("+", "-")
        .replaceAll("/", "_")
        .replace(/=+$/, "");
      await writeVerifier(verifier);
      const result = await api<{ url: string }>("/auth/google/start/", {
        method: "POST",
        body: JSON.stringify({ ...policy, challenge, client: clientType }),
      });
      if (Platform.OS === "web") {
        window.location.assign(result.url);
      } else {
        const response = await WebBrowser.openAuthSessionAsync(
          result.url,
          "pixelmobile://auth/callback",
        );
        if (response.type === "success") {
          const url = new URL(response.url);
          const ticket = url.searchParams.get("ticket");
          if (!ticket)
            throw new Error("Use your verified @sait.ac.in Google account.");
          await completeGoogle(ticket);
        } else {
          await clearVerifier();
          throw new Error("Google sign-in was cancelled.");
        }
      }
    },
    [completeGoogle],
  );

  const logout = useCallback(async () => {
    await api("/auth/logout/", { method: "POST", body: "{}" });
    await dropSession();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      config,
      loading,
      connectionError,
      initialize,
      login,
      google,
      completeGoogle,
      logout,
      updateUser: setUser,
    }),
    [
      user,
      config,
      loading,
      connectionError,
      initialize,
      login,
      google,
      completeGoogle,
      logout,
    ],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAuth() {
  const context = useContext(Context);
  if (!context) throw new Error("AuthProvider is required.");
  return context;
}
