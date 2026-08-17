"use client";

import { BoneTwinClient, type DemoReportKey } from "@bonetwin/api-client";
import type {
  AgentRun,
  DashboardSnapshot,
  DocumentStatus,
  Measurement,
  MemoryTraceItem,
  ProcessingEvent,
  Report,
  ReviewTask,
  Timeline,
  Transparency,
} from "@bonetwin/shared-types";
import { useEffect, useMemo, useRef, useState } from "react";

import { AnatomicalSkeleton } from "./anatomical-skeleton";
import { type AppView, viewHref } from "../lib/navigation";
import {
  clearDemoSessionCache,
  readDemoSessionCache,
  writeDemoSessionCache,
  type DemoSessionCache,
} from "../lib/demo-session-cache";
import { boneSites, type BoneSiteId } from "../lib/preview-data";

const SUBJECT_ID = "30000000-0000-4000-8000-000000000001";
const MAX_UPLOAD_BYTES = 10_000_000;
const API_BASE_URL =
  process.env.NEXT_PUBLIC_BONETWIN_API_URL ?? "http://127.0.0.1:8000";
const LOCAL_API = /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(
  API_BASE_URL,
);

type DashboardApi = Pick<BoneTwinClient, "dashboard">;

export async function loadDashboardData(
  api: DashboardApi,
  subjectId = SUBJECT_ID,
): Promise<DashboardSnapshot> {
  return api.dashboard(subjectId);
}

const navItems: Array<{ id: AppView; label: string; icon: string }> = [
  { id: "overview", label: "Overview", icon: "grid" },
  { id: "report", label: "Parsed report", icon: "document" },
  { id: "trace", label: "Memory trace", icon: "memory" },
  { id: "tasks", label: "Review tasks", icon: "check" },
  { id: "transparency", label: "System", icon: "layers" },
];

function Icon({
  name,
  className = "size-5",
}: {
  name: string;
  className?: string;
}) {
  const paths: Record<string, React.ReactNode> = {
    grid: (
      <path d="M4 4h6v7H4V4Zm10 0h6v4h-6V4ZM4 15h6v5H4v-5Zm10-3h6v8h-6v-8Z" />
    ),
    document: <path d="M6 3h9l4 4v14H6V3Zm9 0v5h4M9 12h7M9 16h5" />,
    memory: (
      <path d="M12 3a4 4 0 0 0-4 4v1a4 4 0 0 0-2 7.46A4.5 4.5 0 0 0 10.5 21H12V3Zm0 0a4 4 0 0 1 4 4v1a4 4 0 0 1 2 7.46A4.5 4.5 0 0 1 13.5 21H12" />
    ),
    check: <path d="M9 11.5 11 14l4.5-5M5 4h14v16H5V4Z" />,
    layers: <path d="m12 3 9 5-9 5-9-5 9-5Zm-9 10 9 5 9-5M3 17l9 5 9-5" />,
    refresh: (
      <path d="M20 6v5h-5M4 18v-5h5m9.5-5A7 7 0 0 0 6 6.5L4 11m16 2-2 4.5A7 7 0 0 1 5.5 16" />
    ),
    arrow: <path d="m9 18 6-6-6-6" />,
    shield: (
      <path d="M12 3 5 6v5c0 4.6 2.7 8.2 7 10 4.3-1.8 7-5.4 7-10V6l-7-3Zm-2.5 9 1.7 1.7 3.6-4" />
    ),
    spark: (
      <path d="m12 3 1.4 4.6L18 9l-4.6 1.4L12 15l-1.4-4.6L6 9l4.6-1.4L12 3Zm6 11 .8 2.2L21 17l-2.2.8L18 20l-.8-2.2L15 17l2.2-.8L18 14Z" />
    ),
    close: <path d="m6 6 12 12M18 6 6 18" />,
  };
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span className="relative grid size-10 place-items-center rounded-2xl bg-[#123d3a] text-white shadow-[0_10px_28px_rgba(18,61,58,.24)]">
        <span className="absolute h-4 w-2 rotate-45 rounded-full border-2 border-white" />
        <span className="absolute h-2 w-4 -rotate-45 rounded-full border-2 border-white" />
      </span>
      <div>
        <p className="font-semibold tracking-tight text-slate-950">BoneTwin</p>
        <p className="text-[9px] font-bold uppercase tracking-[.2em] text-[#65918b]">
          trusted memory
        </p>
      </div>
    </div>
  );
}

function Panel({
  children,
  className = "",
  id,
}: {
  children: React.ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={`rounded-[26px] border border-white/90 bg-white shadow-[0_18px_60px_rgba(29,65,60,.075)] ${className}`}
    >
      {children}
    </section>
  );
}

function Badge({
  children,
  tone = "teal",
}: {
  children: React.ReactNode;
  tone?: "teal" | "amber" | "slate" | "blue" | "red";
}) {
  const tones = {
    teal: "border-emerald-200 bg-emerald-50 text-emerald-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    slate: "border-slate-200 bg-slate-50 text-slate-600",
    blue: "border-sky-200 bg-sky-50 text-sky-700",
    red: "border-rose-200 bg-rose-50 text-rose-700",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.08em] ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function BoneSitePreview({
  selected,
  onSelect,
  timeline,
  latestReport,
}: {
  selected: BoneSiteId;
  onSelect: (site: BoneSiteId) => void;
  timeline: Timeline | null;
  latestReport: Report | null;
}) {
  const sites = displayedBoneSites(timeline, latestReport);
  const site = sites.find((item) => item.id === selected) ?? sites[0];
  return (
    <Panel className="overflow-hidden">
      <div className="flex items-start justify-between px-6 pt-6">
        <div>
          <p className="eyebrow">Anatomical overview</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">
            Bone site preview
          </h2>
        </div>
        <Badge>4 sites</Badge>
      </div>
      <div className="grid items-center px-3 sm:grid-cols-[minmax(0,1fr)_170px]">
        <div className="relative mx-auto w-full max-w-[360px]">
          <AnatomicalSkeleton selected={selected} />
          {sites.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-label={`Select ${item.label}`}
              aria-pressed={selected === item.id}
              onClick={() => onSelect(item.id)}
              style={{ left: item.position.left, top: item.position.top }}
              className={`absolute grid size-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-4 border-white shadow-lg transition hover:scale-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f766e] ${selected === item.id ? "bg-[#2f766e]" : "bg-[#9bbdb5]"}`}
            >
              <span className="size-1.5 rounded-full bg-white" />
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2 px-2 pb-4 sm:grid-cols-1 sm:px-0">
          {sites.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={`rounded-2xl border p-3 text-left transition ${selected === item.id ? "border-[#8db4ac] bg-[#eef7f4]" : "border-slate-100 bg-slate-50 hover:bg-white"}`}
            >
              <span className="block text-xs font-semibold text-slate-800">
                {item.shortLabel}
              </span>
              <span className="mt-1 block text-[10px] text-slate-400">
                {item.status}
              </span>
            </button>
          ))}
        </div>
      </div>
      <div className="border-t border-slate-100 bg-[#fbfcfc] px-6 py-5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold">{site.label}</h3>
          <Badge
            tone={
              site.status === "Excluded"
                ? "amber"
                : site.status === "Review"
                  ? "blue"
                  : site.status === "Missing"
                    ? "slate"
                    : "teal"
            }
          >
            {site.status}
          </Badge>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-4">
          {[
            ["BMD", site.bmd, site.bmd === "—" ? "" : "g/cm²"],
            ["T-score", site.tScore, ""],
            ["Since prior", site.change, ""],
          ].map(([label, value, unit]) => (
            <div key={label}>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {label}
              </p>
              <p className="mt-1 text-lg font-semibold">
                {value}{" "}
                <span className="text-[9px] font-medium text-slate-400">
                  {unit}
                </span>
              </p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          {site.statusDetail}
        </p>
      </div>
    </Panel>
  );
}

function displayedBoneSites(
  timeline: Timeline | null,
  latestReport: Report | null,
) {
  const reports = [...(timeline?.reports ?? [])];
  if (
    latestReport &&
    !reports.some((report) => report.id === latestReport.id)
  ) {
    reports.push(latestReport);
  }
  reports.sort((left, right) => right.scan_date.localeCompare(left.scan_date));
  const matchMeasurement = (site: BoneSiteId, measurement: Measurement) =>
    ({
      "left-total-hip": measurement.region === "TOTAL_HIP",
      "femoral-neck": measurement.region === "FEMORAL_NECK",
      "lumbar-spine": measurement.region === "L1_L4",
      forearm: measurement.skeletal_site === "FOREARM",
    })[site];

  return boneSites.map((definition) => {
    const history = reports.flatMap((report) =>
      report.measurements
        .filter((measurement) => matchMeasurement(definition.id, measurement))
        .map((measurement) => ({ report, measurement })),
    );
    const latest = history[0];
    const prior = history[1];
    if (!latest) {
      return {
        ...definition,
        bmd: "-",
        tScore: "-",
        change: "Missing",
        status: "Missing" as const,
        statusDetail:
          "No uploaded or stored measurement is available for this site.",
      };
    }
    const status = !latest.measurement.usable_for_longitudinal
      ? ("Excluded" as const)
      : latest.measurement.confidence < 0.9
        ? ("Review" as const)
        : ("Verified" as const);
    const change = prior
      ? `${(((latest.measurement.bmd_g_cm2 - prior.measurement.bmd_g_cm2) / prior.measurement.bmd_g_cm2) * 100).toFixed(1)}%`
      : "Baseline";
    return {
      ...definition,
      bmd: latest.measurement.bmd_g_cm2.toFixed(3),
      tScore: latest.measurement.t_score.toFixed(1),
      change,
      status,
      statusDetail:
        status === "Excluded"
          ? "The uploaded source marks this site for review instead of longitudinal use."
          : status === "Review"
            ? "The extracted value is source-backed but below the automatic confidence threshold."
            : `Source-backed measurement from ${latest.report.scan_date}.`,
    };
  });
}

export function TimelinePanel({ timeline }: { timeline: Timeline | null }) {
  const points = (timeline?.reports ?? [])
    .flatMap((report) =>
      report.measurements
        .filter((item) => item.region === "TOTAL_HIP" && item.side === "LEFT")
        .map((item) => ({
          id: item.id,
          date: report.scan_date,
          value: item.bmd_g_cm2,
          tScore: item.t_score,
        })),
    )
    .sort((a, b) => a.date.localeCompare(b.date));
  const values = points;
  const latest = values.at(-1);
  const coords = values.map((point, index) => ({
    ...point,
    x: 28 + (index * 256) / Math.max(values.length - 1, 1),
    y: 32 + (0.79 - point.value) * 1050,
  }));
  const path = coords
    .map((point, index) => `${index ? "L" : "M"}${point.x} ${point.y}`)
    .join(" ");
  return (
    <Panel className="p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Accessible longitudinal view</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">
            Left total hip
          </h2>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-semibold uppercase text-slate-400">
            Latest BMD
          </p>
          <p className="text-xl font-semibold">
            {latest ? latest.value.toFixed(3) : "--"}{" "}
            <span className="text-[9px] text-slate-400">
              {latest ? "g/cm²" : "no source data"}
            </span>
          </p>
        </div>
      </div>
      {values.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-[#f5f9f7] p-7 text-center">
          <p className="text-sm font-semibold text-slate-700">
            No uploaded hip measurements
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Process a fully de-identified DXA PDF to populate the chart from
            stored source evidence.
          </p>
          <a
            href="/demo#upload-report"
            className="mt-4 rounded-xl bg-[#123d3a] px-4 py-2.5 text-xs font-semibold text-white"
          >
            Upload a report
          </a>
        </div>
      ) : (
        <>
          <div className="mt-5 rounded-2xl bg-[#f5f9f7] p-3">
            <svg
              role="img"
              aria-label="Left total hip source values over time"
              viewBox="0 0 312 142"
              className="h-40 w-full"
            >
              {[36, 76, 116].map((y) => (
                <line
                  key={y}
                  x1="16"
                  x2="296"
                  y1={y}
                  y2={y}
                  stroke="#dce8e4"
                  strokeDasharray="3 5"
                />
              ))}
              <path
                d={path}
                fill="none"
                stroke="#2f766e"
                strokeWidth="3"
                strokeLinecap="round"
              />
              {coords.map((point, index) => (
                <g key={point.id}>
                  <circle
                    cx={point.x}
                    cy={point.y}
                    r={index === coords.length - 1 ? 7 : 5}
                    fill={index === coords.length - 1 ? "#2f766e" : "white"}
                    stroke="#2f766e"
                    strokeWidth="3"
                  />
                  <text
                    x={point.x}
                    y="138"
                    textAnchor="middle"
                    className="fill-slate-400 text-[9px] font-semibold"
                  >
                    {point.date.slice(0, 4)}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <table className="mt-4 w-full text-left text-xs">
            <caption className="sr-only">
              Text alternative for left total hip chart
            </caption>
            <thead className="text-[9px] uppercase tracking-wider text-slate-400">
              <tr>
                <th className="pb-2">Report date</th>
                <th className="pb-2">BMD</th>
                <th className="pb-2">T-score</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {values.map((point) => (
                <tr key={point.id}>
                  <td className="py-2.5 font-medium">
                    {new Date(`${point.date}T00:00:00`).toLocaleDateString()}
                  </td>
                  <td className="py-2.5">{point.value.toFixed(3)}</td>
                  <td className="py-2.5">{point.tScore.toFixed(1)}</td>
                  <td className="py-2.5">
                    <Badge>Verified</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Panel>
  );
}

export function ProcessingConsole({
  events,
  busy,
}: {
  events: ProcessingEvent[];
  busy: boolean;
}) {
  return (
    <section className="overflow-hidden rounded-[26px] border border-slate-800 bg-[#071411] text-slate-200 shadow-[0_22px_60px_rgba(7,20,17,.24)]">
      <div className="flex items-center justify-between border-b border-white/10 bg-[#0b1e1a] px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-rose-400" />
          <span className="size-2.5 rounded-full bg-amber-300" />
          <span className="size-2.5 rounded-full bg-emerald-400" />
        </div>
        <p className="font-mono text-[10px] uppercase tracking-[.16em] text-emerald-200/70">
          Backend processing trace
        </p>
      </div>
      <div
        aria-live="polite"
        className="min-h-[290px] space-y-3 overflow-y-auto p-5 font-mono text-[11px] leading-5"
      >
        <p className="text-emerald-300">$ bonetwin workflow --source-backed</p>
        {events.length === 0 ? (
          <div className="space-y-2 text-slate-500">
            <p>[idle] No backend operation has been requested.</p>
            <p>
              [ready] Upload a report or run Trusted Comparison to see real
              service events.
            </p>
          </div>
        ) : (
          events.map((event) => {
            const serviceTone = event.service.includes("CockroachDB")
              ? "text-cyan-300"
              : event.service.includes("Bedrock") ||
                  event.service.includes("AWS")
                ? "text-amber-300"
                : "text-emerald-300";
            const statusTone =
              event.status === "FAILED"
                ? "text-rose-300"
                : event.status === "SAFE_FALLBACK"
                  ? "text-amber-300"
                  : event.status === "RUNNING"
                    ? "text-sky-300"
                    : "text-emerald-300";
            return (
              <div key={event.id} className="border-l border-white/10 pl-3">
                <p>
                  <span className={statusTone}>
                    [{event.status.toLowerCase()}]
                  </span>{" "}
                  <span className={serviceTone}>{event.service}</span>{" "}
                  <span className="text-slate-300">:: {event.operation}</span>
                </p>
                <p className="text-slate-500">{event.detail}</p>
              </div>
            );
          })
        )}
        {busy && <p className="animate-pulse text-sky-300">_ processing</p>}
      </div>
      <div className="border-t border-white/10 px-5 py-3 text-[10px] text-slate-500">
        Completed entries are returned by the active backend contract; no cloud
        service is claimed when a local adapter is used.
      </div>
    </section>
  );
}

function Overview({
  timeline,
  latestReport,
  processingEvents,
  onLoadRecord,
  onRun,
  onUploadSelected,
  selectedFile,
  onFileChange,
  onDemoUpload,
  uploadKey,
  busy,
}: {
  timeline: Timeline | null;
  latestReport: Report | null;
  processingEvents: ProcessingEvent[];
  onLoadRecord: () => void;
  onRun: () => void;
  onUploadSelected: () => void;
  selectedFile: File | null;
  onFileChange: (file: File | null) => void;
  onDemoUpload: (report: DemoReportKey) => void;
  uploadKey: string;
  busy: boolean;
}) {
  const [site, setSite] = useState<BoneSiteId>("left-total-hip");
  useEffect(() => {
    if (latestReport) setSite("left-total-hip");
  }, [latestReport]);
  const latestDate = timeline?.subject.latest_scan_date
    ? new Date(`${timeline.subject.latest_scan_date}T00:00:00`)
    : null;
  return (
    <>
      {timeline === null && (
        <Panel className="mb-5 flex flex-col justify-between gap-4 border-[#cfe2dd] bg-[#f7fbfa] p-5 sm:flex-row sm:items-center">
          <div>
            <p className="eyebrow">Ready on demand</p>
            <h2 className="mt-1 text-lg font-semibold">
              Load this record when you need it
            </h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              No cloud request is made when the dashboard opens. This single
              action loads and caches the record for this browser session.
            </p>
          </div>
          <button
            type="button"
            onClick={onLoadRecord}
            disabled={busy}
            className="shrink-0 rounded-xl bg-[#123d3a] px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {busy ? "Loading…" : "Load record"}
          </button>
        </Panel>
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          [
            "Latest scan",
            latestDate
              ? latestDate.toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })
              : "—",
            latestDate
              ? `${latestDate.getFullYear()} · DXA BMD`
              : "Load record to view",
            "teal",
          ],
          [
            "Trusted memories",
            timeline === null
              ? "—"
              : String(
                  timeline.memories.filter(
                    (item) => item.verification_status === "VERIFIED",
                  ).length,
                ),
            timeline === null
              ? "Load record to view"
              : "Source-backed & filtered",
            "blue",
          ],
          [
            "Open reviews",
            timeline === null ? "—" : String(timeline.subject.open_task_count),
            timeline === null
              ? "Load record to view"
              : "Human approval required",
            "amber",
          ],
        ].map(([label, value, detail, tone]) => (
          <Panel key={label} className="p-5">
            <div
              className={`h-1.5 w-10 rounded-full ${tone === "teal" ? "bg-emerald-300" : tone === "blue" ? "bg-sky-300" : "bg-amber-300"}`}
            />
            <p className="mt-4 text-[10px] font-bold uppercase tracking-[.14em] text-slate-400">
              {label}
            </p>
            <p className="mt-1 text-2xl font-semibold tracking-tight">
              {value}
            </p>
            <p className="mt-1 text-xs text-slate-500">{detail}</p>
          </Panel>
        ))}
      </div>
      <Panel className="mt-5 scroll-mt-24 p-5 sm:p-6" id="upload-report">
        <div className="grid items-center gap-5 lg:grid-cols-[.8fr_1.2fr]">
          <div>
            <p className="eyebrow">Add source evidence</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">
              Upload a DXA report
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Use a generated demo or select a fully de-identified PDF.
              Successful processing refreshes the anatomical preview; the full
              extraction remains available under Parsed report.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(
                [
                  { key: 2019, label: "2019" },
                  { key: 2022, label: "2022" },
                  { key: 2026, label: "Apr 2026" },
                  { key: "2026-08-16", label: "Today" },
                ] as Array<{ key: DemoReportKey; label: string }>
              ).map((report) => (
                <button
                  key={report.key}
                  type="button"
                  onClick={() => onDemoUpload(report.key)}
                  disabled={busy}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-[#2f766e] hover:border-[#8db4ac] hover:bg-white disabled:opacity-50"
                >
                  Process {report.label} demo
                </button>
              ))}
            </div>
          </div>
          <NativePdfPicker
            inputId="overview-pdf-upload"
            uploadKey={uploadKey}
            selectedFile={selectedFile}
            busy={busy}
            onFileChange={onFileChange}
            onUpload={onUploadSelected}
          />
        </div>
      </Panel>
      <div className="mt-5 grid items-start gap-5 xl:grid-cols-[1.04fr_.96fr]">
        <BoneSitePreview
          selected={site}
          onSelect={setSite}
          timeline={timeline}
          latestReport={latestReport}
        />
        <div className="grid gap-5">
          <ProcessingConsole events={processingEvents} busy={busy} />
          <section className="overflow-hidden rounded-[26px] bg-[#123d3a] p-6 text-white shadow-[0_22px_60px_rgba(18,61,58,.2)]">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#a5ccc4]">
                  Trusted comparison
                </p>
                <h2 className="mt-1 text-xl font-semibold">
                  Ask memory, not just the latest report
                </h2>
              </div>
              <span className="grid size-10 place-items-center rounded-2xl bg-white/10">
                <Icon name="spark" />
              </span>
            </div>
            <p className="mt-4 text-sm leading-6 text-white/65">
              BoneTwin retrieves verified corrections, comparable sites, open
              tasks, and source evidence before proposing a human-reviewed next
              step.
            </p>
            <button
              type="button"
              onClick={onRun}
              disabled={busy}
              className="mt-5 w-full rounded-xl bg-white px-4 py-3 text-sm font-semibold text-[#123d3a] transition hover:bg-[#e9f5f1] disabled:opacity-60"
            >
              {busy ? "Building evidence bundle…" : "Run trusted comparison"}
            </button>
          </section>
        </div>
      </div>
    </>
  );
}

export function NativePdfPicker({
  inputId,
  uploadKey,
  selectedFile,
  busy,
  onFileChange,
  onUpload,
}: {
  inputId: string;
  uploadKey: string;
  selectedFile: File | null;
  busy: boolean;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
}) {
  return (
    <form
      action="/api/local-upload"
      method="post"
      encType="multipart/form-data"
      onSubmit={(event) => {
        if (!selectedFile) return;
        event.preventDefault();
        onUpload();
      }}
      className="rounded-2xl border border-[#b8d3cd] bg-[#f4faf8] p-4 text-left"
    >
      <input type="hidden" name="idempotency_key" value={uploadKey} />
      <label
        htmlFor={inputId}
        className="text-[10px] font-bold uppercase tracking-wider text-[#56857f]"
      >
        PDF file
      </label>
      <input
        id={inputId}
        name="report"
        type="file"
        accept="application/pdf,.pdf"
        required
        onChange={(event) =>
          onFileChange(event.currentTarget.files?.item(0) ?? null)
        }
        className="mt-2 block w-full cursor-pointer rounded-xl border border-slate-200 bg-white text-xs text-slate-600 file:mr-3 file:cursor-pointer file:border-0 file:border-r file:border-slate-200 file:bg-white file:px-4 file:py-3 file:text-xs file:font-semibold file:text-[#245f59] hover:border-[#8db4ac]"
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          {selectedFile
            ? `${selectedFile.name} · ${Math.ceil(selectedFile.size / 1024)} KB`
            : "PDF only · 10 MB maximum · no real patient data"}
        </p>
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-[#123d3a] px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-[#123d3a]/15 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Processing report…" : "Upload and process"}
        </button>
      </div>
    </form>
  );
}

function ParsedReportScreen({ document }: { document: DocumentStatus | null }) {
  const report = document?.report;
  return (
    <Panel className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 p-6 sm:p-8">
        <div>
          <p className="eyebrow">Source-backed extraction</p>
          <h2 className="mt-1 text-2xl font-semibold">Parsed report review</h2>
          <p className="mt-2 text-sm text-slate-500">
            {report
              ? `${report.facility_pseudonym} · ${new Date(`${report.scan_date}T00:00:00`).toLocaleDateString()}`
              : "Process the report to populate this review."}
          </p>
        </div>
        {report && (
          <div className="flex gap-2">
            <Badge>Ready</Badge>
            <Badge tone="blue">
              {Math.round(report.extraction_confidence * 100)}% confidence
            </Badge>
          </div>
        )}
      </div>
      {!report ? (
        <div className="grid min-h-80 place-items-center p-8 text-center">
          <div>
            <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-400">
              <Icon name="document" />
            </span>
            <p className="mt-4 font-semibold">No newly parsed report yet</p>
            <p className="mt-1 text-sm text-slate-400">
              Use Upload report to run the pipeline.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto p-5 sm:p-7">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-[10px] uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="pb-3">Site</th>
                  <th className="pb-3">BMD</th>
                  <th className="pb-3">T-score</th>
                  <th className="pb-3">Confidence</th>
                  <th className="pb-3">Evidence</th>
                  <th className="pb-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.measurements.map((measurement) => (
                  <tr key={measurement.id}>
                    <td className="py-4">
                      <p className="font-semibold">
                        {measurement.region.replaceAll("_", " ")}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {measurement.side ?? "Central"} · page{" "}
                        {measurement.source_page}
                      </p>
                    </td>
                    <td className="py-4 font-medium">
                      {measurement.bmd_g_cm2.toFixed(3)}{" "}
                      <span className="text-[10px] text-slate-400">g/cm²</span>
                    </td>
                    <td className="py-4">{measurement.t_score.toFixed(1)}</td>
                    <td className="py-4">
                      {Math.round(measurement.confidence * 100)}%
                    </td>
                    <td className="max-w-[260px] py-4 text-xs text-slate-500">
                      {measurement.source_text}
                    </td>
                    <td className="py-4">
                      <Badge
                        tone={
                          measurement.usable_for_longitudinal ? "blue" : "amber"
                        }
                      >
                        {measurement.usable_for_longitudinal
                          ? "Review"
                          : "Excluded"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid gap-3 border-t border-slate-100 bg-[#fbfcfc] p-6 text-xs sm:grid-cols-3">
            <div>
              <p className="font-bold uppercase tracking-wider text-slate-400">
                Parser
              </p>
              <p className="mt-1 font-medium">
                {report.parser_name} v{report.parser_version}
              </p>
            </div>
            <div>
              <p className="font-bold uppercase tracking-wider text-slate-400">
                Scanner
              </p>
              <p className="mt-1 font-medium">
                {report.scanner_manufacturer} · {report.scanner_model}
              </p>
            </div>
            <div>
              <p className="font-bold uppercase tracking-wider text-slate-400">
                Original evidence
              </p>
              <p className="mt-1 font-medium">
                Preserved · append-only corrections
              </p>
            </div>
          </div>
        </>
      )}
    </Panel>
  );
}

function TraceScreen({
  run,
  onRun,
  busy,
}: {
  run: AgentRun | null;
  onRun: () => void;
  busy: boolean;
}) {
  if (!run)
    return (
      <EmptyAction
        title="No comparison run yet"
        detail="Run a trusted comparison to see exactly which memories were used or excluded."
        action="Run comparison"
        onClick={onRun}
        busy={busy}
      />
    );
  const used = run.memory_trace.filter(
    (item) => item.disposition !== "EXCLUDED",
  );
  const excluded = run.memory_trace.filter(
    (item) => item.disposition === "EXCLUDED",
  );
  return (
    <div className="grid gap-5 xl:grid-cols-[.95fr_1.05fr]">
      <div className="space-y-5">
        <section className="rounded-[26px] bg-[#123d3a] p-6 text-white shadow-[0_22px_60px_rgba(18,61,58,.2)] sm:p-8">
          <div className="flex items-center gap-2 text-[#9ec8c0]">
            <Icon name="spark" className="size-4" />
            <p className="text-[10px] font-bold uppercase tracking-[.18em]">
              Validated agent decision
            </p>
          </div>
          <h2 className="mt-4 text-2xl font-semibold tracking-tight">
            Comparison prepared
          </h2>
          <p className="mt-4 text-sm leading-6 text-white/75">
            {run.decision.summary}
          </p>
          <div className="mt-5 rounded-2xl bg-white/[.08] p-4">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[#9ec8c0]">
              Uncertainty
            </p>
            <p className="mt-2 text-xs leading-5 text-white/65">
              {run.decision.uncertainty}
            </p>
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs text-white/50">
            <Icon name="shield" className="size-4" />
            <span>{run.decision.safety_notice}</span>
          </div>
        </section>
        <Panel className="p-6">
          <p className="eyebrow">Memory that changed behavior</p>
          <h3 className="mt-2 text-lg font-semibold">
            {run.decision.memory_impact_statement}
          </h3>
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700">
              Counterfactual
            </p>
            <p className="mt-2 text-xs leading-5 text-amber-900/70">
              {run.decision.counterfactual_without_key_memory}
            </p>
          </div>
          {run.persisted_review_applied && (
            <div className="mt-4 flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-xs font-semibold text-emerald-700">
              <Icon name="check" className="size-4" /> New-session proof: prior
              approval was retrieved and reused.
            </div>
          )}
        </Panel>
      </div>
      <Panel className="p-6 sm:p-8">
        <div className="flex items-end justify-between">
          <div>
            <p className="eyebrow">Memory Impact Trace</p>
            <h2 className="mt-1 text-xl font-semibold">Evidence disposition</h2>
          </div>
          <Badge tone="blue">{run.memory_trace.length} candidates</Badge>
        </div>
        <TraceGroup title="Used & supporting" items={used} />
        <TraceGroup title="Excluded with reason" items={excluded} excluded />
      </Panel>
    </div>
  );
}

function TraceGroup({
  title,
  items,
  excluded = false,
}: {
  title: string;
  items: MemoryTraceItem[];
  excluded?: boolean;
}) {
  return (
    <div className="mt-6">
      <p className="text-[10px] font-bold uppercase tracking-[.14em] text-slate-400">
        {title}
      </p>
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <article
            key={item.id}
            className={`rounded-2xl border p-4 ${excluded ? "border-slate-200 bg-slate-50/70" : "border-[#d8e9e4] bg-[#f4faf8]"}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Badge
                tone={
                  excluded
                    ? "slate"
                    : item.disposition === "USED"
                      ? "teal"
                      : "blue"
                }
              >
                {item.disposition}
              </Badge>
              <span className="text-[10px] text-slate-400">
                Trust {item.trust_score.toFixed(3)}
              </span>
            </div>
            <h3 className="mt-3 text-sm font-semibold">{item.title}</h3>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              {excluded ? item.disposition_reason : item.content}
            </p>
            <p className="mt-2 text-[10px] font-medium text-slate-400">
              {item.source_label} · {item.verification_status}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}

function TasksScreen({
  tasks,
  loaded,
  busy,
  onLoad,
  onResolve,
  onRun,
}: {
  tasks: ReviewTask[];
  loaded: boolean;
  busy: boolean;
  onLoad: () => void;
  onResolve: (
    task: ReviewTask,
    action: "approve" | "correct" | "reject",
  ) => void;
  onRun: () => void;
}) {
  if (!loaded)
    return (
      <EmptyAction
        title="Review tasks are ready on demand"
        detail="Open this queue only when you need it. BoneTwin will make one request and cache the result for this browser session."
        action="Load review tasks"
        onClick={onLoad}
        busy={busy}
      />
    );
  if (!tasks.length)
    return (
      <EmptyAction
        title="No review tasks yet"
        detail="Run a comparison to create a bounded action for clinician review."
        action="Run comparison"
        onClick={onRun}
        busy={busy}
      />
    );
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      <div className="space-y-4">
        {tasks.map((task) => (
          <Panel key={task.id} className="p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="eyebrow">
                  {task.action_type.replaceAll("_", " ")}
                </p>
                <h2 className="mt-1 text-xl font-semibold">{task.title}</h2>
              </div>
              <Badge
                tone={
                  task.status === "APPLIED"
                    ? "teal"
                    : task.status === "REJECTED"
                      ? "red"
                      : "amber"
                }
              >
                {task.status}
              </Badge>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-500">
              Review the source-backed scanner context. This action changes
              workflow memory only; it does not change a source measurement or
              provide treatment guidance.
            </p>
            <div className="mt-5 flex flex-wrap gap-2 text-xs">
              <span className="rounded-lg bg-slate-100 px-3 py-2">
                {task.evidence_memory_ids.length} evidence memories
              </span>
              <span className="rounded-lg bg-slate-100 px-3 py-2">
                Requires {task.requires_role.toLowerCase()}
              </span>
            </div>
            {task.status === "AWAITING_REVIEW" && (
              <div className="mt-6 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onResolve(task, "approve")}
                  className="rounded-xl bg-[#123d3a] px-4 py-2.5 text-xs font-semibold text-white"
                >
                  Approve & remember
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onResolve(task, "correct")}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold"
                >
                  Correct
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onResolve(task, "reject")}
                  className="rounded-xl px-4 py-2.5 text-xs font-semibold text-rose-600"
                >
                  Reject
                </button>
              </div>
            )}
            {task.resolution_note && (
              <p className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
                Review note: {task.resolution_note}
              </p>
            )}
          </Panel>
        ))}
      </div>
      <Panel className="h-fit p-6">
        <span className="grid size-11 place-items-center rounded-2xl bg-[#e5f3ef] text-[#2f766e]">
          <Icon name="shield" />
        </span>
        <h3 className="mt-4 font-semibold">Human approval boundary</h3>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          The agent can propose this allowlisted action, but only application
          code authorizes the reviewer and writes the durable decision.
        </p>
        <ul className="mt-4 space-y-3 text-xs text-slate-600">
          {[
            "Idempotent action key",
            "Append-only review event",
            "Verified memory on approval",
            "Structured audit record",
          ].map((item) => (
            <li key={item} className="flex items-center gap-2">
              <span className="grid size-5 place-items-center rounded-full bg-emerald-100 text-[10px] text-emerald-700">
                ✓
              </span>
              {item}
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

export function TransparencyScreen({
  data,
  timeline = null,
  loaded = true,
  busy = false,
  recordBusy = false,
  onLoad = () => undefined,
  onLoadRecords = () => undefined,
  onDeleteRecord = () => undefined,
}: {
  data: Transparency | null;
  timeline?: Timeline | null;
  loaded?: boolean;
  busy?: boolean;
  recordBusy?: boolean;
  onLoad?: () => void;
  onLoadRecords?: () => void;
  onDeleteRecord?: (documentId: string) => void;
}) {
  const [confirmDocumentId, setConfirmDocumentId] = useState<string | null>(
    null,
  );
  const groups = [
    ["Document workflow", data?.document_pipeline ?? []],
    ["Memory Trust Engine", data?.memory_engine ?? []],
  ] as const;
  return (
    <div className="space-y-5">
      <Panel className="p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Integration transparency</p>
            <h2 className="mt-1 text-2xl font-semibold">
              What is running in this demo
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              {!loaded
                ? "Runtime details have not been requested. Load them only when you want to inspect the deployment."
                : data === null
                  ? "Runtime details are unavailable because the API could not be reached. No deployment mode is inferred from this fallback."
                  : data.mode === "AWS"
                    ? "This hosted demo runs on AWS Lambda with encrypted Amazon S3 storage and Amazon Bedrock. CockroachDB Cloud is the durable system of record, with allowlisted LangChain MCP retrieval."
                    : data.mode === "LOCAL_CLOUD_MCP"
                      ? "This local UI and API store durable state in CockroachDB Cloud. LangChain calls the managed MCP select_query tool to gate trusted memory retrieval; authorized transactional writes remain in application code."
                      : data.mode === "LOCAL_BEDROCK"
                        ? "This local app is calling Amazon Bedrock for Titan embeddings and validated agent decisions. Application authorization and CockroachDB commits remain local."
                        : "The local workflow uses deterministic offline adapters with the same validated contracts planned for AWS. Cloud usage is never implied when credentials are absent."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="blue">
              {!loaded
                ? "READY ON DEMAND"
                : (data?.mode ?? "STATUS UNAVAILABLE")}
            </Badge>
            {!loaded && (
              <button
                type="button"
                onClick={onLoad}
                disabled={busy}
                className="rounded-xl bg-[#123d3a] px-4 py-2.5 text-xs font-semibold text-white disabled:opacity-60"
              >
                {busy ? "Loading…" : "Load system status"}
              </button>
            )}
          </div>
        </div>
      </Panel>
      <Panel className="p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Demo record controls</p>
            <h3 className="mt-1 text-xl font-semibold">
              Remove one report for a clean re-upload
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              This removes only the selected report, its measurements, and its
              directly indexed evidence. Other reports and clinician corrections
              remain. An audit tombstone records the action.
            </p>
          </div>
          {timeline === null && (
            <button
              type="button"
              onClick={onLoadRecords}
              disabled={recordBusy}
              className="rounded-xl border border-[#8db4ac] bg-white px-4 py-2.5 text-xs font-semibold text-[#2f766e] disabled:opacity-60"
            >
              {recordBusy ? "Loading…" : "Load report records"}
            </button>
          )}
        </div>
        {timeline !== null && (
          <div className="mt-5 space-y-3">
            {timeline.reports.length === 0 ? (
              <div className="rounded-2xl bg-slate-50 p-5 text-sm text-slate-500">
                No uploaded reports remain. Return to Overview to upload one.
              </div>
            ) : (
              timeline.reports.map((report) => {
                const confirming = confirmDocumentId === report.document_id;
                return (
                  <div
                    key={report.document_id}
                    className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-800">
                        {new Date(
                          `${report.scan_date}T00:00:00`,
                        ).toLocaleDateString(undefined, {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        })}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {report.report_type} · {report.scanner_manufacturer}{" "}
                        {report.scanner_model} · {report.measurements.length}{" "}
                        measurements
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {confirming ? (
                        <>
                          <button
                            type="button"
                            onClick={() => setConfirmDocumentId(null)}
                            disabled={recordBusy}
                            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-600 disabled:opacity-60"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setConfirmDocumentId(null);
                              onDeleteRecord(report.document_id);
                            }}
                            disabled={recordBusy}
                            className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
                          >
                            {recordBusy ? "Deleting…" : "Confirm delete"}
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() =>
                            setConfirmDocumentId(report.document_id)
                          }
                          disabled={recordBusy}
                          className="rounded-xl border border-rose-200 bg-white px-4 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-60"
                        >
                          Delete record
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </Panel>
      <div className="grid gap-5 lg:grid-cols-2">
        {groups.map(([title, items]) => (
          <Panel key={title} className="p-6">
            <h3 className="font-semibold">{title}</h3>
            <div className="mt-4 space-y-3">
              {items.map((item, index) => (
                <div
                  key={`${title}-${index}`}
                  className="rounded-2xl bg-slate-50 p-4"
                >
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {item.step}
                  </p>
                  <p className="mt-1 text-sm font-medium">{item.service}</p>
                </div>
              ))}
            </div>
          </Panel>
        ))}
        <Panel className="p-6">
          <h3 className="font-semibold">CockroachDB</h3>
          <div className="mt-4 space-y-3">
            {Object.entries(data?.database ?? {}).map(([key, value]) => (
              <div key={key} className="rounded-2xl bg-slate-50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  {key}
                </p>
                <p className="mt-1 text-sm">{value}</p>
              </div>
            ))}
          </div>
        </Panel>
        <Panel className="p-6">
          <h3 className="font-semibold">Agent boundary</h3>
          <div className="mt-4 space-y-3">
            {Object.entries(data?.agent ?? {}).map(([key, value]) => (
              <div key={key} className="rounded-2xl bg-slate-50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  {key}
                </p>
                <p className="mt-1 text-sm">{value}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-400">
            {data === null
              ? "Audit count unavailable"
              : `${data.audit_event_count} structured API audit events this run`}
          </p>
        </Panel>
      </div>
    </div>
  );
}

function EmptyAction({
  title,
  detail,
  action,
  onClick,
  busy,
}: {
  title: string;
  detail: string;
  action: string;
  onClick: () => void;
  busy: boolean;
}) {
  return (
    <Panel className="grid min-h-[430px] place-items-center p-8 text-center">
      <div className="max-w-md">
        <span className="mx-auto grid size-16 place-items-center rounded-[22px] bg-[#e7f3f0] text-[#2f766e]">
          <Icon name="memory" />
        </span>
        <h2 className="mt-5 text-xl font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">{detail}</p>
        <button
          type="button"
          onClick={onClick}
          disabled={busy}
          className="mt-6 rounded-xl bg-[#123d3a] px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {busy ? "Working…" : action}
        </button>
      </div>
    </Panel>
  );
}

export function ProductApp({
  initialView = "overview",
  initialDocument = null,
  initialNotice,
  uploadKey,
}: {
  initialView?: AppView;
  initialDocument?: DocumentStatus | null;
  initialNotice?: string;
  uploadKey: string;
}) {
  const api = useMemo(
    () =>
      new BoneTwinClient({
        baseUrl: API_BASE_URL,
      }),
    [],
  );
  const [view, setView] = useState<AppView>(initialView);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [document, setDocument] = useState<DocumentStatus | null>(
    initialDocument,
  );
  const [processingEvents, setProcessingEvents] = useState<ProcessingEvent[]>(
    initialDocument?.processing_events ?? [],
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [tasksLoaded, setTasksLoaded] = useState(false);
  const [transparency, setTransparency] = useState<Transparency | null>(null);
  const [transparencyLoaded, setTransparencyLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sectionLoading, setSectionLoading] = useState<AppView | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [usingSessionCache, setUsingSessionCache] = useState(false);
  const [toast, setToast] = useState<string | null>(initialNotice ?? null);
  const [sessionDialog, setSessionDialog] = useState(false);
  const [sessionCount, setSessionCount] = useState(1);
  const recordLoadPending = useRef(false);
  const sectionLoadsPending = useRef(new Set<AppView>());

  useEffect(() => {
    const cached = readDemoSessionCache(window.sessionStorage);
    if (!cached) return;
    if (cached.timeline) setTimeline(cached.timeline);
    if (cached.tasks) {
      setTasks(cached.tasks);
      setTasksLoaded(true);
    }
    if (cached.transparency) {
      setTransparency(cached.transparency);
      setTransparencyLoaded(true);
    }
    setUsingSessionCache(
      Boolean(cached.timeline || cached.tasks || cached.transparency),
    );
  }, []);

  function cachePatch(patch: Partial<Omit<DemoSessionCache, "version">>) {
    const current = readDemoSessionCache(window.sessionStorage) ?? {
      version: 1 as const,
    };
    writeDemoSessionCache(window.sessionStorage, { ...current, ...patch });
  }

  function invalidateRecordCache() {
    setTimeline(null);
    setTasks([]);
    setTasksLoaded(false);
    const next: DemoSessionCache = { version: 1 };
    if (transparencyLoaded && transparency) next.transparency = transparency;
    writeDemoSessionCache(window.sessionStorage, next);
    setUsingSessionCache(false);
  }

  function invalidateTaskCache(updatedTasks?: ReviewTask[]) {
    setTasks(updatedTasks ?? []);
    setTasksLoaded(updatedTasks !== undefined);
    let cachedTimeline = timeline;
    if (updatedTasks && timeline) {
      cachedTimeline = {
        ...timeline,
        tasks: updatedTasks,
        subject: {
          ...timeline.subject,
          open_task_count: updatedTasks.filter(
            (task) => task.status === "AWAITING_REVIEW",
          ).length,
        },
      };
      setTimeline(cachedTimeline);
    }
    const next: DemoSessionCache = { version: 1 };
    if (cachedTimeline) next.timeline = cachedTimeline;
    if (updatedTasks) next.tasks = updatedTasks;
    if (transparencyLoaded && transparency) next.transparency = transparency;
    writeDemoSessionCache(window.sessionStorage, next);
    setUsingSessionCache(false);
  }

  async function loadRecord() {
    if (recordLoadPending.current) return;
    recordLoadPending.current = true;
    setBusy(true);
    try {
      const result = await loadDashboardData(api);
      setTimeline(result.timeline);
      setTasks(result.tasks);
      setTasksLoaded(true);
      setTransparency(result.transparency);
      setTransparencyLoaded(true);
      writeDemoSessionCache(window.sessionStorage, { version: 1, ...result });
      setUsingSessionCache(false);
      setConnected(true);
    } catch (error) {
      setConnected(false);
      notify(
        error instanceof Error ? error.message : "Record could not be loaded.",
      );
    } finally {
      recordLoadPending.current = false;
      setBusy(false);
    }
  }

  async function loadSection(nextView: AppView) {
    if (sectionLoadsPending.current.has(nextView)) return;
    sectionLoadsPending.current.add(nextView);
    if (nextView === "tasks" && !tasksLoaded) {
      setSectionLoading("tasks");
      try {
        const result = await api.tasks(SUBJECT_ID);
        setTasks(result);
        setTasksLoaded(true);
        cachePatch({ tasks: result });
        setConnected(true);
      } catch (error) {
        setConnected(false);
        notify(
          error instanceof Error
            ? error.message
            : "Review tasks could not be loaded.",
        );
      } finally {
        setSectionLoading(null);
      }
    }
    if (nextView === "transparency" && !transparencyLoaded) {
      setSectionLoading("transparency");
      try {
        const result = await api.transparency();
        setTransparency(result);
        setTransparencyLoaded(true);
        cachePatch({ transparency: result });
        setConnected(true);
      } catch (error) {
        setConnected(false);
        notify(
          error instanceof Error
            ? error.message
            : "System status could not be loaded.",
        );
      } finally {
        setSectionLoading(null);
      }
    }
    sectionLoadsPending.current.delete(nextView);
  }

  async function deleteDemoRecord(documentId: string) {
    setBusy(true);
    try {
      const result = await api.deleteDemoRecord(SUBJECT_ID, documentId);
      setTimeline(result.timeline);
      setTasks(result.timeline.tasks);
      setTasksLoaded(true);
      setRun(null);
      if (document?.report?.document_id === documentId) setDocument(null);
      setProcessingEvents([
        {
          id: `record-delete-${documentId}`,
          service: transparency?.database.service ?? "Active workflow database",
          operation: "Scoped demo record deletion",
          status: "COMPLETED",
          detail:
            "Removed the selected report and direct evidence while retaining an audit tombstone.",
        },
      ]);
      const next: DemoSessionCache = {
        version: 1,
        timeline: result.timeline,
        tasks: result.timeline.tasks,
      };
      if (transparencyLoaded && transparency) next.transparency = transparency;
      writeDemoSessionCache(window.sessionStorage, next);
      setUsingSessionCache(false);
      setConnected(true);
      notify(
        `${result.scan_date ?? "Selected report"} deleted. Its PDF can now be uploaded again.`,
      );
    } catch (error) {
      notify(
        error instanceof Error ? error.message : "Record deletion failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  function navigate(nextView: AppView, load = true) {
    setView(nextView);
    window.history.replaceState(null, "", viewHref(nextView));
    if (load) void loadSection(nextView);
  }

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 3600);
  }

  function recordProcessingEvent(event: ProcessingEvent) {
    setProcessingEvents((current) => {
      const existing = current.findIndex((item) => item.id === event.id);
      if (existing < 0) return [...current, event];
      return current.map((item, index) => (index === existing ? event : item));
    });
  }

  async function processFile(file: File) {
    setBusy(true);
    setSelectedFile(file);
    setProcessingEvents([]);
    try {
      const result = await api.uploadDocument(
        SUBJECT_ID,
        file,
        recordProcessingEvent,
      );
      setDocument(result);
      setConnected(true);
      try {
        const snapshot = await loadDashboardData(api);
        setTimeline(snapshot.timeline);
        setTasks(snapshot.tasks);
        setTasksLoaded(true);
        setTransparency(snapshot.transparency);
        setTransparencyLoaded(true);
        writeDemoSessionCache(window.sessionStorage, {
          version: 1,
          ...snapshot,
        });
        recordProcessingEvent({
          id: "post-upload-dashboard",
          service: snapshot.transparency.database.service,
          operation: "Anatomical record refresh",
          status: "COMPLETED",
          detail:
            "Loaded the newly committed measurements into the bone-site preview.",
        });
      } catch {
        invalidateRecordCache();
        recordProcessingEvent({
          id: "post-upload-dashboard",
          service: "BoneTwin API",
          operation: "Anatomical record refresh",
          status: "SAFE_FALLBACK",
          detail:
            "The report is ready and shown directly; use Load record to refresh history.",
        });
      }
      notify(
        `${file.name} is ready. Anatomical source data has been refreshed.`,
      );
    } catch (error) {
      setConnected(false);
      recordProcessingEvent({
        id: "upload-failed",
        service: "BoneTwin API",
        operation: "Report processing",
        status: "FAILED",
        detail:
          error instanceof Error ? error.message : "Report processing failed.",
      });
      notify(
        error instanceof Error
          ? error.message
          : "Report workflow is unavailable.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function uploadDemo(report: DemoReportKey) {
    setBusy(true);
    try {
      const file = await api.demoDocument(report);
      await processFile(file);
    } catch (error) {
      setConnected(false);
      notify(
        error instanceof Error
          ? error.message
          : "Generated report workflow is unavailable.",
      );
      setBusy(false);
    }
  }

  function chooseFile(file: File | null) {
    if (file === null) {
      setSelectedFile(null);
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setSelectedFile(null);
      notify("Local demo uploads must be PDF files.");
      return;
    }
    if (file.size <= 0 || file.size > MAX_UPLOAD_BYTES) {
      setSelectedFile(null);
      notify("Choose a non-empty PDF no larger than 10 MB.");
      return;
    }
    setSelectedFile(file);
    setDocument(null);
  }

  async function runComparison() {
    setBusy(true);
    setProcessingEvents([
      {
        id: "comparison-cockroach-retrieval",
        service:
          transparency?.database.service ??
          (LOCAL_API ? "Configured database" : "CockroachDB Cloud"),
        operation: "Scoped trusted-memory retrieval",
        status: "RUNNING",
        detail:
          "Retrieving subject-scoped candidates and applying trust filters.",
      },
      {
        id: "comparison-bedrock-decision",
        service: LOCAL_API ? "Configured agent runtime" : "Amazon Bedrock",
        operation: "Strict structured decision",
        status: "RUNNING",
        detail:
          "Waiting for a schema-constrained, evidence-authorized response.",
      },
    ]);
    try {
      const result = await api.runComparison(SUBJECT_ID);
      setRun(result);
      setProcessingEvents(result.processing_events);
      setConnected(true);
      invalidateTaskCache();
      navigate("trace", false);
      notify(
        result.persisted_review_applied
          ? "Prior approval retrieved in this new session."
          : "Trusted comparison is ready.",
      );
    } catch (error) {
      recordProcessingEvent({
        id: "comparison-failed",
        service: "BoneTwin API",
        operation: "Trusted comparison",
        status: "FAILED",
        detail:
          error instanceof Error ? error.message : "Agent workflow failed.",
      });
      notify(
        error instanceof Error
          ? error.message
          : "Agent workflow is unavailable.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function resolve(
    task: ReviewTask,
    action: "approve" | "correct" | "reject",
  ) {
    setBusy(true);
    try {
      const payload =
        action === "correct"
          ? {
              note: "Corrected in the clinician review.",
              corrected_title: "Scanner context reviewed with source caveat",
              corrected_content:
                "Use the hip comparison with its documented scanner caveat.",
            }
          : {
              note:
                action === "approve"
                  ? "Approved in clinician review."
                  : "Rejected in clinician review.",
            };
      const updated = await api.resolveTask(task.id, action, payload);
      const updatedTasks = tasks.map((item) =>
        item.id === updated.id ? updated : item,
      );
      invalidateTaskCache(updatedTasks);
      setConnected(true);
      notify(
        action === "reject"
          ? "Task rejected and audit recorded."
          : "Review stored as durable verified memory.",
      );
    } catch (error) {
      notify(error instanceof Error ? error.message : "Review action failed.");
    } finally {
      setBusy(false);
    }
  }

  function beginNewSession() {
    clearDemoSessionCache(window.sessionStorage);
    setRun(null);
    setTimeline(null);
    setTasks([]);
    setTasksLoaded(false);
    setTransparency(null);
    setTransparencyLoaded(false);
    setUsingSessionCache(false);
    setConnected(null);
    navigate("overview", false);
    setSessionCount((count) => count + 1);
    setSessionDialog(false);
    notify(
      "New browser session started. Durable server memory was not cleared.",
    );
  }

  function logout() {
    clearDemoSessionCache(window.sessionStorage);
    window.location.assign("/");
  }

  const activeLabel =
    navItems.find((item) => item.id === view)?.label ?? "Overview";
  return (
    <div className="min-h-screen bg-[#f1f5f3] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[244px] flex-col border-r border-slate-200/80 bg-white px-4 py-5 lg:flex">
        <div className="px-2">
          <Brand />
        </div>
        <nav aria-label="Primary" className="mt-9 space-y-1">
          {navItems.map((item) => (
            <a
              key={item.id}
              href={viewHref(item.id)}
              aria-current={view === item.id ? "page" : undefined}
              onClick={(event) => {
                event.preventDefault();
                navigate(item.id);
              }}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${view === item.id ? "bg-[#e6f2ef] text-[#123d3a]" : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"}`}
            >
              <span
                className={`grid size-8 place-items-center rounded-lg ${view === item.id ? "bg-white shadow-sm" : ""}`}
              >
                <Icon name={item.icon} className="size-4" />
              </span>
              {item.label}
              {item.id === "tasks" &&
                tasks.filter((task) => task.status === "AWAITING_REVIEW")
                  .length > 0 && (
                  <span className="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                    {
                      tasks.filter((task) => task.status === "AWAITING_REVIEW")
                        .length
                    }
                  </span>
                )}
            </a>
          ))}
        </nav>
        <div className="mt-auto">
          <button
            type="button"
            onClick={() => setSessionDialog(true)}
            className="flex w-full items-center gap-3 rounded-xl border border-slate-200 p-3 text-left hover:bg-slate-50"
          >
            <span className="grid size-9 place-items-center rounded-full bg-[#dceee9] text-xs font-bold text-[#2f766e]">
              SR
            </span>
            <span>
              <span className="block text-xs font-semibold">
                Dr. Sam Rivera
              </span>
              <span className="block text-[10px] text-slate-400">
                Demo clinician · session {sessionCount}
              </span>
            </span>
            <Icon name="refresh" className="ml-auto size-4 text-slate-400" />
          </button>
          <button
            type="button"
            onClick={logout}
            className="mt-2 flex w-full items-center justify-center rounded-xl px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-50 hover:text-slate-900"
          >
            Log out
          </button>
          <p className="mt-4 px-2 text-[10px] leading-4 text-slate-400">
            Data only. Organization and review preparation—not diagnosis or
            treatment.
          </p>
        </div>
      </aside>

      <main className="min-h-screen pb-24 lg:pl-[244px] lg:pb-0">
        <header className="sticky top-0 z-20 border-b border-white/80 bg-[#f1f5f3]/90 px-4 py-4 backdrop-blur-xl sm:px-8">
          <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-3">
            <div className="lg:hidden">
              <Brand />
            </div>
            <div className="hidden lg:block">
              <p className="text-sm font-semibold">{activeLabel}</p>
              <p className="text-xs text-slate-400">SYNTH-BONE-001</p>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`hidden items-center gap-2 rounded-full border bg-white px-3 py-2 text-[10px] font-bold uppercase tracking-wider sm:flex ${connected === false ? "border-rose-200 text-rose-600" : "border-emerald-200 text-emerald-700"}`}
              >
                <span
                  className={`size-1.5 rounded-full ${connected === false ? "bg-rose-500" : "bg-emerald-500"}`}
                />
                {connected === false
                  ? "API offline"
                  : connected
                    ? LOCAL_API
                      ? "Local workflow live"
                      : "Hosted workflow live"
                    : usingSessionCache
                      ? "Session cache"
                      : "Ready on demand"}
              </span>
              <button
                type="button"
                onClick={() => setSessionDialog(true)}
                className="grid size-10 place-items-center rounded-full bg-[#dceee9] text-xs font-bold text-[#2f766e] lg:hidden"
              >
                SR
              </button>
              <a
                href="/demo#upload-report"
                onClick={(event) => {
                  event.preventDefault();
                  navigate("overview", false);
                  window.requestAnimationFrame(() => {
                    window.document
                      .getElementById("upload-report")
                      ?.scrollIntoView();
                  });
                }}
                className="rounded-xl bg-[#123d3a] px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-[#123d3a]/15"
              >
                <span className="mr-1.5 text-base">+</span> Add report
              </a>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-[1400px] px-4 pb-14 pt-6 sm:px-8 lg:pt-9">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-[#56857f]">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                Record · source-backed
              </div>
              <h1 className="mt-2 text-3xl font-semibold tracking-[-.035em] sm:text-4xl">
                {activeLabel === "Overview"
                  ? "Bone health overview"
                  : activeLabel}
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                {view === "overview"
                  ? "See the scans, evidence quality, and durable memories that shape this record."
                  : "Complete the end-to-end workflow with visible trust and human control."}
              </p>
            </div>
            <p className="text-xs text-slate-400">
              Session {sessionCount} · {LOCAL_API ? "local" : "hosted"} demo
            </p>
          </div>
          {connected === false && (
            <aside className="mt-5 flex items-center justify-between gap-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700">
              <span>
                BoneTwin cannot reach the API right now. Please retry in a
                moment.
              </span>
              <button
                type="button"
                onClick={() => void loadRecord()}
                className="font-bold"
              >
                Retry
              </button>
            </aside>
          )}
          <div className="mt-6">
            {view === "overview" && (
              <Overview
                timeline={timeline}
                latestReport={document?.report ?? null}
                processingEvents={processingEvents}
                onLoadRecord={() => void loadRecord()}
                onRun={() => void runComparison()}
                onUploadSelected={() => {
                  if (selectedFile) void processFile(selectedFile);
                }}
                selectedFile={selectedFile}
                onFileChange={chooseFile}
                onDemoUpload={(year) => void uploadDemo(year)}
                uploadKey={uploadKey}
                busy={busy}
              />
            )}
            {view === "report" && <ParsedReportScreen document={document} />}
            {view === "trace" && (
              <TraceScreen
                run={run}
                onRun={() => void runComparison()}
                busy={busy}
              />
            )}
            {view === "tasks" && (
              <TasksScreen
                tasks={tasks}
                loaded={tasksLoaded}
                busy={busy || sectionLoading === "tasks"}
                onLoad={() => void loadSection("tasks")}
                onResolve={(task, action) => void resolve(task, action)}
                onRun={() => void runComparison()}
              />
            )}
            {view === "transparency" && (
              <TransparencyScreen
                data={transparency}
                timeline={timeline}
                loaded={transparencyLoaded}
                busy={sectionLoading === "transparency"}
                recordBusy={busy}
                onLoad={() => void loadSection("transparency")}
                onLoadRecords={() => void loadRecord()}
                onDeleteRecord={(documentId) =>
                  void deleteDemoRecord(documentId)
                }
              />
            )}
          </div>
          <footer className="mt-9 flex flex-col justify-between gap-2 border-t border-slate-200/80 pt-5 text-[10px] leading-5 text-slate-400 sm:flex-row">
            <p>
              BoneTwin supports document organization and clinical-review
              preparation only.
            </p>
            <p>Phases 2–7 local workflow · data</p>
          </footer>
        </div>
      </main>

      <nav
        aria-label="Mobile navigation"
        className="fixed inset-x-3 bottom-3 z-30 grid grid-cols-5 rounded-2xl border border-white/80 bg-white/95 p-1.5 shadow-[0_18px_55px_rgba(20,54,50,.2)] backdrop-blur lg:hidden"
      >
        {navItems.map((item) => (
          <a
            key={item.id}
            href={viewHref(item.id)}
            aria-label={item.label}
            aria-current={view === item.id ? "page" : undefined}
            onClick={(event) => {
              event.preventDefault();
              navigate(item.id);
            }}
            className={`grid min-h-12 place-items-center rounded-xl ${view === item.id ? "bg-[#e6f2ef] text-[#123d3a]" : "text-slate-400"}`}
          >
            <Icon name={item.icon} className="size-4" />
            <span className="text-[8px] font-semibold">
              {item.label.split(" ")[0]}
            </span>
          </a>
        ))}
      </nav>

      {sessionDialog && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#0d2a28]/45 p-4 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="session-title"
            className="w-full max-w-md rounded-[28px] bg-white p-7 shadow-2xl"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="eyebrow">New-session proof</p>
                <h2 id="session-title" className="mt-1 text-2xl font-semibold">
                  Start a clean UI session
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setSessionDialog(false)}
                aria-label="Close"
                className="grid size-9 place-items-center rounded-full bg-slate-100 text-slate-500"
              >
                <Icon name="close" className="size-4" />
              </button>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-500">
              This clears the current comparison from the browser, then signs
              the same clinician into a fresh UI session. Server-side review
              memory remains available.
            </p>
            <div className="mt-5 rounded-2xl bg-[#f2f8f6] p-4 text-xs text-[#315f5a]">
              <p className="font-semibold">What proves persistence?</p>
              <p className="mt-1 leading-5">
                After approving a task, start a new session and run the
                comparison again. The trace will show that the prior review was
                retrieved and reused.
              </p>
            </div>
            <button
              type="button"
              onClick={beginNewSession}
              className="mt-6 w-full rounded-xl bg-[#123d3a] px-4 py-3 text-sm font-semibold text-white"
            >
              Start new session
            </button>
            <button
              type="button"
              onClick={logout}
              className="mt-2 w-full rounded-xl px-4 py-3 text-sm font-semibold text-slate-500 hover:bg-slate-50"
            >
              Log out to landing page
            </button>
          </div>
        </div>
      )}
      {toast && (
        <div
          role="status"
          className="fixed bottom-20 left-1/2 z-[60] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 rounded-2xl bg-slate-950 px-5 py-3.5 text-center text-xs font-semibold text-white shadow-2xl lg:bottom-6"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
