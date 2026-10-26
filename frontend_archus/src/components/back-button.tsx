import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export function BackButton({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="back-pill">
      <ArrowLeft size={16} strokeWidth={2} />
      Back
    </Link>
  );
}
