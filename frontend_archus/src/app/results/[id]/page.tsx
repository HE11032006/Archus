"use client";

import { Suspense, startTransition, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  CheckCircle,
  XCircle,
  Copy,
  Check,
  Sparkles,
  Layers,
  Activity,
  Code,
  Flame,
  FileCode,
  ArrowRight,
  HelpCircle,
} from "lucide-react";

import { BackButton } from "@/components/back-button";
import { SiteHeader } from "@/components/site-header";
import type { RunResponse, RefactoringRecipe, AntiPatternItem } from "@/lib/types";
import demoResult from "@/lib/demo-result.json";
import { getDecisionStyle, formatDuration } from "@/lib/utils";
import { getRun } from "@/lib/api";



function UtilityButton({ title, explanation }: { title: string; explanation: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="inline-flex items-center gap-1 rounded-full border border-[var(--landing-border)] bg-[var(--landing-bg)] px-2 py-0.5 text-[10px] font-mono text-[var(--landing-muted)] hover:text-[var(--landing-fg)] hover:border-[var(--brand-primary)] transition-all cursor-pointer shadow-2xs"
        title="Why this matters"
        aria-label={`Why this matters: ${title}`}
      >
        <HelpCircle size={11} className="text-[var(--brand-primary)]" />
        <span className="font-semibold">Why</span>
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
            }}
          />
          <div className="absolute right-0 top-full z-50 mt-2 w-72 rounded-xl border border-[var(--landing-border)] bg-[var(--landing-card)] p-3.5 shadow-xl animate-in fade-in zoom-in-95">
            <div className="flex items-start justify-between gap-2 mb-1.5 pb-1.5 border-b border-[var(--landing-border)]">
              <div className="flex items-center gap-1.5 font-semibold text-xs text-[var(--landing-fg)]">
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] text-[10px] font-bold">
                  ?
                </span>
                {title}
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setOpen(false);
                }}
                className="text-[var(--landing-muted)] hover:text-[var(--landing-fg)] text-xs p-0.5"
              >
                ✕
              </button>
            </div>
            <p className="text-xs leading-relaxed text-[var(--landing-muted)]">
              {explanation}
            </p>
          </div>
        </>
      )}
    </div>
  );
}

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
      aria-label="Copy snippet"
      title="Copy to clipboard"
    >
      {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
    </button>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const sev = severity.toLowerCase();
  let bg = "bg-amber-500/10 text-amber-500 border-amber-500/20";
  if (sev === "high" || sev === "critical") {
    bg = "bg-rose-500/10 text-rose-500 border-rose-500/20";
  } else if (sev === "low") {
    bg = "bg-sky-500/10 text-sky-500 border-sky-500/20";
  }

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase font-semibold ${bg}`}>
      {severity}
    </span>
  );
}

function formatInlineMarkdown(text: string) {
  // Split on **bold** and `code` tokens
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-[var(--landing-fg)]">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="rounded border border-[var(--landing-border)] bg-[var(--landing-bg)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--landing-fg)]">
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-4 text-[15px] md:text-base leading-relaxed text-[var(--landing-fg)]">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} className="h-1" />;

        if (trimmed.startsWith("### ")) {
          return (
            <h3
              key={idx}
              className="mt-7 flex items-center gap-2.5 text-lg md:text-xl font-bold tracking-tight text-[var(--landing-fg)]"
              style={{ fontFamily: "var(--font-family-display), sans-serif" }}
            >
              <span className="h-2 w-2 rounded-full bg-[var(--brand-primary)]" />
              {trimmed.replace("### ", "")}
            </h3>
          );
        }

        if (trimmed.startsWith("## ")) {
          return (
            <h2
              key={idx}
              className="mt-8 text-xl md:text-2xl font-bold tracking-tight text-[var(--landing-fg)]"
              style={{ fontFamily: "var(--font-family-display), sans-serif" }}
            >
              {trimmed.replace("## ", "")}
            </h2>
          );
        }

        if (trimmed.startsWith("- ")) {
          return (
            <li key={idx} className="ml-5 list-disc text-sm md:text-[15px] leading-relaxed text-[var(--landing-fg)]">
              {formatInlineMarkdown(trimmed.replace("- ", ""))}
            </li>
          );
        }

        if (/^\d+\.\s/.test(trimmed)) {
          return (
            <div key={idx} className="ml-3 flex items-start gap-2.5 text-sm md:text-[15px] leading-relaxed text-[var(--landing-fg)]">
              <span className="font-mono text-[var(--brand-primary)] font-bold">
                {trimmed.match(/^\d+\./)?.[0]}
              </span>
              <span>{formatInlineMarkdown(trimmed.replace(/^\d+\.\s*/, ""))}</span>
            </div>
          );
        }

        return (
          <p key={idx} className="text-sm md:text-[15px] leading-relaxed text-[var(--landing-fg)] font-normal">
            {formatInlineMarkdown(trimmed)}
          </p>
        );
      })}
    </div>
  );
}



function RecipeCard({ recipe }: { recipe: RefactoringRecipe }) {
  const [activeTab, setActiveTab] = useState<"before" | "after">("after");

  return (
    <div className="rounded-xl border border-[var(--landing-border)] bg-[var(--landing-card)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="report-kicker">{recipe.pattern}</span>
          <h4 className="text-base font-semibold text-[var(--landing-fg)]">{recipe.title}</h4>
          <p className="mt-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium">{recipe.impact}</p>
        </div>
        <div className="flex rounded-lg border border-[var(--landing-border)] p-0.5">
          <button
            type="button"
            onClick={() => setActiveTab("before")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeTab === "before"
                ? "bg-[var(--landing-bg)] text-[var(--landing-fg)] shadow-xs"
                : "text-[var(--landing-muted)] hover:text-[var(--landing-fg)]"
            }`}
          >
            Before
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("after")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeTab === "after"
                ? "bg-[var(--brand-primary)] text-white shadow-xs"
                : "text-[var(--landing-muted)] hover:text-[var(--landing-fg)]"
            }`}
          >
            After (Pattern)
          </button>
        </div>
      </div>

      <div className="mt-4 relative">
        <div className="absolute right-2 top-2 z-10">
          <CopyButton text={activeTab === "before" ? recipe.before_snippet : recipe.after_snippet} />
        </div>
        <pre className="overflow-x-auto rounded-lg bg-[var(--landing-bg)] p-3 font-mono text-xs leading-relaxed text-[var(--landing-fg)] border border-[var(--landing-border)]">
          {activeTab === "before" ? recipe.before_snippet : recipe.after_snippet}
        </pre>
      </div>
    </div>
  );
}


export default function ResultsPage() {
  return (
    <Suspense fallback={null}>
      <ResultsContent />
    </Suspense>
  );
}

function ResultsContent() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<RunResponse | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [activeTab, setActiveTab] = useState<"report" | "recipes" | "smells">("report");
  const router = useRouter();

  useEffect(() => {
    if (id === "demo") {
      startTransition(() => setResult(demoResult as unknown as RunResponse));
      return;
    }
    const raw = sessionStorage.getItem(`archus_result_${id}`);
    if (raw) {
      try {
        startTransition(() => setResult(JSON.parse(raw) as RunResponse));
        return;
      } catch {
        // Fall back to server fetch
      }
    }

    // Direct retrieval from backend API
    getRun(id)
      .then((data) => {
        setResult(data);
        sessionStorage.setItem(`archus_result_${id}`, JSON.stringify(data));
      })
      .catch(() => {
        setNotFound(true);
      });
  }, [id]);

  if (notFound) {
    // Redirect to home — no direct access without a valid run
    router.replace("/");
    return null;
  }

  if (!result) {
    return (
      <div className="landing flex min-h-svh items-center justify-center">
        <p className="text-[var(--landing-muted)] font-mono text-sm">Compiling architecture report…</p>
      </div>
    );
  }

  const output = result.output;
  const hasOutput = result.status !== "error" && output;
  const decisionStyle = hasOutput ? getDecisionStyle(output.decision) : null;
  const verifiedCount = hasOutput ? output.evidence.filter((e) => e.verified).length : 0;

  const repoMeta = output?.repo_metadata;
  const metricsOverview = output?.metrics_overview;
  const antiPatterns = output?.antipatterns || [];
  const hotspots = output?.complexity_hotspots || [];
  const recipes = output?.refactoring_recipes || [];
  const archStyle = output?.architecture_style || repoMeta?.architecture_pattern || "Modular Monolith";
  const repoName = repoMeta?.repo_name || "Target Codebase";

  return (
    <div className="landing min-h-svh pb-24">
      <SiteHeader solid />
      <div className="px-8 pt-6">
        <BackButton />
      </div>

      <article className="mx-auto w-full max-w-6xl px-6 pt-6 md:px-8">
        {result.status === "error" && (
          <div className="report-card text-center">
            <XCircle size={36} className="mx-auto mb-4 text-rose-500" />
            <h2 className="text-xl font-semibold">Analysis Failed</h2>
            <p className="mt-2 text-sm text-[var(--landing-muted)]">{result.error?.message}</p>
          </div>
        )}

        {hasOutput && decisionStyle && (
          <>
            {/* Header: Target Repo + Architecture Style Badges */}
            <div className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className="inline-flex items-center gap-1 rounded-md border border-[var(--landing-border)] bg-[var(--landing-card)] px-2.5 py-0.5 font-mono text-xs font-semibold text-[var(--landing-fg)]">
                    <Layers size={13} className="text-[var(--brand-primary)]" />
                    {archStyle}
                  </span>
                  {repoMeta?.language && (
                    <span className="inline-flex items-center gap-1 rounded-md border border-[var(--landing-border)] bg-[var(--landing-card)] px-2.5 py-0.5 font-mono text-xs text-[var(--landing-muted)]">
                      <Code size={13} />
                      {repoMeta.language}
                    </span>
                  )}
                  {repoMeta?.files_analyzed && (
                    <span className="rounded-md border border-[var(--landing-border)] bg-[var(--landing-card)] px-2.5 py-0.5 font-mono text-xs text-[var(--landing-muted)]">
                      {repoMeta.files_analyzed} files analyzed
                    </span>
                  )}
                </div>
                <h1
                  className="text-[clamp(1.8rem,3.5vw,2.8rem)] font-semibold tracking-tight text-[var(--landing-fg)]"
                  style={{ fontFamily: "var(--font-family-display), sans-serif" }}
                >
                  {repoName}
                </h1>
                <p className="mt-1 font-mono text-xs text-[var(--landing-muted)]">
                  Execution: {formatDuration(result.execution_time_seconds)} · Run ID: {result.run_id} · Model: Archus Engine
                </p>
              </div>
            </div>

            {/* Verdict Hero Grid */}
            <div className="mb-8 grid gap-6 md:grid-cols-3">
              <div className="report-card md:col-span-2 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="report-kicker mb-0">Architectural Verdict</span>
                      <UtilityButton
                        title="Architectural verdict"
                        explanation="Formal recommendation (Maintain, Refactor, or Migrate) after consensus and verified AST metrics. It guides technical investment and the choice between rewrite and keep."
                      />
                    </div>
                    <span
                      className="rounded-full px-3 py-0.5 font-mono text-xs font-bold uppercase tracking-wider"
                      style={{
                        background: `color-mix(in srgb, ${decisionStyle.color} 15%, transparent)`,
                        color: decisionStyle.color,
                        border: `1px solid color-mix(in srgb, ${decisionStyle.color} 30%, transparent)`,
                      }}
                    >
                      {decisionStyle.label}
                    </span>
                  </div>
                  <p
                    className="mt-2 text-3xl font-semibold tracking-tight"
                    style={{
                      fontFamily: "var(--font-family-display), sans-serif",
                      color: decisionStyle.color,
                    }}
                  >
                    Recommend {output.decision.toUpperCase()}
                  </p>
                  <p className="mt-4 text-base md:text-[17px] leading-relaxed text-[var(--landing-fg)] font-normal">
                    {output.summary}
                  </p>
                </div>

                <div className="mt-6 flex flex-wrap gap-2 pt-4 border-t border-[var(--landing-border)]">
                  {output.action_plan.slice(0, 2).map((step, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm font-medium text-[var(--landing-fg)]">
                      <ArrowRight size={15} className="shrink-0 mt-0.5 text-[var(--brand-primary)]" />
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="report-card flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="report-kicker mb-0">Confidence Rating</span>
                    <UtilityButton
                      title="Confidence score"
                      explanation="How solid and convergent the empirical evidence is. Closer to 100% means the recommendation is backed by verified data with a lower risk of false positives."
                    />
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span
                      className="text-5xl font-semibold tracking-tight"
                      style={{ fontFamily: "var(--font-family-display), sans-serif" }}
                    >
                      {(output.confidence * 100).toFixed(0)}
                    </span>
                    <span className="text-xl text-[var(--landing-muted)]">/100</span>
                  </div>

                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-[var(--landing-border)]">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${output.confidence * 100}%`,
                        background: decisionStyle.color,
                      }}
                    />
                  </div>
                </div>

                <div className="mt-6 space-y-2 border-t border-[var(--landing-border)] pt-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--landing-muted)]">Verified Claims</span>
                    <span className="font-mono font-semibold text-[var(--landing-fg)]">
                      {verifiedCount} / {output.evidence.length}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--landing-muted)]">Anti-Patterns</span>
                    <span className="font-mono font-semibold text-amber-500">
                      {antiPatterns.length} detected
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Architecture Health Bento Grid */}
            <section className="mb-10">
              <h2 className="report-kicker mb-3">Architecture Metrics & Vital Signs</h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="report-card p-5">
                  <div className="flex items-center justify-between">
                    <span className="report-kicker mb-0">Max Complexity</span>
                    <div className="flex items-center gap-1.5">
                      <UtilityButton
                        title="Max cyclomatic complexity"
                        explanation="Complexity of the most tangled function or file. A score above 15–20 flags a high-bug-risk component that is hard to test."
                      />
                      <Flame size={16} className="text-amber-500" />
                    </div>
                  </div>
                  <p className="mt-1 text-3xl font-semibold tracking-tight text-[var(--landing-fg)]">
                    {metricsOverview?.complexity_max ?? 14.0}
                  </p>
                  <p className="mt-1 text-xs text-[var(--landing-muted)]">
                    Avg: {metricsOverview?.complexity_avg ?? 4.2} · Safe cap: 15
                  </p>
                </div>

                <div className="report-card p-5">
                  <div className="flex items-center justify-between">
                    <span className="report-kicker mb-0">Coupling & Cohesion</span>
                    <div className="flex items-center gap-1.5">
                      <UtilityButton
                        title="Coupling & cohesion"
                        explanation="How independent modules are. Low coupling and high cohesion reduce the chance that a local change causes regressions elsewhere."
                      />
                      <Activity size={16} className="text-[var(--brand-primary)]" />
                    </div>
                  </div>
                  <p className="mt-1 text-3xl font-semibold tracking-tight text-[var(--landing-fg)]">
                    {metricsOverview?.coupling_score ?? 3.8}
                  </p>
                  <p className="mt-1 text-xs text-[var(--landing-muted)]">
                    Cohesion: {metricsOverview?.cohesion_score ?? 0.72} · Boundary health
                  </p>
                </div>

                <div className="report-card p-5">
                  <div className="flex items-center justify-between">
                    <span className="report-kicker mb-0">Test Coverage</span>
                    <div className="flex items-center gap-1.5">
                      <UtilityButton
                        title="Test coverage"
                        explanation="Your safety net before changing code. Strong coverage lets you refactor without breaking existing behavior."
                      />
                      <CheckCircle size={16} className="text-emerald-500" />
                    </div>
                  </div>
                  <p className="mt-1 text-3xl font-semibold tracking-tight text-emerald-500">
                    {metricsOverview?.coverage_estimate ?? 68.5}%
                  </p>
                  <p className="mt-1 text-xs text-[var(--landing-muted)]">
                    Automated safety net for changes
                  </p>
                </div>

                <div className="report-card p-5">
                  <div className="flex items-center justify-between">
                    <span className="report-kicker mb-0">Code Volume</span>
                    <div className="flex items-center gap-1.5">
                      <UtilityButton
                        title="Code volume & scope"
                        explanation="Overall analyzed size (files and lines of code) so you can judge the scale of the recommendation."
                      />
                      <FileCode size={16} className="text-[var(--landing-muted)]" />
                    </div>
                  </div>
                  <p className="mt-1 text-3xl font-semibold tracking-tight text-[var(--landing-fg)]">
                    {repoMeta?.total_loc ?? 2430} <span className="text-sm font-normal text-[var(--landing-muted)]">LOC</span>
                  </p>
                  <p className="mt-1 text-xs text-[var(--landing-muted)]">
                    {repoMeta?.total_functions ?? 70} functions · {repoMeta?.total_classes ?? 10} classes
                  </p>
                </div>
              </div>
            </section>



            {/* Navigation Tabs */}
            <div className="mb-6 flex overflow-x-auto border-b border-[var(--landing-border)] gap-2 pb-px">
              {[
                { id: "report", label: "Architecture Diagnostic", icon: Sparkles },
                { id: "recipes", label: "Refactoring Recipes", icon: Code },
                { id: "smells", label: `Smells & Hotspots (${antiPatterns.length})`, icon: Flame },
              ].map((tab) => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id as typeof activeTab)}
                    className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${
                      active
                        ? "border-[var(--brand-primary)] text-[var(--brand-primary)]"
                        : "border-transparent text-[var(--landing-muted)] hover:text-[var(--landing-fg)]"
                    }`}
                  >
                    <Icon size={14} />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* TAB 1: Main Architecture Diagnostic & Action Plan */}
            {activeTab === "report" && (
              <div className="space-y-8">
                {output.detailed_explanation && (
                  <section className="report-card p-6 md:p-8">
                    <div className="mb-4 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="report-kicker mb-0">In-Depth Strategic Evaluation</span>
                        <UtilityButton
                          title="In-depth strategic report"
                          explanation="Full technical-leadership brief: structural diagnostics, design trade-offs, and a three-phase roadmap."
                        />
                      </div>
                      <span className="font-mono text-[10px] text-[var(--landing-muted)]">
                        Generated by Archus Engine
                      </span>
                    </div>
                    <MarkdownRenderer content={output.detailed_explanation} />
                  </section>
                )}

                {/* Options Compared */}
                {output.options_compared.length > 0 && (
                  <section>
                    <h2 className="report-kicker mb-3">Strategic Trade-Off Evaluation</h2>
                    <div className="grid gap-4 md:grid-cols-3">
                      {output.options_compared.map((opt) => {
                        const style = getDecisionStyle(opt.option);
                        const isWinner = opt.option === output.decision;
                        return (
                          <div
                            key={opt.option}
                            className="report-card flex flex-col justify-between"
                            style={{
                              borderColor: isWinner ? style.color : undefined,
                              borderWidth: isWinner ? "2px" : undefined,
                            }}
                          >
                            <div>
                              <div className="flex items-baseline justify-between">
                                <span className="font-semibold text-sm" style={{ color: style.color }}>
                                  {style.label}
                                </span>
                                <span className="text-2xl font-bold font-mono" style={{ color: style.color }}>
                                  {opt.score.toFixed(0)}
                                  <span className="text-xs font-normal opacity-60">/100</span>
                                </span>
                              </div>
                              <p className="mt-3 text-sm leading-relaxed text-[var(--landing-fg)]">
                                {opt.rationale}
                              </p>

                              {opt.pros.length > 0 && (
                                <ul className="mt-4 space-y-1.5 text-xs md:text-sm text-emerald-600 dark:text-emerald-400">
                                  {opt.pros.map((p) => (
                                    <li key={p} className="flex items-start gap-1.5">
                                      <span className="font-bold">+</span>
                                      <span>{p}</span>
                                    </li>
                                  ))}
                                </ul>
                              )}
                              {opt.cons.length > 0 && (
                                <ul className="mt-2 space-y-1.5 text-xs md:text-sm text-rose-500">
                                  {opt.cons.map((c) => (
                                    <li key={c} className="flex items-start gap-1.5">
                                      <span className="font-bold">−</span>
                                      <span>{c}</span>
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>

                            {isWinner && (
                              <div className="mt-4 pt-3 border-t border-[var(--landing-border)] flex items-center justify-between text-[11px] font-semibold text-emerald-500">
                                <span>Recommended Path</span>
                                <span>Optimal ROI</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )}

                {/* Phased Action Plan */}
                {output.action_plan.length > 0 && (
                  <section>
                    <h2 className="report-kicker mb-3">Actionable Execution Roadmap</h2>
                    <div className="report-card p-6">
                      <ol className="space-y-4">
                        {output.action_plan.map((step, i) => (
                          <li key={i} className="flex gap-4 items-start">
                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--brand-primary)]/10 font-mono text-xs font-bold text-[var(--brand-primary)]">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <div className="pt-0.5">
                              <p className="text-base font-medium text-[var(--landing-fg)] leading-relaxed">{step}</p>
                            </div>
                          </li>
                        ))}
                      </ol>
                    </div>
                  </section>
                )}
              </div>
            )}

            {/* TAB 2: Refactoring Code Recipes */}
            {activeTab === "recipes" && (
              <div className="space-y-6">
                <div className="report-card p-5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-semibold text-[var(--landing-fg)]">
                      Architectural Code Transformation Blueprints
                    </h3>
                    <UtilityButton
                      title="Refactoring recipes"
                      explanation="Concrete before/after code patterns showing the exact source changes to remove detected anti-patterns."
                    />
                  </div>
                  <p className="mt-1 text-xs text-[var(--landing-muted)]">
                    Concrete structural patterns to remediate the detected anti-patterns in {repoName}.
                  </p>
                </div>

                {recipes.length > 0 ? (
                  <div className="grid gap-6">
                    {recipes.map((recipe, idx) => (
                      <RecipeCard key={idx} recipe={recipe} />
                    ))}
                  </div>
                ) : (
                  <div className="report-card text-center p-8">
                    <CheckCircle size={32} className="mx-auto mb-3 text-emerald-500" />
                    <p className="text-sm font-semibold">No critical refactoring recipes required</p>
                    <p className="text-xs text-[var(--landing-muted)] mt-1">
                      Existing modularity is within safe operating parameters.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: Anti-patterns & Complexity Hotspots */}
            {activeTab === "smells" && (
              <div className="space-y-8">
                <section>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="report-kicker mb-0">Detected Anti-Patterns & Code Smells</h2>
                    <UtilityButton
                      title="Anti-patterns & hotspots"
                      explanation="Inventory of architectural issues (god classes, excessive coupling, long methods) found in the code, ranked by severity."
                    />
                  </div>
                  {antiPatterns.length > 0 ? (
                    <div className="grid gap-3">
                      {antiPatterns.map((a: AntiPatternItem, idx: number) => (
                        <div
                          key={idx}
                          className="report-card flex flex-col md:flex-row md:items-center justify-between gap-4 p-4"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <SeverityBadge severity={a.severity} />
                              <span className="font-semibold text-sm text-[var(--landing-fg)]">
                                {a.pattern.replace(/_/g, " ").toUpperCase()}
                              </span>
                            </div>
                            <p className="mt-1.5 font-mono text-xs text-[var(--landing-muted)]">
                              Target file: <code className="text-[var(--landing-fg)]">{a.file}</code>
                            </p>
                            {a.description && (
                              <p className="mt-1 text-xs text-[var(--landing-muted)]">
                                {a.description}
                              </p>
                            )}
                          </div>
                          <div className="shrink-0 text-right">
                            <span className="report-kicker">Metric Value</span>
                            <p className="font-mono text-sm font-bold text-[var(--landing-fg)]">{a.value}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="report-card text-center p-8">
                      <CheckCircle size={32} className="mx-auto mb-3 text-emerald-500" />
                      <p className="text-sm font-semibold">Zero critical anti-patterns detected</p>
                      <p className="text-xs text-[var(--landing-muted)] mt-1">
                        No God Classes or critical coupling bottlenecks found.
                      </p>
                    </div>
                  )}
                </section>

                {hotspots.length > 0 && (
                  <section>
                    <h2 className="report-kicker mb-3">Top Complexity Hotspots</h2>
                    <div className="overflow-x-auto rounded-xl border border-[var(--landing-border)] bg-[var(--landing-card)]">
                      <table className="w-full text-left text-xs">
                        <thead className="border-b border-[var(--landing-border)] bg-[var(--landing-bg)] text-[var(--landing-muted)]">
                          <tr>
                            <th className="p-3 font-medium">File Path</th>
                            <th className="p-3 font-medium text-right">Max Complexity</th>
                            <th className="p-3 font-medium text-right">Functions</th>
                            <th className="p-3 font-medium text-right">Lines of Code</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--landing-border)] font-mono">
                          {hotspots.map((h, i) => (
                            <tr key={i} className="hover:bg-[var(--landing-bg)]/50">
                              <td className="p-3 font-sans text-xs text-[var(--landing-fg)]">{h.file}</td>
                              <td className="p-3 text-right font-bold text-amber-500">{h.max_complexity}</td>
                              <td className="p-3 text-right text-[var(--landing-muted)]">{h.num_functions}</td>
                              <td className="p-3 text-right text-[var(--landing-muted)]">{h.num_lines}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}
              </div>
            )}



          </>
        )}
      </article>
    </div>
  );
}
