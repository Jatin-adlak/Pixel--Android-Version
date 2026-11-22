import { Platform } from "react-native";
import { clearRefresh, readRefresh, writeRefresh } from "./storage";
import type { AuthConfig, Tokens } from "./types";
import { apiOrigin } from "./apiOrigin";

export const API_URL = apiOrigin(
  process.env.EXPO_PUBLIC_API_URL,
  Platform.OS,
  Platform.OS === "web" && typeof window !== "undefined"
    ? window.location.hostname
    : undefined,
);
export const clientType = Platform.OS === "web" ? "web" : "native";
let accessToken: string | null = null;
let csrfToken = "";
let refreshing: Promise<Tokens> | null = null;
let onExpired: (() => void) | null = null;
export function handleSessionExpiry(callback: (() => void) | null) {
  onExpired = callback;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
  }
}

function errorText(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(errorText).join(" ");
  if (value && typeof value === "object")
    return Object.entries(value)
      .filter(([key]) => key !== "code")
      .map(
        ([key, item]) =>
          `${key === "detail" || key === "non_field_errors" ? "" : `${key.replaceAll("_", " ")}: `}${errorText(item)}`,
      )
      .join("\n");
  return "Something went wrong. Please try again.";
}

export async function api<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
  retry = true,
  csrfRetry = true,
): Promise<T> {
  let response: Response;
  const controller = new AbortController();
  let timedOut = false;
  const abort = () => controller.abort();
  if (options.signal?.aborted) abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  const timeout = setTimeout(() => {
    timedOut = true;
    abort();
  }, options.timeoutMs ?? 15000);
  try {
    response = await fetch(`${API_URL}/api/v1${path}`, {
      ...options,
      credentials: "include",
      signal: controller.signal,
      headers: {
        ...(options.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      timedOut
        ? "PIXEL took too long to respond. Please try again on a stable connection."
        : "Cannot reach PIXEL. Check your connection and that the backend is running.",
      0,
      timedOut ? "timeout" : "network",
    );
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abort);
  }
  if (
    response.status === 401 &&
    retry &&
    (!path.startsWith("/auth/") || path === "/auth/logout/")
  ) {
    try {
      await refreshSession();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await dropSession();
        onExpired?.();
      }
      throw error;
    }
    return api<T>(path, options, false, csrfRetry);
  }
  const payload = await response.json().catch(() => ({}));
  if (
    response.status === 403 &&
    payload.code === "csrf_failed" &&
    csrfRetry &&
    path !== "/auth/config/"
  ) {
    await loadConfig();
    return api<T>(path, options, retry, false);
  }
  if (!response.ok)
    throw new ApiError(errorText(payload), response.status, payload.code);
  return payload as T;
}

export async function loadConfig() {
  const config = await api<AuthConfig>("/auth/config/");
  csrfToken = config.csrf_token;
  return config;
}

export async function storeSession(tokens: Tokens) {
  if (tokens.refresh) await writeRefresh(tokens.refresh);
  accessToken = tokens.access;
  return tokens.user;
}

export async function refreshSession(): Promise<Tokens> {
  if (!refreshing) {
    refreshing = (async () => {
      const refresh = await readRefresh();
      if (clientType === "native" && !refresh)
        throw new ApiError("Please sign in.", 401);
      const tokens = await api<Tokens>(
        "/auth/refresh/",
        {
          method: "POST",
          body: JSON.stringify({
            client: clientType,
            ...(refresh ? { refresh } : {}),
          }),
        },
        false,
      );
      await storeSession(tokens);
      return tokens;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export async function dropSession() {
  accessToken = null;
  await clearRefresh();
}
