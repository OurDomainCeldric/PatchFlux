export interface BrowserIdentity {
  userId: string;
  userSecret: string;
  displayName: string;
}

const STORAGE_KEY = "patchflux:commentIdentity";

function randomToken() {
  const browserCrypto = globalThis.crypto;
  if (browserCrypto?.randomUUID) {
    return browserCrypto.randomUUID();
  }
  const values = new Uint32Array(4);
  browserCrypto?.getRandomValues(values);
  return Array.from(values, (value) => value.toString(16).padStart(8, "0")).join("-");
}

export function readBrowserIdentity(): BrowserIdentity {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<BrowserIdentity>;
      if (parsed.userId && parsed.userSecret) {
        return {
          userId: parsed.userId,
          userSecret: parsed.userSecret,
          displayName: parsed.displayName ?? "",
        };
      }
    }
  } catch {
    /* ignore corrupt localStorage */
  }
  const identity = {
    userId: randomToken(),
    userSecret: randomToken(),
    displayName: "",
  };
  saveBrowserIdentity(identity);
  return identity;
}

export function saveBrowserIdentity(identity: BrowserIdentity) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(identity));
  } catch {
    /* ignore */
  }
}
