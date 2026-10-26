import { cn } from "@/lib/utils";

export function ArchusLogo({
  size = 28,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 -2.01 38.443 38.443"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0 text-current", className)}
      aria-hidden="true"
    >
      <g
        transform="translate(-300.778 -214.586)"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="2"
      >
        <path d="M338,239l-4.5-17.1a7.753,7.753,0,0,0-1.9-3.3L329,216" />
        <path d="M302,239l4.5-17.1a7.753,7.753,0,0,1,1.9-3.3L311,216" />
        <path d="M309,244a2.946,2.946,0,0,1-3-3" />
        <path d="M331,244a2.946,2.946,0,0,1-3-3" />
        <circle cx="7" cy="7" r="7" transform="translate(302 234)" />
        <circle cx="7" cy="7" r="7" transform="translate(324 234)" />
        <path d="M324,241a4,4,0,0,0-8,0" strokeLinecap="butt" />
      </g>
    </svg>
  );
}
