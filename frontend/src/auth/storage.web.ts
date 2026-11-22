// Refresh credentials stay in the server's HttpOnly cookie, never browser storage.
export const readRefresh = async (): Promise<string | null> => null;
export const writeRefresh = async (_value: string) => {};
export const clearRefresh = async () => {};
// A short-lived PKCE verifier is not a session token. It binds this tab's OAuth exchange.
export const readVerifier = async () =>
  sessionStorage.getItem("pixel.oauth.verifier");
export const writeVerifier = async (value: string) => {
  sessionStorage.setItem("pixel.oauth.verifier", value);
};
export const clearVerifier = async () => {
  sessionStorage.removeItem("pixel.oauth.verifier");
};
