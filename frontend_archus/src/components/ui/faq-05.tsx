"use client";

import * as React from "react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const FAQS: readonly { id: string; q: string; a: string }[] = [
  {
    id: "item-1",
    q: "What is Archus, exactly?",
    a: "Archus is a multi-agent architecture system that audits a repository and recommends Maintain, Refactor, or Migrate. Every claim is backed by verified SQL evidence   if the data is missing, it abstains instead of guessing.",
  },
  {
    id: "item-2",
    q: "How do the five agents work together?",
    a: "Planner turns your question into metric queries. Retriever runs them through SQLGuard. Analyst scores the three options. EvidenceEvaluator re-queries and can veto. Reporter writes the sourced decision and action plan.",
  },
  {
    id: "item-3",
    q: "What does SQLGuard actually block?",
    a: "Every generated query is parsed as an AST before it runs. Writes (DROP, DELETE, UPDATE), injections, and multi-statement batches are rejected. Only read-only SELECTs with a LIMIT are allowed.",
  },
  {
    id: "item-4",
    q: "Which languages and projects are supported?",
    a: "Archus is language-agnostic. It works with Python, Java/Kotlin, TypeScript, Dart/Flutter, Go, C#, Rust, PHP, C++, and more   from legacy monoliths to services and libraries.",
  },
  {
    id: "item-5",
    q: "Can I try it without API keys?",
    a: "Yes. Sample Mode ships with three demo codebases (Django, Spring Boot, Flutter). You can run a full analysis locally against SQLite, with no Zetaris credentials.",
  },
];

const Faq05 = () => {
  return (
    <section id="faq-section" data-slot="faq" className="landing-faq">
      <div className="landing-faq-frame">
        <div data-slot="faq-intro" className="landing-faq-intro">
          <span className="landing-faq-kicker">FAQ</span>
          <h2>
            Questions,
            <br />
            answered.
          </h2>
          <p>
            The things people ask most often. Still stuck? Reach out and we&apos;ll
            walk you through it.
          </p>
        </div>

        <div data-slot="faq-list" className="landing-faq-list">
          <Accordion type="single" collapsible className="w-full">
            {FAQS.map((item) => (
              <AccordionItem key={item.id} value={item.id}>
                <AccordionTrigger className="py-5 text-left text-[15px] font-medium hover:no-underline">
                  {item.q}
                </AccordionTrigger>
                <AccordionContent className="text-[var(--landing-muted)]">{item.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
};

export default Faq05;
