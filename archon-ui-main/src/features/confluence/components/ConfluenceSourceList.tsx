/**
 * Confluence Source List Component
 * Displays a grid of Confluence source cards with loading and empty states
 */

import { MessageSquare, Plus } from "lucide-react";
import { Button } from "../../ui/primitives/button";
import { cn } from "../../ui/primitives/styles";
import { useConfluenceSources } from "../hooks/useConfluenceQueries";
import { ConfluenceSourceCard } from "./ConfluenceSourceCard";

interface ConfluenceSourceListProps {
  onAddSource: () => void;
  onSyncStarted?: (operationId: string) => void;
}

export const ConfluenceSourceList: React.FC<ConfluenceSourceListProps> = ({ onAddSource, onSyncStarted }) => {
  const { data, isLoading, error, refetch } = useConfluenceSources();

  const sources = data?.sources || [];
  const hasNoSources = sources.length === 0 && !isLoading;

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className={cn(
              "h-[240px] rounded-lg",
              "bg-white/5 dark:bg-white/[0.02]",
              "border border-gray-200/20 dark:border-white/10",
              "animate-pulse",
            )}
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="text-red-500 dark:text-red-400 mb-4">Failed to load Confluence sources</div>
        <Button variant="outline" onClick={() => refetch()}>
          Try Again
        </Button>
      </div>
    );
  }

  if (hasNoSources) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 rounded-full bg-cyan-500/10 flex items-center justify-center mb-4">
          <Plus className="w-8 h-8 text-cyan-500" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90 mb-2">No Confluence sources yet</h3>
        <p className="text-gray-600 dark:text-gray-400 max-w-sm mb-6">
          Connect your Confluence spaces to search their content alongside your other knowledge sources.
        </p>
        <Button
          onClick={onAddSource}
          className={cn(
            "bg-gradient-to-r from-cyan-500 to-cyan-600",
            "hover:from-cyan-600 hover:to-cyan-700",
            "shadow-[0_0_20px_rgba(6,182,212,0.25)]",
          )}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Confluence Source
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <a
          href="https://github.com/coleam00/Archon/issues/new?template=feature_request.md&title=[Confluence]%20Feedback"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button
            variant="outline"
            className={cn(
              "border-gray-300/60 dark:border-gray-600/60",
              "hover:border-cyan-400/50 hover:text-cyan-600 dark:hover:text-cyan-400",
            )}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Give Feedback
          </Button>
        </a>
        <Button
          onClick={onAddSource}
          className={cn(
            "bg-gradient-to-r from-cyan-500 to-cyan-600",
            "hover:from-cyan-600 hover:to-cyan-700",
            "shadow-[0_0_15px_rgba(6,182,212,0.2)]",
          )}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Source
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sources.map((source) => (
          <ConfluenceSourceCard
            key={source.source_id}
            source={source}
            onDeleteSuccess={() => refetch()}
            onSyncStarted={onSyncStarted}
          />
        ))}
      </div>
    </div>
  );
};
