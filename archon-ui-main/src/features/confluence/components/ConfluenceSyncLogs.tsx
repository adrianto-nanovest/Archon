/**
 * Confluence Sync Logs Component
 * Expandable log section showing recent sync log entries
 */

import { useEffect, useRef, useState } from "react";
import { Collapsible } from "../../ui/primitives/collapsible";
import { cn } from "../../ui/primitives/styles";

interface ConfluenceSyncLogsProps {
  /** Array of log entries */
  logs: string[];
  /** Max number of logs to display */
  maxLogs?: number;
  /** Optional className */
  className?: string;
  /** Default open state */
  defaultOpen?: boolean;
}

export const ConfluenceSyncLogs: React.FC<ConfluenceSyncLogsProps> = ({
  logs,
  maxLogs = 10,
  className,
  defaultOpen = false,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Display the most recent logs (last N entries)
  const displayLogs = logs.slice(-maxLogs);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs.length, isOpen]);

  if (logs.length === 0) return null;

  return (
    <div className={className}>
      <Collapsible
        open={isOpen}
        onOpenChange={setIsOpen}
        trigger={`Show logs (${logs.length} ${logs.length === 1 ? "entry" : "entries"})`}
        triggerClassName="text-gray-500 dark:text-gray-400 hover:text-cyan-500 dark:hover:text-cyan-400"
        contentClassName="mt-2"
      >
        <div
          ref={scrollRef}
          className={cn(
            "rounded-md p-3 max-h-48 overflow-y-auto",
            "bg-gray-100 dark:bg-gray-800/50",
            "border border-gray-200/50 dark:border-gray-700/50",
            "font-mono text-xs leading-relaxed",
            "scrollbar-thin",
          )}
        >
          {displayLogs.map((log, index) => {
            // Extract timestamp if present (format: HH:MM:SS - message)
            const timestampMatch = log.match(/^(\d{2}:\d{2}:\d{2})\s*-?\s*/);
            const timestamp = timestampMatch ? timestampMatch[1] : null;
            const message = timestamp && timestampMatch ? log.slice(timestampMatch[0].length) : log;

            return (
              <div key={`log-${index}-${log.slice(0, 20)}`} className="py-0.5 text-gray-600 dark:text-gray-400">
                {timestamp && <span className="text-gray-400 dark:text-gray-500 mr-2">{timestamp}</span>}
                <span>{message}</span>
              </div>
            );
          })}
        </div>
      </Collapsible>
    </div>
  );
};

export type { ConfluenceSyncLogsProps };
