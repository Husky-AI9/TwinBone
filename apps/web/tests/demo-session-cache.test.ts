import { describe, expect, it } from "vitest";

import {
  clearDemoSessionCache,
  DEMO_SESSION_CACHE_KEY,
  readDemoSessionCache,
  writeDemoSessionCache,
} from "../lib/demo-session-cache";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}

describe("demo browser-session cache", () => {
  it("round-trips loaded data and clears it on logout", () => {
    const storage = memoryStorage();
    const cache = { version: 1 as const, tasks: [] };

    writeDemoSessionCache(storage, cache);
    expect(readDemoSessionCache(storage)).toEqual(cache);

    clearDemoSessionCache(storage);
    expect(storage.getItem(DEMO_SESSION_CACHE_KEY)).toBeNull();
    expect(readDemoSessionCache(storage)).toBeNull();
  });

  it("ignores malformed or obsolete browser data", () => {
    const storage = memoryStorage();
    storage.setItem(DEMO_SESSION_CACHE_KEY, "not-json");
    expect(readDemoSessionCache(storage)).toBeNull();
    storage.setItem(DEMO_SESSION_CACHE_KEY, JSON.stringify({ version: 99 }));
    expect(readDemoSessionCache(storage)).toBeNull();
  });
});
