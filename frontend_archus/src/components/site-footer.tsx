import Link from "next/link";

import { ArchusLogo } from "@/components/archus-logo";

export function SiteFooter() {
  return (
    <footer className="landing-footer">
      <div className="landing-footer-inner">
        <Link href="/" className="landing-footer-brand landing-brand">
          <ArchusLogo size={20} className="text-white" />
          Archus
        </Link>
        <p className="landing-footer-copy">© 2026 Archus. All rights reserved.</p>
        <a href="#faq-section" className="landing-footer-link">
          FAQ
        </a>
      </div>
    </footer>
  );
}
