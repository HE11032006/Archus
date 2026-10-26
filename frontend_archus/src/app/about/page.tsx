"use client";

import Link from "next/link";

import { BackButton } from "@/components/back-button";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

const PIPELINE = [
  {
    step: "01",
    name: "Planner",
    input: "Your architecture question",
    output: "Criteria and SQL retrieval plan",
    desc: "Turns a Maintain / Refactor / Migrate question into measurable metrics and thresholds.",
  },
  {
    step: "02",
    name: "Retriever",
    input: "The query plan",
    output: "Metric rows with provenance",
    desc: "Runs read-only SQL through SQLGuard against Zetaris or local SQLite.",
  },
  {
    step: "03",
    name: "Analyst",
    input: "Retrieved metrics",
    output: "Draft decision and option scores",
    desc: "Compares the three options and proposes a first rationale and action plan.",
  },
  {
    step: "04",
    name: "EvidenceEvaluator",
    input: "Claims from the Analyst",
    output: "Verified claims, or abstention",
    desc: "Re-queries every number independently. Can send the dossier back, or refuse to conclude.",
  },
  {
    step: "05",
    name: "Reporter",
    input: "Verified evidence",
    output: "Decision record",
    desc: "Assembles the verdict, confidence, evidence table, and next steps.",
  },
];

export default function AboutPage() {
  return (
    <div className="landing min-h-svh">
      <SiteHeader solid />
      <div className="px-8 pt-6">
        <BackButton />
      </div>

      <main className="mx-auto w-full max-w-4xl px-6 py-10 md:px-8 md:py-16">
        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-[var(--landing-muted)]">
          Architecture
        </p>
        <h1
          className="mt-4 max-w-xl text-4xl font-semibold tracking-tight md:text-5xl"
          style={{ fontFamily: "var(--font-family-display), sans-serif" }}
        >
          How Archus reaches a decision
        </h1>
        <p className="mt-5 max-w-xl text-base leading-relaxed text-[var(--landing-muted)] md:text-lg">
          Five agents, one veto. The report only keeps claims that exist in the
          metric tables. If the data is missing, the system abstains.
        </p>

        <ol className="mt-16 space-y-0">
          {PIPELINE.map((step) => (
            <li
              key={step.name}
              className="grid gap-4 border-t border-[var(--landing-border)] py-8 md:grid-cols-[88px_1fr]"
            >
              <span className="font-mono text-sm text-[var(--landing-muted)]">{step.step}</span>
              <div>
                <h2 className="text-xl font-semibold tracking-tight">{step.name}</h2>
                <p className="mt-2 text-sm leading-relaxed text-[var(--landing-muted)]">{step.desc}</p>
                <dl className="mt-4 grid gap-3 text-xs sm:grid-cols-2">
                  <div>
                    <dt className="font-mono uppercase tracking-wider text-[var(--landing-muted)]">Input</dt>
                    <dd className="mt-1">{step.input}</dd>
                  </div>
                  <div>
                    <dt className="font-mono uppercase tracking-wider text-[var(--landing-muted)]">Output</dt>
                    <dd className="mt-1">{step.output}</dd>
                  </div>
                </dl>
              </div>
            </li>
          ))}
        </ol>

        <section className="mt-8 border-t border-[var(--landing-border)] pt-12">
          <h2
            className="text-2xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-family-display), sans-serif" }}
          >
            What gets queried
          </h2>
          <ul className="mt-6 space-y-3 text-sm text-[var(--landing-muted)]">
            <li>
              <code className="mr-2 font-mono text-[var(--landing-fg)]">modules</code>
              complexity, coupling, cohesion
            </li>
            <li>
              <code className="mr-2 font-mono text-[var(--landing-fg)]">antipatterns</code>
              god classes, deep inheritance, circular deps
            </li>
            <li>
              <code className="mr-2 font-mono text-[var(--landing-fg)]">tests</code>
              coverage estimates
            </li>
            <li>
              <code className="mr-2 font-mono text-[var(--landing-fg)]">git_hotspots</code>
              change frequency and churn
            </li>
          </ul>
        </section>

        <div className="mt-16">
          <Link
            href="/analyze?repo=django_app"
            className="inline-flex rounded-full border border-[var(--landing-border)] px-5 py-2.5 text-sm font-medium hover:bg-[color-mix(in_srgb,var(--landing-fg)_6%,transparent)]"
          >
            Run a demo analysis
          </Link>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
