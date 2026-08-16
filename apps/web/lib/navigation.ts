export const appViews = [
  "overview",
  "report",
  "trace",
  "tasks",
  "transparency",
] as const;

export type AppView = (typeof appViews)[number];

export function normalizeAppView(
  value: string | string[] | undefined,
): AppView {
  const candidate = Array.isArray(value) ? value[0] : value;
  return appViews.includes(candidate as AppView)
    ? (candidate as AppView)
    : "overview";
}

export function viewHref(view: AppView): string {
  return `/demo?view=${view}`;
}
