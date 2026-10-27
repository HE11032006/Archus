"use client";

import { useState } from "react";
import { Search, AlertCircle } from "lucide-react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { UtilityBento } from "@/components/landing/utility-bento";
import Faq05 from "@/components/ui/faq-05";
import { LiquidFillInput } from "@/components/ui/liquid-fill-input";

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const validateRepo = (input: string): { valid: boolean; message?: string } => {
    const val = input.trim();
    if (!val) {
      return {
        valid: false,
        message: "Enter a GitHub URL (e.g. https://github.com/owner/repo) or a project name.",
      };
    }
    if (val.startsWith("http://") || val.startsWith("https://")) {
      const isGithub = /github\.com\/[\w.-]+\/[\w.-]+/i.test(val);
      if (!isGithub) {
        return {
          valid: false,
          message: "Only public GitHub repositories are supported. Example: https://github.com/pallets/flask",
        };
      }
      return { valid: true };
    }
    // Allow owner/repo, single identifier, or local sample
    if (/^[\w.-]+(\/[\w.-]+)?$/.test(val)) {
      return { valid: true };
    }
    return {
      valid: false,
      message: "Invalid format. Use 'owner/repo' or a full GitHub URL.",
    };
  };

  const goToAnalyze = () => {
    const validation = validateRepo(searchQuery);
    if (!validation.valid) {
      setValidationError(validation.message || "Invalid input.");
      return;
    }
    setValidationError(null);
    const next = `/analyze?repo=${encodeURIComponent(searchQuery.trim())}`;
    if (typeof document !== "undefined") {
      (document.activeElement as HTMLElement | null)?.blur();
    }
    // Delay so the Enter key that submitted the form cannot activate the header "home" link.
    window.setTimeout(() => {
      window.location.assign(next);
    }, 200);
  };

  return (
    <div className="landing">
      <SiteHeader />

      <main>
        <section className="landing-hero">
          <div className="landing-hero-inner">
            <h1 className="landing-hero-title">Archus</h1>
            <p className="landing-hero-sub">
              A new perspective on architecture for the agentic era.
              <br />
              Evidence-backed decisions | Maintain, Refactor, or Migrate.
            </p>

            <form
              className="landing-search"
              onSubmit={(event) => {
                event.preventDefault();
                goToAnalyze();
              }}
            >
              <div
                className={`landing-search-pill transition-all ${
                  validationError ? "ring-2 ring-rose-500/60 border-rose-500/50" : ""
                }`}
              >
                <LiquidFillInput
                  value={searchQuery}
                  onChange={(event) => {
                    setSearchQuery(event.target.value);
                    if (validationError) setValidationError(null);
                  }}
                  placeholder="Find a repo or paste a GitHub URL"
                  aria-label="Repository to analyze"
                />
                <button type="submit" title="Search" className="landing-search-submit">
                  <Search size={18} strokeWidth={2.2} />
                </button>
              </div>

              {validationError && (
                <div
                  role="alert"
                  className="mt-3 flex items-center justify-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-xs font-medium text-rose-500 animate-in fade-in slide-in-from-top-1"
                >
                  <AlertCircle size={15} className="shrink-0" />
                  <span>{validationError}</span>
                </div>
              )}
            </form>
          </div>
        </section>

        <UtilityBento />
        <Faq05 />
      </main>

      <SiteFooter />
    </div>
  );
}
