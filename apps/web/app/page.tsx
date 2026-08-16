import Link from "next/link";

import { AnatomicalSkeleton } from "../components/anatomical-skeleton";
import { MarketingBrand } from "../components/marketing-brand";

const technologies = [
  "CockroachDB Cloud",
  "Amazon Bedrock",
  "LangChain MCP",
  "Human Review",
];

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4" fill="none">
      <path
        d="M5 12h14m-6-6 6 6-6 6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      className="size-3.5"
      fill="none"
    >
      <path
        d="m5 10.2 3.1 3.1L15.2 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function BoneLink() {
  return (
    <svg
      aria-label="Linked evidence over time"
      role="img"
      viewBox="0 0 184 72"
      className="h-[.78em] w-[1.65em] shrink-0"
    >
      <defs>
        <linearGradient id="bone-link-stroke" x1="0" x2="1">
          <stop stopColor="#123d3a" />
          <stop offset="1" stopColor="#56a194" />
        </linearGradient>
      </defs>
      <path
        d="M7 14c12 0 17 11 26 20 11 11 20 22 36 22 17 0 26-14 38-28 10-11 18-20 32-20 15 0 24 13 38 30"
        fill="none"
        stroke="url(#bone-link-stroke)"
        strokeWidth="6"
        strokeLinecap="round"
      />
      <path
        d="M7 58c12 0 17-11 26-20 11-11 20-22 36-22 17 0 26 14 38 28 10 11 18 20 32 20 15 0 24-13 38-30"
        fill="none"
        stroke="#83b7ae"
        strokeWidth="6"
        strokeLinecap="round"
      />
      {[31, 55, 81, 108, 134, 157].map((x, index) => (
        <path
          key={x}
          d={`M${x} ${index % 2 ? 24 : 20}v${index % 2 ? 25 : 32}`}
          stroke="#b7d5ce"
          strokeWidth="3"
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}

function SourceToken({ label }: { label: string }) {
  return (
    <span
      aria-label={label}
      className="grid size-9 place-items-center rounded-full border-2 border-[#d7ebe6] bg-white text-[#2f766e] shadow-sm"
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 20 20"
        className="size-4"
        fill="none"
      >
        <path
          d="M5 2.8h6l4 4V17H5V2.8Zm6 0v4h4M7.5 10h5M7.5 13h4"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_80%_15%,#5c9e92_0,#39786f_36%,#173f3c_100%)] p-3 text-slate-950 sm:p-7 lg:p-10">
      <div className="relative mx-auto min-h-[calc(100vh-1.5rem)] max-w-[1500px] overflow-hidden rounded-[28px] border border-white/30 bg-[#edf6f4] shadow-[0_36px_100px_rgba(9,39,36,.28)] sm:min-h-[calc(100vh-3.5rem)] sm:rounded-[36px]">
        <div className="pointer-events-none absolute -left-40 top-32 size-[34rem] rounded-full bg-white/45 blur-[90px]" />
        <div className="pointer-events-none absolute -right-32 top-0 size-[30rem] rounded-full bg-[#c5e4dc]/45 blur-[100px]" />

        <header className="relative z-10 flex items-center justify-between px-5 py-6 sm:px-9 lg:px-14 lg:py-9">
          <MarketingBrand />
          <nav
            aria-label="Primary navigation"
            className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-9 text-xs font-semibold text-slate-500 lg:flex"
          >
            <Link href="/" className="text-[#1f685f]">
              Home
            </Link>
            <Link
              href="#how-it-works"
              className="transition hover:text-[#1f685f]"
            >
              How it works
            </Link>
            <Link href="#safety" className="transition hover:text-[#1f685f]">
              Safety
            </Link>
            <Link href="/sign-in" className="transition hover:text-[#1f685f]">
              Sign in
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link
              href="/sign-up"
              className="hidden min-h-11 items-center justify-center rounded-xl border border-[#9dc5bc] bg-white/45 px-4 text-xs font-semibold text-[#205e57] transition hover:bg-white sm:inline-flex"
            >
              Sign up
            </Link>
            <Link
              href="/demo"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#123d3a] px-4 text-xs font-semibold text-white shadow-[0_12px_28px_rgba(18,61,58,.2)] transition hover:-translate-y-0.5 hover:bg-[#194d48] sm:px-5"
            >
              Try demo
              <ArrowIcon />
            </Link>
          </div>
        </header>

        <section className="relative z-[1] grid items-center gap-10 px-5 pb-14 pt-8 sm:px-9 lg:grid-cols-[1.03fr_.97fr] lg:gap-12 lg:px-14 lg:pb-12 lg:pt-14 xl:gap-16">
          <div className="max-w-[720px]">
            <p className="mb-6 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#4e8b82]">
              One evidence-backed timeline
            </p>
            <h1 className="text-[clamp(3.5rem,7vw,7.5rem)] font-medium leading-[.84] tracking-[-.065em] text-[#172d2c]">
              <span className="block">Connected</span>
              <span className="mt-3 flex items-center gap-[.09em] text-[#2f766e]">
                <BoneLink />
                Bone
              </span>
              <span className="mt-3 block">Memory</span>
            </h1>
            <p className="mt-9 max-w-lg text-sm leading-6 text-slate-600 sm:text-base sm:leading-7">
              BoneTwin turns years of scattered bone-density reports into one
              trusted history, preserving what was measured, corrected, and
              approved for human review.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/demo"
                className="inline-flex min-h-12 items-center justify-center gap-3 rounded-xl bg-[#123d3a] px-6 text-sm font-semibold text-white shadow-[0_14px_34px_rgba(18,61,58,.22)] transition hover:-translate-y-0.5 hover:bg-[#194d48]"
              >
                Try demo account
                <ArrowIcon />
              </Link>
              <div className="flex items-center gap-2 px-2 text-xs font-medium text-slate-500">
                <span className="grid size-6 place-items-center rounded-full bg-[#d5ebe5] text-[#2f766e]">
                  <CheckIcon />
                </span>
                Data only
              </div>
            </div>
            <div
              id="safety"
              className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-[11px] text-slate-500"
            >
              <span>Source evidence preserved</span>
              <span className="hidden text-[#9ebbb5] sm:inline">/</span>
              <span>Human approval required</span>
              <span className="hidden text-[#9ebbb5] sm:inline">/</span>
              <span>No diagnosis or treatment advice</span>
            </div>
          </div>

          <div
            id="how-it-works"
            className="mx-auto grid w-full max-w-[620px] gap-3 sm:grid-cols-[1.16fr_.84fr] sm:grid-rows-[1fr_auto] lg:max-w-none"
          >
            <article className="relative min-h-[480px] overflow-hidden rounded-[28px] bg-[linear-gradient(165deg,#d8eee8_0%,#8bc4b8_52%,#397b72_100%)] p-5 shadow-[0_24px_65px_rgba(39,100,91,.22)] sm:row-span-2 lg:min-h-[540px]">
              <div className="relative z-10 flex items-start justify-between border-b border-white/35 pb-4 text-[#123d3a]">
                <div>
                  <p className="text-[9px] font-extrabold uppercase tracking-[.17em] text-[#2d6f66]">
                    Anatomical overview
                  </p>
                  <h2 className="mt-1 text-lg font-semibold">
                    See every site in context
                  </h2>
                </div>
                <span className="grid size-10 place-items-center rounded-full bg-white/35 backdrop-blur">
                  <ArrowIcon />
                </span>
              </div>
              <div className="absolute inset-x-0 bottom-[-112px] top-[82px] opacity-95">
                <AnatomicalSkeleton selected="left-total-hip" />
              </div>
              <div className="absolute inset-x-5 bottom-5 z-10 rounded-2xl border border-white/25 bg-[#123d3a]/82 p-4 text-white shadow-xl backdrop-blur-md">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-[9px] font-bold uppercase tracking-[.15em] text-[#9cd2c7]">
                      Selected evidence
                    </p>
                    <p className="mt-1 text-sm font-semibold">
                      Left total hip timeline
                    </p>
                  </div>
                  <span className="rounded-full bg-white/12 px-3 py-1.5 text-[9px] font-bold uppercase tracking-wider">
                    Verified
                  </span>
                </div>
              </div>
            </article>

            <article className="relative min-h-[330px] overflow-hidden rounded-[28px] bg-[#2f766e] p-5 text-white shadow-[0_24px_65px_rgba(39,100,91,.2)] sm:min-h-0">
              <div className="flex justify-end">
                <span className="grid size-10 place-items-center rounded-full bg-white/12">
                  <ArrowIcon />
                </span>
              </div>
              <p className="mt-2 text-4xl font-semibold tracking-[-.045em]">
                3 steps
              </p>
              <p className="mt-1 text-sm text-white/70">
                to trusted longitudinal memory
              </p>
              <div className="relative mx-auto mt-7 grid size-36 place-items-center rounded-full border border-white/15">
                <div className="absolute inset-4 rounded-full border border-dashed border-white/25" />
                <div className="grid size-20 place-items-center rounded-[30%] bg-[radial-gradient(circle_at_35%_30%,#d9f3ed,#70b6aa_55%,#194f4a)] shadow-[inset_-10px_-14px_24px_rgba(13,55,51,.35),0_18px_35px_rgba(7,41,38,.2)]">
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 38 38"
                    className="size-10"
                    fill="none"
                  >
                    <path
                      d="M19 6v26M9 12h20M7 19h24M10 26h18"
                      stroke="white"
                      strokeWidth="2"
                      strokeLinecap="round"
                      opacity=".88"
                    />
                    <circle cx="19" cy="19" r="4" fill="white" />
                  </svg>
                </div>
              </div>
            </article>

            <article className="rounded-[22px] bg-[#174d48] p-4 text-white shadow-[0_18px_45px_rgba(18,61,58,.18)]">
              <div className="flex items-center justify-between gap-3">
                <div className="flex -space-x-2">
                  <SourceToken label="Original report evidence" />
                  <SourceToken label="Verified correction evidence" />
                  <SourceToken label="Human review evidence" />
                </div>
                <div className="text-right">
                  <p className="text-xs font-semibold">
                    Evidence stays visible
                  </p>
                  <p className="mt-0.5 text-[9px] text-[#9ac8be]">
                    Originals are never overwritten
                  </p>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section className="relative z-10 mx-5 border-t border-[#bcd5cf]/70 py-7 sm:mx-9 lg:mx-14">
          <p className="text-center text-[9px] font-extrabold uppercase tracking-[.2em] text-[#769a94]">
            Built for explainable, durable review memory
          </p>
          <div className="mt-5 grid grid-cols-2 gap-x-5 gap-y-4 text-center text-xs font-semibold text-[#486966] sm:grid-cols-4">
            {technologies.map((technology) => (
              <div
                key={technology}
                className="flex items-center justify-center gap-2"
              >
                <span className="size-2 rounded-full border-2 border-[#65a297]" />
                {technology}
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
