"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { BackButton } from "@/components/back-button";
import { PipelineProgress } from "@/components/pipeline-progress";
import { SiteHeader } from "@/components/site-header";
import { runAnalysis } from "@/lib/api";

const DEMO_PROJECTS = [
  {
    repo: "django_app",
    query: "Should we refactor the accounts module?",
  },
  {
    repo: "spring_boot_api",
    query: "Is the payment service ready for microservices migration?",
  },
  {
    repo: "flutter_app",
    query: "Evaluate the state management architecture",
  },
];

function getRepoParam(): string {
  if (typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get("repo")?.trim() ?? "";
}

export default function AnalyzePage() {
  const router = useRouter();
  const started = useRef(false);
  const [repo] = useState<string>(getRepoParam);
  const [currentStep, setCurrentStep] = useState(0);
  const [failed, setFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (started.current) return;
    if (!repo) {
      router.replace("/");
      return;
    }
    started.current = true;

    const match = DEMO_PROJECTS.find(
      (d) => d.repo.toLowerCase() === repo.toLowerCase()
    );
    const query =
      match?.query ??
      `Evaluate architectural health, modularity, and refactoring risks for ${repo}`;

    const timers: number[] = [
      window.setTimeout(() => setCurrentStep(1), 2500),
      window.setTimeout(() => setCurrentStep(2), 5500),
      window.setTimeout(() => setCurrentStep(3), 8500),
      window.setTimeout(() => setCurrentStep(4), 12000),
    ];

    runAnalysis({
      input: { query, repo },
      options: { sample_mode: false },
    })
      .then((result) => {
        timers.forEach((id) => window.clearTimeout(id));
        setCurrentStep(5);
        sessionStorage.setItem(`archus_result_${result.run_id}`, JSON.stringify(result));
        window.setTimeout(() => {
          router.push(`/results/${result.run_id}`);
        }, 450);
      })
      .catch((err) => {
        timers.forEach((id) => window.clearTimeout(id));
        setFailed(true);
        setError(err instanceof Error ? err.message : "Analysis failed");
      });

    return () => {
      timers.forEach((id) => window.clearTimeout(id));
    };
  }, [repo, router]);

  return (
    <div className="landing scan-screen min-h-svh flex flex-col">
      <SiteHeader solid />
      <div className="px-6 pt-3 pb-1">
        <BackButton />
      </div>

      <div className="flex flex-1 items-center justify-center">
        <PipelineProgress currentStep={currentStep} failed={failed} repo={repo} />
      </div>

      {error && (
        <p className="mx-auto max-w-xl px-8 pb-6 text-center text-xs font-mono text-rose-500">{error}</p>
      )}
    </div>
  );
}
