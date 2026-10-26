"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { HelpCircle, Moon, Sun } from "lucide-react";

import { ArchusLogo } from "@/components/archus-logo";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

export function SiteHeader({ solid = false }: { solid?: boolean }) {
  const { theme, toggleTheme } = useTheme();
  const pathname = usePathname();
  const faqHref = pathname === "/" ? "#faq-section" : "/#faq-section";

  return (
    <header className={cn("landing-header", solid && "is-solid")}>
      <div className="landing-header-inner">
        <Link href="/" className="landing-brand">
          <ArchusLogo size={28} />
          Archus
        </Link>

        <div className="landing-header-actions">
          <button
            type="button"
            onClick={toggleTheme}
            className="landing-icon-btn"
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? (
              <Sun className="h-[18px] w-[18px]" strokeWidth={1.8} />
            ) : (
              <Moon className="h-[18px] w-[18px]" strokeWidth={1.8} />
            )}
          </button>
          <a href={faqHref} className="landing-icon-btn" aria-label="FAQ">
            <HelpCircle className="h-[18px] w-[18px]" strokeWidth={1.8} />
          </a>
          <Link href="/about" className="landing-nav-link">
            About
          </Link>
        </div>
      </div>
    </header>
  );
}
