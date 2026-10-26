import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}

export function getDecisionStyle(decision: string) {
  switch (decision) {
    case "maintain":
      return { color: "#6b8f71", label: "Maintain", bg: "rgba(107,143,113,0.12)", border: "rgba(107,143,113,0.35)" };
    case "refactor":
      return { color: "#6a7d92", label: "Refactor", bg: "rgba(106,125,146,0.12)", border: "rgba(106,125,146,0.35)" };
    case "migrate":
      return { color: "#b08968", label: "Migrate", bg: "rgba(176,137,104,0.12)", border: "rgba(176,137,104,0.35)" };
    case "insufficient_evidence":
      return { color: "#8a8a84", label: "Insufficient Evidence", bg: "rgba(138,138,132,0.12)", border: "rgba(138,138,132,0.35)" };
    default:
      return { color: "inherit", label: decision, bg: "transparent", border: "currentColor" };
  }
}
