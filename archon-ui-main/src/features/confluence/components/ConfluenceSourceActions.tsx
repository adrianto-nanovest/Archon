/**
 * Confluence Source Actions Component
 * Dropdown menu with sync and delete actions
 */

import { MoreHorizontal, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "../../ui/primitives/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../ui/primitives/dropdown-menu";
import { cn } from "../../ui/primitives/styles";
import { useDeleteSource, useTriggerSync } from "../hooks/useConfluenceQueries";
import { DeleteConfluenceSourceDialog } from "./DeleteConfluenceSourceDialog";

interface ConfluenceSourceActionsProps {
  sourceId: string;
  spaceName: string;
  isSyncing: boolean;
  onDeleteSuccess: () => void;
  onSyncStarted?: (operationId: string) => void;
}

export const ConfluenceSourceActions: React.FC<ConfluenceSourceActionsProps> = ({
  sourceId,
  spaceName,
  isSyncing,
  onDeleteSuccess,
  onSyncStarted,
}) => {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const syncMutation = useTriggerSync();
  const deleteMutation = useDeleteSource();

  const handleSync = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isSyncing || syncMutation.isPending) return;

    const result = await syncMutation.mutateAsync(sourceId);
    if (result?.operation_id && onSyncStarted) {
      onSyncStarted(result.operation_id);
    }
  };

  const handleDelete = async () => {
    await deleteMutation.mutateAsync(sourceId);
    setShowDeleteDialog(false);
    onDeleteSuccess();
  };

  const isDeleting = deleteMutation.isPending;
  const isSyncingNow = syncMutation.isPending || isSyncing;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className={cn("h-8 w-8 p-0 text-gray-400 hover:text-white hover:bg-white/10", "opacity-100")}
            disabled={isDeleting}
            title="More actions"
          >
            {isSyncingNow ? <RefreshCw className="w-4 h-4 animate-spin" /> : <MoreHorizontal className="w-4 h-4" />}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuItem onClick={handleSync} disabled={isSyncingNow}>
            <RefreshCw className={cn("w-4 h-4 mr-2", isSyncingNow && "animate-spin")} />
            {isSyncingNow ? "Syncing..." : "Sync Now"}
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              setShowDeleteDialog(true);
            }}
            disabled={isDeleting}
            className="text-red-400 focus:text-red-400"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            {isDeleting ? "Deleting..." : "Delete"}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <DeleteConfluenceSourceDialog
        spaceName={spaceName}
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={handleDelete}
        isDeleting={isDeleting}
      />
    </>
  );
};
