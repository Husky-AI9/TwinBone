import Link from "next/link";

import { MarketingBrand } from "./marketing-brand";

export function AuthGateway({ mode }: { mode: "sign-in" | "sign-up" }) {
  const signingIn = mode === "sign-in";
  return (
    <main className="grid min-h-screen bg-[#f2f6f4] px-5 py-8 text-slate-950 lg:grid-cols-2 lg:p-4">
      <section className="mx-auto flex w-full max-w-md flex-col justify-center py-8 lg:py-0">
        <MarketingBrand />
        <div className="mt-14">
          <p className="eyebrow">
            {signingIn ? "Welcome back" : "Get started"}
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-.045em] text-[#123d3a]">
            {signingIn ? "Sign in to BoneTwin" : "Create your account"}
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-500">
            Hosted accounts will use Amazon Cognito. Local testing stays
            isolated behind a demo identity and does not create real user
            accounts.
          </p>
          <div className="mt-8 rounded-2xl border border-[#cce2dc] bg-white p-5 shadow-[0_18px_55px_rgba(30,68,62,.08)]">
            <div className="flex gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-[#e4f2ee] text-sm text-[#39786f]">
                ✓
              </span>
              <div>
                <p className="text-sm font-semibold text-[#173c39]">
                  Local demo access is ready
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Explore report upload, trusted memory retrieval, and human
                  review using records only.
                </p>
              </div>
            </div>
          </div>
          <Link
            href="/demo"
            className="mt-5 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#123d3a] px-5 text-sm font-semibold text-white shadow-[0_14px_34px_rgba(18,61,58,.2)] transition hover:-translate-y-0.5 hover:bg-[#184b47]"
          >
            Continue with demo account
          </Link>
          <p className="mt-5 text-center text-xs text-slate-500">
            {signingIn ? "Need an account?" : "Already registered?"}
            <span aria-hidden="true"> </span>
            <Link
              href={signingIn ? "/sign-up" : "/sign-in"}
              className="font-semibold text-[#2c7168] hover:underline"
            >
              {signingIn ? "Sign up" : "Sign in"}
            </Link>
          </p>
          <Link
            href="/"
            className="mt-8 block text-center text-xs font-medium text-slate-400 hover:text-[#123d3a]"
          >
            ← Back to home
          </Link>
        </div>
      </section>
      <aside className="relative hidden overflow-hidden rounded-[2rem] bg-[#123d3a] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-32 -top-32 size-96 rounded-full border border-white/10" />
        <div className="absolute -right-16 -top-16 size-64 rounded-full border border-white/10" />
        <div className="relative">
          <span className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-[9px] font-bold uppercase tracking-[.18em] text-[#b9ddd4]">
            CockroachDB × AWS
          </span>
          <blockquote className="mt-10 max-w-lg text-3xl font-medium leading-[1.25] tracking-[-.035em]">
            “BoneTwin remembers not only the measurement, but why it can be
            trusted.”
          </blockquote>
        </div>
        <div className="relative grid grid-cols-3 gap-3">
          {[
            ["Evidence", "Preserved"],
            ["Actions", "Human reviewed"],
            ["Demo data", ""],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl bg-white/8 p-4">
              <p className="text-[9px] font-bold uppercase tracking-wider text-[#8ebdb2]">
                {label}
              </p>
              <p className="mt-2 text-xs font-semibold">{value}</p>
            </div>
          ))}
        </div>
      </aside>
    </main>
  );
}
