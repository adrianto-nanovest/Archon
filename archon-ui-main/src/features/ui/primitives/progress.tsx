/**
 * Progress primitive - Radix UI Progress with Tron-inspired styling
 *
 * Wraps @radix-ui/react-progress with accessibility attributes and
 * glassmorphism styling consistent with our design system.
 */

import * as ProgressPrimitive from "@radix-ui/react-progress";
import { cn } from "./styles";

type ProgressSize = "sm" | "md" | "lg";
type ProgressColor = "cyan" | "green" | "orange" | "red" | "purple" | "blue";

interface ProgressProps {
  /** Progress value from 0 to 100 */
  value: number;
  /** Size variant */
  size?: ProgressSize;
  /** Color variant */
  color?: ProgressColor;
  /** Accessible label for screen readers */
  label?: string;
  /** Optional className for the root element */
  className?: string;
}

const sizeClasses: Record<ProgressSize, string> = {
  sm: "h-1",
  md: "h-2",
  lg: "h-3",
};

const colorClasses: Record<ProgressColor, string> = {
  cyan: "bg-cyan-500 dark:bg-cyan-400",
  green: "bg-green-500 dark:bg-green-400",
  orange: "bg-orange-500 dark:bg-orange-400",
  red: "bg-red-500 dark:bg-red-400",
  purple: "bg-purple-500 dark:bg-purple-400",
  blue: "bg-blue-500 dark:bg-blue-400",
};

const glowClasses: Record<ProgressColor, string> = {
  cyan: "shadow-[0_0_8px_rgba(34,211,238,0.5)]",
  green: "shadow-[0_0_8px_rgba(34,197,94,0.5)]",
  orange: "shadow-[0_0_8px_rgba(251,146,60,0.5)]",
  red: "shadow-[0_0_8px_rgba(239,68,68,0.5)]",
  purple: "shadow-[0_0_8px_rgba(168,85,247,0.5)]",
  blue: "shadow-[0_0_8px_rgba(59,130,246,0.5)]",
};

export function Progress({ value, size = "md", color = "cyan", label, className }: ProgressProps) {
  const clampedValue = Math.max(0, Math.min(100, value));

  return (
    <ProgressPrimitive.Root
      className={cn(
        "relative w-full overflow-hidden rounded-full",
        "bg-gray-200/50 dark:bg-gray-700/50",
        sizeClasses[size],
        className,
      )}
      value={clampedValue}
      aria-label={label}
      aria-valuenow={clampedValue}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <ProgressPrimitive.Indicator
        className={cn(
          "h-full transition-all duration-300 ease-out rounded-full",
          colorClasses[color],
          glowClasses[color],
        )}
        style={{ width: `${clampedValue}%` }}
      />
    </ProgressPrimitive.Root>
  );
}

export { ProgressPrimitive };
export type { ProgressProps, ProgressSize, ProgressColor };
