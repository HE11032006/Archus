"use client";

const STEPS = [
  { step: 0, label: "Planner", detail: "Turning your question into measurable criteria" },
  { step: 1, label: "Retriever", detail: "Running SQL through SQLGuard" },
  { step: 2, label: "Analyst", detail: "Scoring Maintain, Refactor, Migrate" },
  { step: 3, label: "EvidenceEvaluator", detail: "Re-querying every claim   veto if needed" },
  { step: 4, label: "Reporter", detail: "Writing the sourced decision" },
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
    <section className="mx-auto flex min-h-[calc(100svh-64px)] w-full max-w-2xl flex-col items-center justify-center px-8 py-20">
      <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.16em] text-[var(--landing-muted)]">
        {failed ? "Analysis failed" : "Analysis in progress"}
      </p>
      <h1
        className="mb-2 text-center font-display text-3xl font-semibold tracking-tight md:text-4xl"
        style={{ fontFamily: "var(--font-family-display), sans-serif" }}
      >
        {failed ? "Something went wrong" : "Reading the architecture"}
      </h1>
      {repo ? (
        <p className="mb-10 max-w-md text-center font-mono text-sm text-[var(--landing-muted)]">
          {repo}
        </p>
      ) : (
        <div className="mb-10" />
      )}

      <div className="w-full rounded-2xl border border-[var(--landing-border)] bg-[var(--landing-card)] p-6 md:p-8">
        <div className="flex flex-col gap-5">
          {STEPS.map((step) => {
            const done = !failed && currentStep > step.step;
            const active = !failed && currentStep === step.step;
            const pending = !done && !active;

            return (
              <div key={step.step} className="flex items-start gap-4">
                <div
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md font-mono text-xs"
                  style={{
                    background: done
                      ? "var(--landing-fg)"
                      : active
                        ? "color-mix(in srgb, var(--landing-fg) 12%, transparent)"
                        : "transparent",
                    color: done
                      ? "var(--landing-bg)"
                      : pending
                        ? "var(--landing-muted)"
                        : "var(--landing-fg)",
                    border: "1px solid var(--landing-border)",
                  }}
                >
                  {done ? "✓" : step.step + 1}
                </div>
                <div className="min-w-0 flex-1 pt-0.5">
                  <p
                    className="text-sm font-medium"
                    style={{ color: pending ? "var(--landing-muted)" : "var(--landing-fg)" }}
                  >
                    {step.label}
                  </p>
                  <p className="text-xs text-[var(--landing-muted)]">{step.detail}</p>
                  {active && (
                    <div className="mt-2 h-0.5 overflow-hidden rounded-full bg-[var(--landing-border)]">
                      <div className="h-full w-2/3 animate-pulse bg-[var(--landing-fg)]" />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
