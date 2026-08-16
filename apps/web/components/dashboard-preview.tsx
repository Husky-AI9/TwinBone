"use client";

import { useMemo, useState } from "react";

import {
  boneSites,
  memoryTrace,
  statusTone,
  timelinePoints,
  type BoneSiteId,
} from "../lib/preview-data";

function BrandMark() {
  return (
    <span className="relative grid size-10 place-items-center rounded-2xl bg-[#123d3a] text-white shadow-[0_8px_24px_rgba(18,61,58,0.22)]">
      <svg aria-hidden="true" viewBox="0 0 28 28" className="size-6">
        <path
          d="M8.2 5.7c1.5-1.5 3.8-1.5 5.3 0l8.8 8.8c1.5 1.5 1.5 3.8 0 5.3s-3.8 1.5-5.3 0l-8.8-8.8c-1.5-1.5-1.5-3.8 0-5.3Z"
          fill="currentColor"
          opacity=".45"
        />
        <circle cx="7.2" cy="6.2" r="3.2" fill="currentColor" />
        <circle cx="21.1" cy="20.1" r="3.2" fill="currentColor" />
      </svg>
    </span>
  );
}

function NavIcon({
  children,
  active = false,
  label,
}: {
  children: React.ReactNode;
  active?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-current={active ? "page" : undefined}
      className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${
        active
          ? "bg-[#e5f2ee] text-[#123d3a]"
          : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
      }`}
    >
      <span
        className={`grid size-8 place-items-center rounded-lg ${
          active ? "bg-white shadow-sm" : "group-hover:bg-white"
        }`}
      >
        {children}
      </span>
      <span className="hidden lg:inline">{label}</span>
    </button>
  );
}

function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[76px] flex-col border-r border-slate-200/80 bg-white px-3 py-5 md:flex lg:w-60">
      <div className="flex items-center gap-3 px-1 lg:px-2">
        <BrandMark />
        <div className="hidden lg:block">
          <p className="text-lg font-semibold tracking-tight text-slate-950">
            BoneTwin
          </p>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#56857f]">
            trusted memory
          </p>
        </div>
      </div>
      <nav aria-label="Primary" className="mt-10 space-y-1">
        <NavIcon active label="Overview">
          <svg
            aria-hidden="true"
            className="size-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M4 13h6V4H4v9Zm10 7h6v-9h-6v9ZM4 20h6v-3H4v3Zm10-13h6V4h-6v3Z" />
          </svg>
        </NavIcon>
        <NavIcon label="Timeline">
          <svg
            aria-hidden="true"
            className="size-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M4 19V8m6 11V4m6 15v-7m4 7H2" />
          </svg>
        </NavIcon>
        <NavIcon label="Reports">
          <svg
            aria-hidden="true"
            className="size-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M6 3h9l4 4v14H6V3Zm9 0v5h4M9 12h7M9 16h5" />
          </svg>
        </NavIcon>
        <NavIcon label="Memory trace">
          <svg
            aria-hidden="true"
            className="size-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M12 3a4 4 0 0 0-4 4v1a4 4 0 0 0-2 7.46A4.5 4.5 0 0 0 10.5 21H12V3Zm0 0a4 4 0 0 1 4 4v1a4 4 0 0 1 2 7.46A4.5 4.5 0 0 1 13.5 21H12" />
          </svg>
        </NavIcon>
      </nav>
      <div className="mt-auto rounded-2xl bg-[#f4f8f7] p-3 text-center lg:p-4 lg:text-left">
        <div className="mx-auto mb-2 grid size-8 place-items-center rounded-full bg-white text-[#2f6f68] lg:mx-0">
          <svg
            aria-hidden="true"
            className="size-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M12 3 5 6v5c0 4.6 2.7 8.2 7 10 4.3-1.8 7-5.4 7-10V6l-7-3Z" />
            <path d="m9.5 12 1.7 1.7 3.6-4" />
          </svg>
        </div>
        <p className="hidden text-xs font-semibold text-slate-700 lg:block">
          Data only
        </p>
        <p className="mt-1 hidden text-[11px] leading-4 text-slate-500 lg:block">
          No real health records in this preview.
        </p>
      </div>
    </aside>
  );
}

function SkeletonGraphic({ selectedSite }: { selectedSite: BoneSiteId }) {
  const selectedColor = "#2f766e";
  const boneColor = "#d7e6e1";
  const mutedColor = "#e9f0ed";
  const siteColor = (site: BoneSiteId) =>
    selectedSite === site ? selectedColor : boneColor;

  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 280 490"
      className="h-[360px] w-full drop-shadow-[0_18px_24px_rgba(26,72,67,0.08)] sm:h-[420px]"
    >
      <defs>
        <linearGradient id="bone-fill" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#f3f7f5" />
          <stop offset="1" stopColor="#d8e7e2" />
        </linearGradient>
      </defs>
      <circle cx="140" cy="40" r="25" fill="url(#bone-fill)" />
      <path
        d="M120 62c-10 8-17 20-18 38l-4 73c-1 17-8 34-19 47l-15 17 24 17 26-20 26 13 26-13 26 20 24-17-15-17c-11-13-18-30-19-47l-4-73c-1-18-8-30-18-38l-20 12-20-12Z"
        fill="url(#bone-fill)"
      />
      <path
        d="M104 92 73 121 50 210"
        fill="none"
        stroke={mutedColor}
        strokeLinecap="round"
        strokeWidth="16"
      />
      <path
        d="m176 92 31 29 23 89"
        fill="none"
        stroke={siteColor("forearm")}
        strokeLinecap="round"
        strokeWidth="16"
      />
      <path
        d="M51 211 43 306m188-95 8 95"
        fill="none"
        stroke={mutedColor}
        strokeLinecap="round"
        strokeWidth="11"
      />
      <path
        d="M112 241 93 271l-9 115m84-145 19 30 9 115"
        fill="none"
        stroke={boneColor}
        strokeLinecap="round"
        strokeWidth="24"
      />
      <path
        d="M83 386 76 461m121-75 7 75"
        fill="none"
        stroke={mutedColor}
        strokeLinecap="round"
        strokeWidth="16"
      />
      <path
        d="M98 218c13-18 27-26 42-26s29 8 42 26l-16 31-26-13-26 13-16-31Z"
        fill={siteColor("left-total-hip")}
        opacity=".96"
      />
      <circle cx="109" cy="246" r="13" fill={siteColor("femoral-neck")} />
      <circle cx="171" cy="246" r="13" fill={boneColor} />
      {Array.from({ length: 7 }, (_, index) => (
        <rect
          key={index}
          x="130"
          y={83 + index * 17}
          width="20"
          height="11"
          rx="5"
          fill={siteColor("lumbar-spine")}
          opacity={0.72 + index * 0.035}
        />
      ))}
      <path
        d="M76 461h-26m154 0h26"
        fill="none"
        stroke={mutedColor}
        strokeLinecap="round"
        strokeWidth="13"
      />
    </svg>
  );
}

function BonePreview({
  selectedSite,
  onSelect,
}: {
  selectedSite: BoneSiteId;
  onSelect: (site: BoneSiteId) => void;
}) {
  const site = boneSites.find((item) => item.id === selectedSite)!;

  return (
    <section className="overflow-hidden rounded-[28px] border border-white/80 bg-white shadow-[0_20px_60px_rgba(27,58,55,0.08)]">
      <div className="flex items-start justify-between px-5 pt-5 sm:px-7 sm:pt-7">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#56857f]">
            Anatomical overview
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">
            Bone site preview
          </h2>
        </div>
        <span className="rounded-full border border-[#d8e9e4] bg-[#f2f8f6] px-3 py-1 text-[11px] font-semibold text-[#2f6f68]">
          4 sites
        </span>
      </div>

      <div className="grid items-center gap-2 px-3 pb-4 sm:grid-cols-[1fr_170px] sm:px-5">
        <div className="relative mx-auto w-full max-w-[310px]">
          <SkeletonGraphic selectedSite={selectedSite} />
          {boneSites.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-label={`Select ${item.label}`}
              aria-pressed={selectedSite === item.id}
              onClick={() => onSelect(item.id)}
              style={{ left: item.position.left, top: item.position.top }}
              className={`absolute grid size-7 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-4 border-white shadow-lg transition hover:scale-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f766e] ${
                selectedSite === item.id ? "bg-[#2f766e]" : "bg-[#9bbdb5]"
              }`}
            >
              <span className="size-1.5 rounded-full bg-white" />
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-1">
          {boneSites.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              aria-pressed={selectedSite === item.id}
              className={`rounded-2xl border px-3 py-3 text-left transition ${
                selectedSite === item.id
                  ? "border-[#83aaa2] bg-[#eef7f4] shadow-sm"
                  : "border-slate-100 bg-slate-50/70 hover:border-slate-200 hover:bg-white"
              }`}
            >
              <span className="block text-xs font-semibold text-slate-800">
                {item.shortLabel}
              </span>
              <span className="mt-1 block text-[11px] text-slate-500">
                {item.status}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-slate-100 bg-[#fbfcfc] px-5 py-4 sm:px-7">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold text-slate-900">{site.label}</h3>
          <span
            className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${statusTone(
              site.status,
            )}`}
          >
            {site.status}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              BMD
            </p>
            <p className="mt-1 text-lg font-semibold text-slate-900">
              {site.bmd}
              {site.bmd !== "—" && (
                <span className="ml-1 text-[10px] font-medium text-slate-400">
                  g/cm²
                </span>
              )}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              T-score
            </p>
            <p className="mt-1 text-lg font-semibold text-slate-900">
              {site.tScore}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Since prior
            </p>
            <p className="mt-1 text-lg font-semibold text-slate-900">
              {site.change}
            </p>
          </div>
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          {site.statusDetail}
        </p>
      </div>
    </section>
  );
}

function TimelineChart() {
  const chartPoints = useMemo(
    () =>
      timelinePoints.map((point, index) => ({
        ...point,
        x: 32 + index * 124,
        y: 44 + (0.79 - point.bmd) * 680,
      })),
    [],
  );
  const path = chartPoints
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x} ${point.y}`)
    .join(" ");

  return (
    <section className="rounded-[28px] border border-white/80 bg-white p-5 shadow-[0_20px_60px_rgba(27,58,55,0.08)] sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#56857f]">
            Longitudinal view
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">
            Left total hip
          </h2>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-400">Latest BMD</p>
          <p className="text-lg font-semibold text-slate-900">
            0.742{" "}
            <span className="text-[10px] font-medium text-slate-400">
              g/cm²
            </span>
          </p>
        </div>
      </div>

      <div className="mt-6 rounded-2xl bg-[#f7faf9] px-3 py-4">
        <svg
          role="img"
          aria-label="Left total hip BMD declined from 0.781 in 2019 to 0.742 in 2026"
          viewBox="0 0 312 150"
          className="h-40 w-full"
        >
          {[36, 76, 116].map((y) => (
            <line
              key={y}
              x1="18"
              y1={y}
              x2="294"
              y2={y}
              stroke="#dfe8e5"
              strokeDasharray="3 5"
            />
          ))}
          <path
            d={path}
            fill="none"
            stroke="#2f766e"
            strokeLinecap="round"
            strokeWidth="3"
          />
          <path
            d={`${path} L280 130 L32 130 Z`}
            fill="url(#timeline-gradient)"
            opacity=".48"
          />
          <defs>
            <linearGradient id="timeline-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop stopColor="#82b7ae" />
              <stop offset="1" stopColor="#eef6f3" />
            </linearGradient>
          </defs>
          {chartPoints.map((point, index) => (
            <g key={point.year}>
              <circle
                cx={point.x}
                cy={point.y}
                r={index === chartPoints.length - 1 ? 7 : 5}
                fill={index === chartPoints.length - 1 ? "#2f766e" : "white"}
                stroke="#2f766e"
                strokeWidth="3"
              />
              <text
                x={point.x}
                y="147"
                textAnchor="middle"
                className="fill-slate-400 text-[10px] font-semibold"
              >
                {point.year}
              </text>
            </g>
          ))}
        </svg>
      </div>

      <div className="mt-4 grid grid-cols-3 divide-x divide-slate-100">
        {timelinePoints.map((point) => (
          <div key={point.year} className="px-3 first:pl-0 last:pr-0">
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
              {point.label}
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-800">
              {point.bmd.toFixed(3)}
            </p>
            <p className="text-[11px] text-slate-400">T {point.tScore}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function MemoryImpactCard() {
  return (
    <section className="rounded-[28px] bg-[#143f3b] p-5 text-white shadow-[0_24px_60px_rgba(18,61,58,0.2)] sm:p-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#a9ccc5]">
            Memory impact trace
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">
            Why the comparison changed
          </h2>
        </div>
        <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-white/10">
          <svg
            aria-hidden="true"
            className="size-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M12 3a4 4 0 0 0-4 4v1a4 4 0 0 0-2 7.46A4.5 4.5 0 0 0 10.5 21H12V3Zm0 0a4 4 0 0 1 4 4v1a4 4 0 0 1 2 7.46A4.5 4.5 0 0 1 13.5 21H12" />
          </svg>
        </span>
      </div>

      <div className="mt-6 space-y-3">
        {memoryTrace.map((memory) => (
          <article
            key={memory.title}
            className="rounded-2xl border border-white/10 bg-white/[0.07] p-4"
          >
            <div className="flex items-center gap-2">
              <span
                className={`size-2 rounded-full ${
                  memory.tone === "teal"
                    ? "bg-[#79c5b8]"
                    : memory.tone === "amber"
                      ? "bg-amber-300"
                      : "bg-slate-300"
                }`}
              />
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#a9ccc5]">
                {memory.label}
              </p>
            </div>
            <p className="mt-2 text-sm font-medium leading-5">{memory.title}</p>
            <p className="mt-1 text-[11px] leading-4 text-white/50">
              {memory.source}
            </p>
          </article>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-[#7bc3b7]/25 bg-[#7bc3b7]/10 p-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9fd2c9]">
          Counterfactual
        </p>
        <p className="mt-2 text-xs leading-5 text-white/75">
          Without the verified correction, the preview would have included the
          lumbar value in the longitudinal comparison.
        </p>
      </div>
    </section>
  );
}

function MetricCard({
  label,
  value,
  detail,
  accent,
}: {
  label: string;
  value: string;
  detail: string;
  accent: "teal" | "amber" | "blue";
}) {
  const accentClass = {
    teal: "bg-[#dff1ec] text-[#2f766e]",
    amber: "bg-amber-100 text-amber-700",
    blue: "bg-sky-100 text-sky-700",
  }[accent];

  return (
    <article className="rounded-2xl border border-white bg-white p-4 shadow-[0_12px_36px_rgba(27,58,55,0.06)]">
      <div className={`mb-3 h-1.5 w-10 rounded-full ${accentClass}`} />
      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </article>
  );
}

function UploadDialog({
  onClose,
  onLoadSynthetic,
}: {
  onClose: () => void;
  onLoadSynthetic: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-[#0d2a28]/45 p-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
        className="w-full max-w-lg rounded-[28px] bg-white p-6 shadow-2xl sm:p-8"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#56857f]">
              Preview workflow
            </p>
            <h2
              id="upload-title"
              className="mt-1 text-2xl font-semibold tracking-tight text-slate-950"
            >
              Load a DXA report
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="grid size-9 place-items-center rounded-full bg-slate-100 text-slate-500 hover:bg-slate-200"
          >
            ×
          </button>
        </div>
        <div className="mt-6 rounded-2xl border border-dashed border-[#a9c9c2] bg-[#f3f9f7] p-7 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-white text-[#2f766e] shadow-sm">
            <svg
              aria-hidden="true"
              className="size-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path d="M12 16V4m0 0L7 9m5-5 5 5M5 14v5h14v-5" />
            </svg>
          </span>
          <p className="mt-4 text-sm font-semibold text-slate-800">
            Fixture only
          </p>
          <p className="mx-auto mt-2 max-w-xs text-xs leading-5 text-slate-500">
            Real file upload arrives with the ingestion phase. This preview
            loads a fabricated report without reading anything from your device.
          </p>
          <button
            type="button"
            onClick={onLoadSynthetic}
            className="mt-5 rounded-xl bg-[#123d3a] px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-[#123d3a]/15 hover:bg-[#1b524d]"
          >
            Load report
          </button>
        </div>
        <p className="mt-4 text-center text-[11px] leading-4 text-slate-400">
          BoneTwin organizes reports for human review. It does not diagnose or
          recommend treatment.
        </p>
      </div>
    </div>
  );
}

export function DashboardPreview() {
  const [selectedSite, setSelectedSite] =
    useState<BoneSiteId>("left-total-hip");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  function loadSyntheticReport() {
    setUploadOpen(false);
    setToast("Report loaded into preview mode.");
    window.setTimeout(() => setToast(null), 4200);
  }

  return (
    <div className="min-h-screen bg-[#f2f6f4] text-slate-900">
      <Sidebar />
      <main className="min-h-screen md:pl-[76px] lg:pl-60">
        <header className="sticky top-0 z-20 border-b border-white/70 bg-[#f2f6f4]/90 px-4 py-4 backdrop-blur-xl sm:px-7 lg:px-10">
          <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4">
            <div className="flex items-center gap-3 md:hidden">
              <BrandMark />
              <p className="font-semibold text-slate-950">BoneTwin</p>
            </div>
            <div className="hidden md:block">
              <p className="text-sm font-semibold text-slate-900">Subject</p>
              <p className="text-xs text-slate-500">SYNTH-BONE-001</p>
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <span className="hidden rounded-full border border-[#d6e8e3] bg-white px-3 py-2 text-xs font-semibold text-[#41756f] sm:inline">
                Preview mode
              </span>
              <button
                type="button"
                onClick={() => setUploadOpen(true)}
                className="rounded-xl bg-[#123d3a] px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-[#123d3a]/15 transition hover:-translate-y-0.5 hover:bg-[#1b524d] sm:text-sm"
              >
                <span className="mr-2 text-base leading-none">+</span>
                Add report
              </button>
              <span className="grid size-10 place-items-center rounded-full bg-[#d9ece7] text-xs font-bold text-[#2f6f68]">
                SJ
              </span>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-[1440px] px-4 pb-14 pt-6 sm:px-7 lg:px-10 lg:pt-9">
          <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-[#56857f]">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                Longitudinal record ready
              </div>
              <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-4xl">
                Bone health overview
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                Review scan history, evidence quality, and the durable memories
                that changed this comparison.
              </p>
            </div>
            <p className="text-xs text-slate-400">
              Last refreshed · Today, 10:31 PM
            </p>
          </section>

          <aside className="mt-6 flex items-start gap-3 rounded-2xl border border-[#cfe2dd] bg-[#eaf5f2] px-4 py-3 text-xs leading-5 text-[#315f5a]">
            <svg
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M12 10v6m0-9h.01" />
            </svg>
            <p>
              <strong className="font-semibold">UI preview.</strong> Values are
              fabricated for product design and are not medical interpretation.
            </p>
          </aside>

          <section
            aria-label="Subject summary"
            className="mt-5 grid gap-3 sm:grid-cols-3"
          >
            <MetricCard
              label="Latest scan"
              value="Apr 12"
              detail="2026 · DXA BMD"
              accent="teal"
            />
            <MetricCard
              label="Verified memories"
              value="8"
              detail="2 influenced this view"
              accent="blue"
            />
            <MetricCard
              label="Open reviews"
              value="2"
              detail="1 requires clinician"
              accent="amber"
            />
          </section>

          <div className="mt-5 grid items-start gap-5 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,.98fr)]">
            <BonePreview
              selectedSite={selectedSite}
              onSelect={setSelectedSite}
            />
            <div className="grid gap-5">
              <TimelineChart />
              <MemoryImpactCard />
            </div>
          </div>

          <footer className="mt-8 flex flex-col justify-between gap-3 border-t border-slate-200/80 pt-5 text-[11px] leading-5 text-slate-400 sm:flex-row">
            <p>
              BoneTwin supports document organization and clinical-review
              preparation only.
            </p>
            <p>Phase 1 database foundation · UI concept preview</p>
          </footer>
        </div>
      </main>

      {uploadOpen && (
        <UploadDialog
          onClose={() => setUploadOpen(false)}
          onLoadSynthetic={loadSyntheticReport}
        />
      )}
      {toast && (
        <div
          role="status"
          className="fixed bottom-5 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-slate-950 px-5 py-3 text-xs font-semibold text-white shadow-2xl"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
