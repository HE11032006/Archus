"use client";

import { Check, Loader2 } from "lucide-react";

const STEPS = [
  {
    step: 0,
    label: "Repo Ingestion & AST Inspection",
    detail: "Cloning repository, analyzing files, and detecting architecture pattern",
  },
  {
    step: 1,
    label: "SQL Metric Retrieval",
    detail: "Querying complexity, coupling, tests, and churn through SQLGuard",
  },
  {
    step: 2,
    label: "Analyst Agent",
    detail: "Scoring options: Maintain, Refactor, or Migrate",
  },
  {
    step: 3,
    label: "Evidence Evaluator",
    detail: "Independently re-querying every claim with veto authority",
  },
  {
    step: 4,
    label: "Reporter & Meterless AI",
    detail: "Synthesizing formal decision record and transformation roadmap",
  },
] as const;

export function PipelineProgress({
  currentStep,
  failed,
  repo,
}: {
  currentStep: number;
  failed?: boolean;
  repo?: string;
}) {
  return (
    <section className="mx-auto flex w-full max-w-xl flex-col items-center justify-center px-4 pt-4 pb-8">
      {failed && (
        <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-rose-500">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
          Analysis failed
        </div>
      )}

      <h1
        className="mb-1 text-center font-display text-2xl font-semibold tracking-tight md:text-3xl"
        style={{ fontFamily: "var(--font-family-display), sans-serif" }}
      >
        {failed ? "Something went wrong" : "Reading the Architecture"}
      </h1>

      {repo ? (
        <p className="mb-5 max-w-md text-center font-mono text-xs text-[var(--landing-muted)] truncate">
          {repo}
        </p>
      ) : (
        <div className="mb-4" />
      )}

      <div className="w-full rounded-2xl border border-[var(--landing-border)] bg-[var(--landing-card)] p-5 md:p-6 shadow-sm">
        <div className="flex flex-col gap-4">
          {STEPS.map((step) => {
            const done = !failed && currentStep > step.step;
            const active = !failed && currentStep === step.step;

            return (
              <div key={step.step} className="flex items-center gap-3.5">
                {/* Circular indicator: Done = Check circle, Active = Spinner circle, Pending = Number circle */}
                <div className="shrink-0">
                  {done ? (
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500 text-white shadow-xs">
                      <Check size={14} strokeWidth={2.8} />
                    </div>
                  ) : active ? (
                    <div className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-[var(--brand-primary)] bg-[var(--brand-primary)]/10 text-[var(--brand-primary)]">
                      <Loader2 size={13} className="animate-spin text-[var(--brand-primary)]" />
                    </div>
                  ) : (
                    <div className="flex h-7 w-7 items-center justify-center rounded-full border border-[var(--landing-border)] bg-[var(--landing-bg)] font-mono text-[11px] font-semibold text-[var(--landing-muted)]">
                      {step.step + 1}
                    </div>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className={`text-xs font-semibold ${
                        active
                          ? "text-[var(--brand-primary)]"
                          : done
                          ? "text-[var(--landing-fg)]"
                          : "text-[var(--landing-muted)]"
                      }`}
                    >
                      {step.label}
                    </p>
                    {active && (
                      <span className="shrink-0 font-mono text-[10px] uppercase font-bold text-[var(--brand-primary)]">
                        Running
                      </span>
                    )}
                    {done && (
                      <span className="shrink-0 font-mono text-[10px] uppercase font-bold text-emerald-500">
                        Done
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-[11px] leading-tight text-[var(--landing-muted)] line-clamp-1">
                    {step.detail}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
