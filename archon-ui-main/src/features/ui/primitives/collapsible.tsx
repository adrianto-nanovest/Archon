/**
 * Collapsible primitive - Radix UI Collapsible with Tron-inspired styling
 *
 * Wraps @radix-ui/react-collapsible with chevron rotation animation
 * and consistent styling with our design system.
 */

import * as CollapsiblePrimitive from "@radix-ui/react-collapsible";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "./styles";

interface CollapsibleProps {
  /** Controlled open state */
  open?: boolean;
  /** Callback when open state changes */
  onOpenChange?: (open: boolean) => void;
  /** Content for the trigger button */
  trigger: ReactNode;
  /** Collapsible content */
  children: ReactNode;
  /** Optional className for the root element */
  className?: string;
  /** Optional className for the trigger button */
  triggerClassName?: string;
  /** Optional className for the content container */
  contentClassName?: string;
  /** Default open state (uncontrolled) */
  defaultOpen?: boolean;
}

export function Collapsible({
  open,
  onOpenChange,
  trigger,
  children,
  className,
  triggerClassName,
  contentClassName,
  defaultOpen,
}: CollapsibleProps) {
  return (
    <CollapsiblePrimitive.Root open={open} onOpenChange={onOpenChange} defaultOpen={defaultOpen} className={className}>
      <CollapsiblePrimitive.Trigger asChild>
        <button
          type="button"
          className={cn(
            "flex items-center gap-2 text-sm",
            "text-gray-600 dark:text-gray-400",
            "hover:text-cyan-500 dark:hover:text-cyan-400",
            "transition-colors duration-200",
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 rounded",
            triggerClassName,
          )}
        >
          <ChevronRight
            className={cn("w-4 h-4 transition-transform duration-200", "data-[state=open]:rotate-90")}
            data-state={open ? "open" : "closed"}
          />
          {trigger}
        </button>
      </CollapsiblePrimitive.Trigger>
      <CollapsiblePrimitive.Content
        className={cn(
          "overflow-hidden",
          "data-[state=open]:animate-[accordion-down_200ms_ease-out]",
          "data-[state=closed]:animate-[accordion-up_200ms_ease-out]",
          contentClassName,
        )}
      >
        {children}
      </CollapsiblePrimitive.Content>
    </CollapsiblePrimitive.Root>
  );
}

export { CollapsiblePrimitive };
export type { CollapsibleProps };
