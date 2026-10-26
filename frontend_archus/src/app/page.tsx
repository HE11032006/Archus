"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { UtilityBento } from "@/components/landing/utility-bento";
import Faq05 from "@/components/ui/faq-05";
import { LiquidFillInput } from "@/components/ui/liquid-fill-input";

export default function HomePage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  const goToAnalyze = () => {
    const value = searchQuery.trim();
    if (!value) {
      router.push("/analyze");
      return;
    }
    router.push(`/analyze?repo=${encodeURIComponent(value)}`);
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
              Evidence-backed decisions   Maintain, Refactor, or Migrate.
            </p>

            <form
              className="landing-search"
              onSubmit={(event) => {
                event.preventDefault();
                goToAnalyze();
              }}
            >
              <div className="landing-search-pill">
                <LiquidFillInput
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Find a repo or paste a GitHub URL"
                  aria-label="Repository to analyze"
                />
                <button type="submit" title="Search" className="landing-search-submit">
                  <Search size={18} strokeWidth={2.2} />
                </button>
              </div>
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
