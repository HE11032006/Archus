"use client";

import * as React from "react";
import { startTransition } from "react";

import { cn } from "@/lib/utils";

type LiquidFillInputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  placeholder?: string;
};

export function LiquidFillInput({
  placeholder = "Focus for liquid…",
  className,
  onFocus,
  onBlur,
  ...props
}: LiquidFillInputProps) {
  const [focused, setFocused] = React.useState(false);
  const phaseRef = React.useRef(0);
  const fillRef = React.useRef(100);
  const [clipPath, setClipPath] = React.useState(
    "polygon(0% 100%,100% 100%,100% 100%,0% 100%)"
  );
  const rafRef = React.useRef<number | null>(null);

  React.useEffect(() => {
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion:reduce)"
    ).matches;
    const target = focused ? 65 : 100;
    if (prefersReduced) {
      startTransition(() =>
        setClipPath(
          `polygon(0% 100%,100% 100%,100% ${target}%,0% ${target}%)`
        )
      );
      return;
    }
    const animate = () => {
      phaseRef.current += 0.06;
      fillRef.current += (target - fillRef.current) * 0.04;
      const f = fillRef.current;
      const n = 20;
      const pts = [`0% 100%`, `100% 100%`, `100% ${f.toFixed(1)}%`];
      for (let i = n; i >= 0; i--) {
        const x = (i / n) * 100;
        const y = f - 4 * Math.sin((x / 100) * Math.PI * 4 + phaseRef.current);
        pts.push(`${x.toFixed(1)}% ${y.toFixed(1)}%`);
      }
      pts.push(`0% ${f.toFixed(1)}%`);
      setClipPath(`polygon(${pts.join(",")})`);
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [focused]);

  return (
    <div className="relative w-full overflow-hidden rounded-full">
      <div
        className="pointer-events-none absolute inset-px rounded-full"
        style={{
          background:
            "linear-gradient(to top, rgba(167,171,178,0.28), rgba(167,171,178,0.08))",
          clipPath,
        }}
      />
      <input
        type="text"
        placeholder={placeholder}
        {...props}
        onFocus={(event) => {
          setFocused(true);
          onFocus?.(event);
        }}
        onBlur={(event) => {
          setFocused(false);
          onBlur?.(event);
        }}
        className={cn(
          "relative w-full bg-transparent text-[15px] text-[var(--landing-fg)] outline-none placeholder:text-[color-mix(in_srgb,var(--landing-fg)_40%,transparent)]",
          className
        )}
      />
    </div>
  );
}
