function localHost(host: string) {
  if (["localhost", "127.0.0.1", "[::1]"].includes(host)) return true;
  const parts = host.split(".").map(Number);
  return (
    parts.length === 4 &&
    parts.every((part) => Number.isInteger(part) && part >= 0 && part <= 255) &&
    (parts[0] === 10 ||
      (parts[0] === 192 && parts[1] === 168) ||
      (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31))
  );
}

// LAN Expo Go keeps its LAN API. Browser previews use the page's local host,
// so cookie authentication does not depend on third-party cookie exceptions.
export function apiOrigin(
  configured: string | undefined,
  platform: string,
  pageHost?: string,
) {
  const fallback =
    platform === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000";
  const url = new URL(configured || fallback);
  if (
    platform === "web" &&
    pageHost &&
    url.protocol === "http:" &&
    ["8000", "8001"].includes(url.port) &&
    localHost(url.hostname) &&
    localHost(pageHost)
  )
    url.hostname = pageHost;
  return url.toString().replace(/\/$/, "");
}
