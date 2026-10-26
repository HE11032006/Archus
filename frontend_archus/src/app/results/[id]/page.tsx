"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
} from "lucide-react";

import { BackButton } from "@/components/back-button";
import { SiteHeader } from "@/components/site-header";
import type { RunResponse, EvidenceItem } from "@/lib/types";
import demoResult from "@/lib/demo-result.json";
import { getDecisionStyle, formatDuration } from "@/lib/utils";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="landing-icon-btn h-8 w-8"
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        });
      }}
      aria-label="Copy SQL"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

function EvidenceRow({ item }: { item: EvidenceItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-[var(--landing-border)] bg-[var(--landing-card)]">
      <button
        type="button"
        className="flex w-full items-start gap-3 p-4 text-left"
        onClick={() => setOpen(!open)}
      >
        {item.verified ? (
          <CheckCircle size={16} className="mt-0.5 shrink-0" />
        ) : (
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[var(--landing-muted)]" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{item.claim}</p>
          <p className="mt-1 font-mono text-[11px] text-[var(--landing-muted)]">
            {item.metric} · {item.source_table}
          </p>
        </div>
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--landing-muted)]">
          {item.verified ? "Verified" : "Unverified"}
        </span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && (
        <div className="space-y-3 border-t border-[var(--landing-border)] px-4 py-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="report-kicker mb-1">Value</p>
              <code className="text-xs">{String(item.value)}</code>
            </div>
            {item.threshold != null && (
              <div>
                <p className="report-kicker mb-1">Threshold</p>
                <code className="text-xs">{String(item.threshold)}</code>
              </div>
            )}
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between">
              <p className="report-kicker mb-0">SQL</p>
              <CopyButton text={item.sql_query} />
            </div>
            <pre className="overflow-x-auto rounded-lg bg-[var(--landing-bg)] p-3 font-mono text-[11px] leading-relaxed text-[var(--landing-muted)]">
              {item.sql_query}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

function formatMetricValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(1);
  }
  return String(value);
}

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<RunResponse | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (id === "demo") {
      setResult(demoResult as RunResponse);
      return;
    }
    const raw = sessionStorage.getItem(`archus_result_${id}`);
    if (!raw) {
      setResult(demoResult as RunResponse);
      return;
    }
    try {
      setResult(JSON.parse(raw) as RunResponse);
    } catch {
      setNotFound(true);
    }
  }, [id]);

  if (notFound) {
    return (
      <div className="landing flex min-h-svh flex-col">
        <SiteHeader solid />
        <div className="px-8 pt-6">
          <BackButton />
        </div>
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6">
          <XCircle size={36} />
          <h1 className="text-2xl font-semibold">Result not found</h1>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="landing flex min-h-svh items-center justify-center">
        <p className="text-[var(--landing-muted)]">Loading result…</p>
      </div>
    );
  }

  const output = result.output;
  const hasOutput = result.status !== "error" && output;
  const decisionStyle = hasOutput ? getDecisionStyle(output.decision) : null;
  const verified = hasOutput
    ? output.evidence.filter((e) => e.verified).length
    : 0;

  return (
    <div className="landing min-h-svh">
      <SiteHeader solid />
      <div className="px-8 pt-6">
        <BackButton />
      </div>

      <article className="mx-auto w-full max-w-6xl px-6 pb-20 pt-8 md:px-8">
        {result.status === "error" && (
          <div className="report-card text-center">
            <XCircle size={36} className="mx-auto mb-4" />
            <h2 className="text-xl font-semibold">Analysis failed</h2>
            <p className="mt-2 text-sm text-[var(--landing-muted)]">{result.error?.message}</p>
          </div>
        )}

        {hasOutput && decisionStyle && (
          <>
            <div className="mb-10">
              <p className="report-kicker">Analysis complete</p>
              <h1
                className="text-[clamp(2rem,4vw,3rem)] font-semibold tracking-tight"
                style={{ fontFamily: "var(--font-family-display), sans-serif" }}
              >
                Architecture Report
              </h1>
              <p className="mt-2 font-mono text-sm text-[var(--landing-muted)]">
                {formatDuration(result.execution_time_seconds)} · {result.run_id}
              </p>
            </div>

            <div className="mb-8 grid gap-6 md:grid-cols-2">
              <div className="report-card">
                <span className="report-kicker">Confidence</span>
                <div className="flex items-baseline gap-2">
                  <span
                    className="text-5xl font-semibold tracking-tight"
                    style={{ fontFamily: "var(--font-family-display), sans-serif" }}
                  >
                    {(output.confidence * 100).toFixed(0)}
                  </span>
                  <span className="text-[var(--landing-muted)]">/100</span>
                </div>
                <div className="mt-4 h-1 overflow-hidden rounded-full bg-[var(--landing-border)]">
                  <div
                    className="h-full"
                    style={{
                      width: `${output.confidence * 100}%`,
                      background: decisionStyle.color,
                    }}
                  />
                </div>
                <p className="mt-3 text-xs text-[var(--landing-muted)]">
                  {verified}/{output.evidence.length} claims independently verified
                </p>
              </div>

              <div className="report-card">
                <span className="report-kicker">Verdict</span>
                <p
                  className="mb-3 text-3xl font-semibold tracking-tight"
                  style={{
                    fontFamily: "var(--font-family-display), sans-serif",
                    color: decisionStyle.color,
                  }}
                >
                  {decisionStyle.label}
                </p>
                <p className="text-sm leading-relaxed text-[var(--landing-muted)]">
                  {output.summary}
                </p>
              </div>
            </div>

            {output.evidence.length > 0 && (
              <section className="mb-8">
                <h2 className="report-kicker">Metrics from evidence</h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {output.evidence.map((item) => (
                    <div key={item.metric} className="report-card p-5">
                      <span className="report-kicker mb-2">{item.metric.replace(/_/g, " ")}</span>
                      <p
                        className="text-3xl font-semibold tracking-tight"
                        style={{ fontFamily: "var(--font-family-display), sans-serif" }}
                      >
                        {formatMetricValue(item.value)}
                      </p>
                      <p className="mt-2 font-mono text-[11px] text-[var(--landing-muted)]">
                        {item.source_table}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {output.options_compared.length > 0 && (
              <section className="mb-8">
                <h2 className="report-kicker">Options compared</h2>
                <div className="grid gap-4 md:grid-cols-3">
                  {output.options_compared.map((opt) => {
                    const style = getDecisionStyle(opt.option);
                    const isWinner = opt.option === output.decision;
                    return (
                      <div
                        key={opt.option}
                        className="report-card"
                        style={{
                          borderColor: isWinner ? style.color : undefined,
                        }}
                      >
                        <div className="flex items-baseline justify-between">
                          <span className="font-medium" style={{ color: style.color }}>
                            {style.label}
                          </span>
                          <span
                            className="text-2xl font-semibold"
                            style={{
                              fontFamily: "var(--font-family-display), sans-serif",
                              color: style.color,
                            }}
                          >
                            {opt.score.toFixed(0)}
                          </span>
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-[var(--landing-muted)]">
                          {opt.rationale}
                        </p>
                        {opt.pros.length > 0 && (
                          <ul className="mt-4 space-y-1 text-xs text-[var(--landing-muted)]">
                            {opt.pros.map((p) => (
                              <li key={p}>+ {p}</li>
                            ))}
                          </ul>
                        )}
                        {opt.cons.length > 0 && (
                          <ul className="mt-2 space-y-1 text-xs text-[var(--landing-muted)]">
                            {opt.cons.map((c) => (
                              <li key={c}>− {c}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {output.action_plan.length > 0 && (
              <section className="mb-8">
                <h2 className="report-kicker">Action plan</h2>
                <div className="report-card">
                  <ol className="space-y-5">
                    {output.action_plan.map((step, i) => (
                      <li key={i} className="flex gap-4">
                        <span className="font-mono text-sm text-[var(--landing-muted)]">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <p className="text-sm leading-relaxed">{step}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              </section>
            )}

            {output.evidence.length > 0 && (
              <section className="mb-8">
                <h2 className="report-kicker">Evidence · {output.evidence.length}</h2>
                <div className="flex flex-col gap-2">
                  {output.evidence.map((item, i) => (
                    <EvidenceRow key={i} item={item} />
                  ))}
                </div>
              </section>
            )}

            {output.missing_data.length > 0 && (
              <section className="mb-8">
                <h2 className="report-kicker">Missing data</h2>
                <div className="report-card">
                  <ul className="space-y-2 text-sm text-[var(--landing-muted)]">
                    {output.missing_data.map((item) => (
                      <li key={item} className="flex gap-2">
                        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            <p className="font-mono text-[11px] text-[var(--landing-muted)]">
              {result.agents.map((a) => a.name).join(" → ")}
            </p>
          </>
        )}
      </article>
    </div>
  );
}
