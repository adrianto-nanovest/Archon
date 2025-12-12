/**
 * Confluence Sync Status Component
 * Displays sync progress with real-time updates using existing progress infrastructure
 */

import { AlertCircle, CheckCircle2, Clock, Loader2, RefreshCw } from "lucide-react";
import { useMemo } from "react";
import type { ProgressResponse, ProgressStatus } from "../../progress/types";
import { Button } from "../../ui/primitives/button";
import { Progress } from "../../ui/primitives/progress";
import { cn } from "../../ui/primitives/styles";

type SyncState = "idle" | "syncing" | "completed" | "error";

interface ConfluenceSyncStatusProps {
  /** Progress data from useOperationProgress */
  progressData: ProgressResponse | null;
  /** Whether the operation is currently loading */
  isLoading?: boolean;
  /** Whether the operation is in a terminal state */
  isComplete?: boolean;
  /** Whether the operation failed */
  isFailed?: boolean;
  /** Callback to retry sync */
  onRetry?: () => void;
  /** Optional className */
  className?: string;
}

const stateStyles: Record<SyncState, { badge: string; label: string }> = {
  idle: {
    badge: "bg-gray-100 text-gray-700 dark:bg-gray-500/10 dark:text-gray-400",
    label: "Idle",
  },
  syncing: {
    badge: "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400",
    label: "Syncing",
  },
  completed: {
    badge: "bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400",
    label: "Complete",
  },
  error: {
    badge: "bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400",
    label: "Error",
  },
};

const StateIcon: React.FC<{ state: SyncState; className?: string }> = ({ state, className }) => {
  switch (state) {
    case "syncing":
      return <Loader2 className={cn("animate-spin", className)} />;
    case "completed":
      return <CheckCircle2 className={className} />;
    case "error":
      return <AlertCircle className={className} />;
    default:
      return <Clock className={className} />;
  }
};

function getSyncState(status: ProgressStatus | undefined, isComplete?: boolean, isFailed?: boolean): SyncState {
  if (isFailed) return "error";
  if (isComplete) return "completed";
  if (!status) return "idle";

  const terminalStates: ProgressStatus[] = ["completed", "error", "failed", "cancelled"];
  if (terminalStates.includes(status)) {
    return status === "completed" ? "completed" : "error";
  }

  return "syncing";
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
}

function estimateTimeRemaining(
  processedPages: number | undefined,
  totalPages: number | undefined,
  startTime: string | undefined,
): string | null {
  if (!processedPages || !totalPages || !startTime || processedPages === 0) return null;

  const elapsed = (Date.now() - new Date(startTime).getTime()) / 1000;
  const pagesPerSecond = processedPages / elapsed;
  const remainingPages = totalPages - processedPages;
  const remainingSeconds = remainingPages / pagesPerSecond;

  if (remainingSeconds < 5) return "Almost done";
  return `~${formatDuration(remainingSeconds)} remaining`;
}

export const ConfluenceSyncStatusDisplay: React.FC<ConfluenceSyncStatusProps> = ({
  progressData,
  isLoading,
  isComplete,
  isFailed,
  onRetry,
  className,
}) => {
  const state = getSyncState(progressData?.status, isComplete, isFailed);
  const styleConfig = stateStyles[state];

  const progress = progressData?.progress ?? 0;
  const processedPages = progressData?.processedPages ?? progressData?.stats?.pages_crawled;
  const totalPages = progressData?.totalPages ?? progressData?.stats?.documents_created;
  const message = progressData?.message || progressData?.current_step;
  const error = progressData?.error || progressData?.error_message;

  const timeRemaining = useMemo(() => {
    if (state !== "syncing") return null;
    return estimateTimeRemaining(processedPages, totalPages, progressData?.startedAt);
  }, [state, processedPages, totalPages, progressData?.startedAt]);

  // Render completed state
  if (state === "completed") {
    const stats = progressData?.stats;
    return (
      <div className={cn("rounded-lg border border-green-500/30 bg-green-500/5 p-3", className)}>
        <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
          <CheckCircle2 className="w-4 h-4" />
          <span className="text-sm font-medium">Sync Complete</span>
        </div>
        {stats && (
          <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
            {stats.pages_crawled ?? 0} pages synced
            {stats.documents_created ? ` \u00b7 ${stats.documents_created} documents` : ""}
            {stats.errors ? ` \u00b7 ${stats.errors} errors` : ""}
          </p>
        )}
      </div>
    );
  }

  // Render error state
  if (state === "error") {
    return (
      <div className={cn("rounded-lg border border-red-500/30 bg-red-500/5 p-3", className)}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm font-medium">Sync Failed</span>
          </div>
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry} className="h-7 px-2 text-xs">
              <RefreshCw className="w-3 h-3 mr-1" />
              Retry
            </Button>
          )}
        </div>
        {error && <p className="mt-1 text-xs text-red-600/80 dark:text-red-400/80">{error}</p>}
      </div>
    );
  }

  // Render syncing state
  if (state === "syncing" || isLoading) {
    return (
      <div className={cn("rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-3", className)}>
        <div className="flex items-center gap-2 mb-2">
          <div className={cn("flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium", styleConfig.badge)}>
            <StateIcon state="syncing" className="w-3 h-3" />
            <span>{styleConfig.label}</span>
          </div>
          {message && <span className="text-xs text-gray-500 dark:text-gray-400 truncate">{message}</span>}
        </div>

        <Progress value={progress} size="md" color="cyan" label="Sync progress" className="mb-2" />

        <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
          <span>
            {processedPages !== undefined && totalPages !== undefined
              ? `Processing ${processedPages} of ${totalPages} pages`
              : `${Math.round(progress)}% complete`}
          </span>
          {timeRemaining && <span>{timeRemaining}</span>}
        </div>
      </div>
    );
  }

  // Render idle state (no sync in progress)
  return null;
};

export type { ConfluenceSyncStatusProps, SyncState };
