import type {
  ReviewTask,
  Timeline,
  Transparency,
} from "@bonetwin/shared-types";

export const DEMO_SESSION_CACHE_KEY = "bonetwin.demo-dashboard.v1";

export type DemoSessionCache = {
  version: 1;
  timeline?: Timeline;
  tasks?: ReviewTask[];
  transparency?: Transparency;
};

type ReadStorage = Pick<Storage, "getItem">;
type WriteStorage = Pick<Storage, "setItem">;
type ClearStorage = Pick<Storage, "removeItem">;

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function readDemoSessionCache(
  storage: ReadStorage,
): DemoSessionCache | null {
  try {
    const raw = storage.getItem(DEMO_SESSION_CACHE_KEY);
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (!isObject(value) || value.version !== 1) return null;

    const cache: DemoSessionCache = { version: 1 };
    if (isObject(value.timeline))
      cache.timeline = value.timeline as unknown as Timeline;
    if (Array.isArray(value.tasks)) cache.tasks = value.tasks as ReviewTask[];
    if (isObject(value.transparency)) {
      cache.transparency = value.transparency as unknown as Transparency;
    }
    return cache;
  } catch {
    return null;
  }
}

export function writeDemoSessionCache(
  storage: WriteStorage,
  cache: DemoSessionCache,
): void {
  storage.setItem(DEMO_SESSION_CACHE_KEY, JSON.stringify(cache));
}

export function clearDemoSessionCache(storage: ClearStorage): void {
  storage.removeItem(DEMO_SESSION_CACHE_KEY);
}
