import Link from "next/link";

export function MarketingBrand({ compact = false }: { compact?: boolean }) {
  const markSize = compact ? "size-8 rounded-xl" : "size-10 rounded-2xl";
  return (
    <Link href="/" className="inline-flex items-center gap-3 text-[#123d3a]">
      <span
        aria-hidden="true"
        className={`${markSize} relative grid place-items-center bg-[#123d3a] text-white shadow-[0_10px_28px_rgba(18,61,58,.18)]`}
      >
        <span className="absolute h-4 w-2 rotate-45 rounded-full border-2 border-white" />
        <span className="absolute h-2 w-4 -rotate-45 rounded-full border-2 border-white" />
      </span>
      <span>
        <span className="block text-sm font-semibold tracking-tight">
          BoneTwin
        </span>
        {!compact && (
          <span className="block text-[8px] font-extrabold uppercase tracking-[.2em] text-[#65918b]">
            trusted memory
          </span>
        )}
      </span>
    </Link>
  );
}
