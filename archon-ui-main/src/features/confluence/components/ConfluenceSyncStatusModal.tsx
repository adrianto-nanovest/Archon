/**
 * Confluence Sync Status Modal
 * Full detail view of sync progress with complete log history
 */

import { format } from "date-fns";
import { AlertCircle, CheckCircle2, Clock, Loader2, RefreshCw, XCircle } from "lucide-react";
import { useEffect, useRef } from "react";
import type { ProgressResponse, ProgressStatus } from "../../progress/types";
import { Button } from "../../ui/primitives/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../ui/primitives/dialog";
import { Progress } from "../../ui/primitives/progress";
import { cn } from "../../ui/primitives/styles";

interface ConfluenceSyncStatusModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal open state changes */
  onOpenChange: (open: boolean) => void;
  /** Space name for display */
  spaceName: string;
  /** Progress data from useOperationProgress */
  progressData: ProgressResponse | null;
  /** Whether the operation is currently loading */
  isLoading?: boolean;
  /** Whether the operation is complete */
  isComplete?: boolean;
  /** Whether the operation failed */
  isFailed?: boolean;
  /** Callback to retry sync */
  onRetry?: () => void;
  /** Callback when modal closes */
  onClose?: () => void;
}

function getStatusInfo(status: ProgressStatus | undefined, isComplete?: boolean, isFailed?: boolean) {
  if (isFailed || status === "error" || status === "failed") {
    return {
      color: "text-red-500 dark:text-red-400",
      bgColor: "bg-red-500/10",
      icon: XCircle,
      label: "Failed",
    };
  }
  if (isComplete || status === "completed") {
    return {
      color: "text-green-500 dark:text-green-400",
      bgColor: "bg-green-500/10",
      icon: CheckCircle2,
      label: "Completed",
    };
  }
  if (status === "cancelled") {
    return {
      color: "text-yellow-500 dark:text-yellow-400",
      bgColor: "bg-yellow-500/10",
      icon: AlertCircle,
      label: "Cancelled",
    };
  }
  return {
    color: "text-cyan-500 dark:text-cyan-400",
    bgColor: "bg-cyan-500/10",
    icon: Loader2,
    label: "Syncing",
  };
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

export const ConfluenceSyncStatusModal: React.FC<ConfluenceSyncStatusModalProps> = ({
  open,
  onOpenChange,
  spaceName,
  progressData,
  isLoading: _isLoading,
  isComplete,
  isFailed,
  onRetry,
  onClose,
}) => {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const statusInfo = getStatusInfo(progressData?.status, isComplete, isFailed);
  const StatusIcon = statusInfo.icon;

  const progress = progressData?.progress ?? 0;
  const logs = progressData?.logs ?? [];
  const processedPages = progressData?.processedPages ?? progressData?.stats?.pages_crawled;
  const totalPages = progressData?.totalPages ?? progressData?.stats?.documents_created;
  const error = progressData?.error || progressData?.error_message;
  const startedAt = progressData?.startedAt;
  const stats = progressData?.stats;

  // Calculate elapsed time
  const elapsedSeconds = startedAt ? Math.round((Date.now() - new Date(startedAt).getTime()) / 1000) : undefined;

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs.length]);

  const handleClose = () => {
    onClose?.();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Sync Progress - {spaceName}</DialogTitle>
          <DialogDescription>
            {statusInfo.label === "Syncing"
              ? "Synchronizing pages from Confluence..."
              : `Sync ${statusInfo.label.toLowerCase()}`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Status badge */}
          <div className="flex items-center gap-3">
            <div className={cn("p-2 rounded-lg", statusInfo.bgColor)}>
              <StatusIcon
                className={cn("w-5 h-5", statusInfo.color, statusInfo.label === "Syncing" && "animate-spin")}
              />
            </div>
            <div>
              <div className={cn("font-medium", statusInfo.color)}>{statusInfo.label}</div>
              {progressData?.message && (
                <div className="text-sm text-gray-500 dark:text-gray-400">{progressData.message}</div>
              )}
            </div>
          </div>

          {/* Progress bar */}
          {!isFailed && !isComplete && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  {processedPages !== undefined && totalPages !== undefined
                    ? `${processedPages} of ${totalPages} pages`
                    : `${Math.round(progress)}% complete`}
                </span>
                {elapsedSeconds !== undefined && (
                  <span className="text-gray-500 dark:text-gray-500">Elapsed: {formatDuration(elapsedSeconds)}</span>
                )}
              </div>
              <Progress value={progress} size="lg" color="cyan" label="Sync progress" />
            </div>
          )}

          {/* Completion stats */}
          {isComplete && stats && (
            <div className="grid grid-cols-3 gap-4 p-4 rounded-lg bg-green-500/5 border border-green-500/20">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">{stats.pages_crawled ?? 0}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">Pages Synced</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-cyan-600 dark:text-cyan-400">
                  {stats.documents_created ?? 0}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">Documents</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                  {elapsedSeconds !== undefined ? formatDuration(elapsedSeconds) : "-"}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">Duration</div>
              </div>
            </div>
          )}

          {/* Error display */}
          {isFailed && error && (
            <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/20">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-red-600 dark:text-red-400">Sync Failed</div>
                  <div className="text-sm text-red-500/80 dark:text-red-400/80 mt-1">{error}</div>
                </div>
              </div>
            </div>
          )}

          {/* Logs section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Sync Logs</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">{logs.length} entries</span>
            </div>
            <div
              className={cn(
                "h-48 overflow-y-auto rounded-lg p-3",
                "bg-gray-100 dark:bg-gray-800/50",
                "border border-gray-200/50 dark:border-gray-700/50",
                "font-mono text-xs",
                "scrollbar-thin",
              )}
            >
              {logs.length === 0 ? (
                <div className="text-gray-400 dark:text-gray-500 italic">No logs yet...</div>
              ) : (
                <>
                  {logs.map((log, index) => {
                    const timestampMatch = log.match(/^(\d{2}:\d{2}:\d{2})\s*-?\s*/);
                    const timestamp = timestampMatch ? timestampMatch[1] : null;
                    const message = timestamp && timestampMatch ? log.slice(timestampMatch[0].length) : log;

                    return (
                      <div key={`log-${index}`} className="py-0.5 text-gray-600 dark:text-gray-400">
                        {timestamp && <span className="text-gray-400 dark:text-gray-500 mr-2">{timestamp}</span>}
                        <span>{message}</span>
                      </div>
                    );
                  })}
                  <div ref={logsEndRef} />
                </>
              )}
            </div>
          </div>

          {/* Timestamps */}
          {startedAt && (
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span>Started: {format(new Date(startedAt), "MMM d, yyyy 'at' HH:mm:ss")}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          {isFailed && onRetry && (
            <Button variant="outline" onClick={onRetry}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry Sync
            </Button>
          )}
          <Button variant={isFailed ? "ghost" : "cyan"} onClick={handleClose}>
            {isComplete || isFailed ? "Close" : "Minimize"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export type { ConfluenceSyncStatusModalProps };
