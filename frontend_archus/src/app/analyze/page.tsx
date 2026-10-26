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

export default function AnalyzePage() {
  const router = useRouter();
  const started = useRef(false);
  const [repo, setRepo] = useState("");
  const [currentStep, setCurrentStep] = useState(0);
  const [failed, setFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (started.current) return;
    const params = new URLSearchParams(window.location.search);
    const repoParam = params.get("repo")?.trim();
    if (!repoParam) {
      router.replace("/");
      return;
    }
    started.current = true;
    setRepo(repoParam);

    const match = DEMO_PROJECTS.find(
      (d) => d.repo.toLowerCase() === repoParam.toLowerCase()
    );
    const query =
      match?.query ??
      `Evaluate architectural health, modularity, and refactoring risks for ${repoParam}`;

    const timers: number[] = [];
    for (let i = 1; i <= 4; i++) {
      timers.push(window.setTimeout(() => setCurrentStep(i), i * 1400));
    }

    runAnalysis({
      input: { query, repo: repoParam },
      options: { sample_mode: true },
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
  }, [router]);

  return (
    <div className="landing scan-screen">
      <SiteHeader solid />
      <div className="px-8 pt-6">
        <BackButton />
      </div>

      <PipelineProgress currentStep={currentStep} failed={failed} repo={repo} />

      {error && (
        <p className="mx-auto max-w-xl px-8 pb-16 text-center text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}
