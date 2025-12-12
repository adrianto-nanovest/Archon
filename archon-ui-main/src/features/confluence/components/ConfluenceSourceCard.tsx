/**
 * Confluence Source Card Component
 * Displays a Confluence source with status, sync info, and actions
 */

import { format } from "date-fns";
import { motion } from "framer-motion";
import { Clock, ExternalLink, Eye, FileText, Folder } from "lucide-react";
import { useCallback, useState } from "react";
import { useToast } from "@/features/shared/hooks";
import { isOptimistic } from "@/features/shared/utils/optimistic";
import { Button, StatPill } from "../../ui/primitives";
import { DataCard, DataCardContent, DataCardFooter, DataCardHeader } from "../../ui/primitives/data-card";
import { OptimisticIndicator } from "../../ui/primitives/OptimisticIndicator";
import { cn } from "../../ui/primitives/styles";
import { SimpleTooltip } from "../../ui/primitives/tooltip";
import { useConfluenceSyncProgress } from "../hooks/useConfluenceSyncProgress";
import type { ConfluenceSource } from "../types";
import { ConfluenceSourceActions } from "./ConfluenceSourceActions";
import { ConfluenceSyncLogs } from "./ConfluenceSyncLogs";
import { ConfluenceSyncStatusDisplay } from "./ConfluenceSyncStatusDisplay";
import { ConfluenceSyncStatusModal } from "./ConfluenceSyncStatusModal";

interface ConfluenceSourceCardProps {
  source: ConfluenceSource;
  onDeleteSuccess: () => void;
  onSyncStarted?: (operationId: string) => void;
}

// Static status badge styles
const statusBadgeStyles = {
  ready: "bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400",
  syncing: "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400 animate-pulse",
  error: "bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400",
  idle: "bg-gray-100 text-gray-700 dark:bg-gray-500/10 dark:text-gray-400",
} as const;

export const ConfluenceSourceCard: React.FC<ConfluenceSourceCardProps> = ({
  source,
  onDeleteSuccess,
  onSyncStarted,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [activeOperationId, setActiveOperationId] = useState<string | null>(null);
  const [showProgressModal, setShowProgressModal] = useState(false);
  const { showToast } = useToast();

  // Track sync progress
  const {
    data: progressData,
    isLoading: isProgressLoading,
    isComplete,
    isFailed,
    isActive,
  } = useConfluenceSyncProgress(activeOperationId, {
    onComplete: () => {
      showToast("Confluence sync completed successfully", "success");
      setActiveOperationId(null);
    },
    onError: (error) => {
      showToast(`Sync failed: ${error}`, "error");
      setActiveOperationId(null);
    },
  });

  // Handle sync started from actions menu
  const handleSyncStarted = useCallback(
    (operationId: string) => {
      setActiveOperationId(operationId);
      onSyncStarted?.(operationId);
    },
    [onSyncStarted],
  );

  // Handle retry after failure
  const handleRetry = useCallback(() => {
    setActiveOperationId(null);
  }, []);

  const optimistic = isOptimistic(source);
  const status = (source.status || "idle") as keyof typeof statusBadgeStyles;
  const isSyncing = status === "syncing" || isActive;

  // Truncate base URL for display
  const displayUrl = source.base_url.replace(/^https?:\/\//, "").replace(/\/wiki\/?$/, "");

  const getEdgeColor = (): "cyan" | "orange" | "red" => {
    if (isSyncing) return "orange";
    if (status === "error") return "red";
    return "cyan";
  };

  return (
    <motion.div
      className={cn("relative group", optimistic && "opacity-80")}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      <DataCard
        edgePosition="top"
        edgeColor={getEdgeColor()}
        blur="md"
        className={cn(
          "transition-shadow",
          isHovered && "shadow-[0_0_30px_rgba(6,182,212,0.2)]",
          optimistic && "ring-1 ring-cyan-400/30",
        )}
      >
        <DataCardHeader>
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <SimpleTooltip content={`Confluence Space: ${source.space_key}`}>
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium bg-cyan-100 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400">
                  <Folder className="w-4 h-4" />
                  <span>{source.space_key}</span>
                </div>
              </SimpleTooltip>

              <div className={cn("px-2 py-1 rounded-md text-xs font-medium", statusBadgeStyles[status])}>
                {status === "syncing" ? "Syncing..." : status.charAt(0).toUpperCase() + status.slice(1)}
              </div>
            </div>

            <div
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") e.stopPropagation();
              }}
              role="none"
            >
              <ConfluenceSourceActions
                sourceId={source.source_id}
                spaceName={source.space_key}
                isSyncing={isSyncing}
                onDeleteSuccess={onDeleteSuccess}
                onSyncStarted={handleSyncStarted}
              />
            </div>
          </div>

          <div className="mb-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90 line-clamp-1">
              {source.space_key} Space
            </h3>
            <OptimisticIndicator isOptimistic={optimistic} className="mt-2" />
          </div>

          <SimpleTooltip content={source.base_url}>
            <a
              href={source.base_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors mt-1"
            >
              <ExternalLink className="w-3 h-3" />
              <span className="truncate max-w-[200px]">{displayUrl}</span>
            </a>
          </SimpleTooltip>
        </DataCardHeader>

        <DataCardContent>
          {/* Sync progress display when active */}
          {(isActive || isFailed || isComplete) && activeOperationId && (
            <div className="mt-3">
              <ConfluenceSyncStatusDisplay
                progressData={progressData ?? null}
                isLoading={isProgressLoading}
                isComplete={isComplete}
                isFailed={isFailed}
                onRetry={handleRetry}
              />
              {/* Expandable logs section */}
              {progressData?.logs && progressData.logs.length > 0 && (
                <ConfluenceSyncLogs logs={progressData.logs} className="mt-2" />
              )}
              {/* View Details button */}
              <div className="mt-2 flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowProgressModal(true);
                  }}
                  className="h-7 px-2 text-xs text-gray-500 hover:text-cyan-400"
                >
                  <Eye className="w-3 h-3 mr-1" />
                  View Details
                </Button>
              </div>
            </div>
          )}

          {/* Last sync info when not actively syncing */}
          {!isActive && !isFailed && source.last_sync && (
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mt-2">
              <Clock className="w-3 h-3" />
              <span>Last sync: {format(new Date(source.last_sync), "MMM d, yyyy HH:mm")}</span>
            </div>
          )}
        </DataCardContent>

        <DataCardFooter>
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span>Created: {format(new Date(source.created_at), "M/d/yyyy")}</span>
            </div>
            <div className="flex items-center gap-2">
              <SimpleTooltip content={`${source.total_pages} page${source.total_pages !== 1 ? "s" : ""} synced`}>
                <div>
                  <StatPill
                    color="cyan"
                    value={source.total_pages}
                    size="sm"
                    aria-label="Pages count"
                    icon={<FileText className="w-3.5 h-3.5" />}
                  />
                </div>
              </SimpleTooltip>
            </div>
          </div>
        </DataCardFooter>
      </DataCard>

      {/* Progress details modal */}
      <ConfluenceSyncStatusModal
        open={showProgressModal}
        onOpenChange={setShowProgressModal}
        spaceName={source.space_key}
        progressData={progressData ?? null}
        isLoading={isProgressLoading}
        isComplete={isComplete}
        isFailed={isFailed}
        onRetry={handleRetry}
        onClose={() => setShowProgressModal(false)}
      />
    </motion.div>
  );
};
