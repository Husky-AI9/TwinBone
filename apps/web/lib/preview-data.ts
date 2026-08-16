export type BoneSiteId =
  "left-total-hip" | "lumbar-spine" | "femoral-neck" | "forearm";

export type BoneSite = {
  id: BoneSiteId;
  label: string;
  shortLabel: string;
  bmd: string;
  tScore: string;
  change: string;
  status: "Verified" | "Excluded" | "Review" | "Missing";
  statusDetail: string;
  position: { left: string; top: string };
};

export const boneSites: BoneSite[] = [
  {
    id: "left-total-hip",
    label: "Left total hip",
    shortLabel: "Total hip",
    bmd: "0.742",
    tScore: "−1.6",
    change: "−1.9%",
    status: "Verified",
    statusDetail:
      "Comparable with the 2022 report and approved for the longitudinal view.",
    position: { left: "63%", top: "54%" },
  },
  {
    id: "lumbar-spine",
    label: "Lumbar spine",
    shortLabel: "Lumbar",
    bmd: "0.811",
    tScore: "−2.1",
    change: "Excluded",
    status: "Excluded",
    statusDetail:
      "A prior verified correction marks this site unsuitable for longitudinal comparison.",
    position: { left: "50%", top: "43%" },
  },
  {
    id: "femoral-neck",
    label: "Left femoral neck",
    shortLabel: "Femoral neck",
    bmd: "0.668",
    tScore: "−1.7",
    change: "−2.2%",
    status: "Review",
    statusDetail:
      "The value is source-backed, but scanner metadata needs clinician confirmation.",
    position: { left: "64%", top: "59%" },
  },
  {
    id: "forearm",
    label: "Distal forearm",
    shortLabel: "Forearm",
    bmd: "—",
    tScore: "—",
    change: "Missing",
    status: "Missing",
    statusDetail:
      "No comparable forearm measurement is present in the timeline.",
    position: { left: "81%", top: "46%" },
  },
];

export const timelinePoints = [
  { year: "2019", bmd: 0.781, tScore: "−1.3", label: "Baseline" },
  { year: "2022", bmd: 0.756, tScore: "−1.5", label: "Prior" },
  { year: "2026", bmd: 0.742, tScore: "−1.6", label: "Latest" },
];

export const memoryTrace = [
  {
    label: "Used",
    title: "Hip values are longitudinally comparable",
    source: "Report · Apr 12, 2026",
    tone: "teal",
  },
  {
    label: "Changed action",
    title: "Do not compare the lumbar measurement",
    source: "Clinician-verified correction · Jun 8, 2022",
    tone: "amber",
  },
  {
    label: "Open",
    title: "Confirm scanner metadata",
    source: "Review task · awaiting clinician",
    tone: "slate",
  },
] as const;

export function statusTone(status: BoneSite["status"]): string {
  return {
    Verified: "border-emerald-200 bg-emerald-50 text-emerald-700",
    Excluded: "border-amber-200 bg-amber-50 text-amber-800",
    Review: "border-sky-200 bg-sky-50 text-sky-700",
    Missing: "border-slate-200 bg-slate-50 text-slate-600",
  }[status];
}
