"use client";

import Link from "next/link";
import { Settings2, Shield } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { BentoGridShowcase } from "@/components/ui/bento-product-features";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const cardShell = "landing-bento-card flex flex-col";

const IntegrationCard = () => (
  <Card className={`flex flex-col ${cardShell}`}>
    <CardHeader className="p-6 md:p-8">
      <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-full border border-[var(--landing-border)] bg-[color-mix(in_srgb,var(--landing-fg)_6%,transparent)]">
        <Shield className="h-5 w-5" aria-hidden="true" />
      </div>
      <CardTitle className="text-2xl">SQLGuard</CardTitle>
      <CardDescription className="mt-3 max-w-sm text-[15px] leading-relaxed text-[var(--landing-muted)]">
        Every generated query is parsed as an AST before it runs. Writes are
        blocked. If a number cannot be re-queried, Archus abstains instead of
        inventing it.
      </CardDescription>
    </CardHeader>
    <CardFooter className="mt-auto p-6 md:p-8">
      <Button variant="outline" size="sm" className="rounded-full" asChild>
        <Link href="/about">
          <Settings2 className="mr-2 h-4 w-4" />
          How it works
        </Link>
      </Button>
    </CardFooter>
  </Card>
);

const TrackersCard = () => (
  <Card className={cardShell}>
    <CardContent className="flex h-full flex-col justify-between p-6">
      <CardDescription className="text-[var(--landing-muted)]">
        Planner · Retriever · Analyst · Evaluator · Reporter
      </CardDescription>
      <div>
        <p className="text-5xl font-bold tracking-tight md:text-6xl">Five agents</p>
      </div>
    </CardContent>
  </Card>
);

const StatisticCard = () => (
  <Card className={`relative w-full overflow-hidden ${cardShell}`}>
    <div
      className="absolute inset-0 opacity-20"
      style={{
        backgroundImage: "radial-gradient(currentColor 1px, transparent 1px)",
        backgroundSize: "16px 16px",
      }}
    />
    <CardContent className="relative z-10 flex h-full flex-col items-center justify-center p-6">
      <span className="text-7xl font-bold tracking-tight md:text-8xl">3</span>
      <span className="mt-1 font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--landing-muted)]">
        Decision options
      </span>
    </CardContent>
  </Card>
);

const FocusCard = () => (
  <Card className={cardShell}>
    <CardContent className="flex h-full flex-col justify-between p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base font-medium">Evidence first</CardTitle>
          <CardDescription className="text-[var(--landing-muted)]">
            Independent re-query
          </CardDescription>
        </div>
        <Badge variant="outline">Veto</Badge>
      </div>
      <div>
        <span className="text-6xl font-bold tracking-tight">0</span>
        <span className="ml-2 text-sm text-[var(--landing-muted)]">guesses</span>
      </div>
      <div className="flex justify-between text-xs text-[var(--landing-muted)]">
        <span>Claims must exist in SQL</span>
        <span>Or we abstain</span>
      </div>
    </CardContent>
  </Card>
);

const ProductivityCard = () => (
  <Card className={cardShell}>
    <CardContent className="flex h-full flex-col justify-end p-6">
      <CardTitle className="text-base font-medium">
        Maintain · Refactor · Migrate
      </CardTitle>
      <CardDescription className="mt-1 text-[var(--landing-muted)]">
        A scored comparison of the three options, with an action plan   not a
        debate in a meeting room.
      </CardDescription>
    </CardContent>
  </Card>
);

const ShortcutsCard = () => (
  <Card className={cardShell}>
    <CardContent className="flex h-full flex-col justify-end p-6">
      <CardTitle className="text-base font-medium">Run an analysis</CardTitle>
      <CardDescription className="mt-1 text-[var(--landing-muted)]">
        Paste a repo in the hero. Sample Mode runs against local metrics   no
        live credentials required.
      </CardDescription>
    </CardContent>
  </Card>
);

export function UtilityBento() {
  return (
    <section id="utilite-section" className="landing-features">
      <div className="landing-features-inner">
        <div className="landing-features-head">
          <h2>What Archus actually does</h2>
          <p>
            Five agents, one veto, three options.
            <br />
            Every claim in the report has a SQL source.
          </p>
        </div>

        <BentoGridShowcase
          integration={<IntegrationCard />}
          trackers={<TrackersCard />}
          statistic={<StatisticCard />}
          focus={<FocusCard />}
          productivity={<ProductivityCard />}
          shortcuts={<ShortcutsCard />}
        />
      </div>
    </section>
  );
}
