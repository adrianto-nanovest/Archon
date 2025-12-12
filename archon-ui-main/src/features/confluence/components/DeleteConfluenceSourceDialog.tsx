/**
 * Delete Confluence Source Dialog
 * Confirmation dialog before deleting a Confluence source
 */

import { Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../../ui/primitives/alert-dialog";
import { Button } from "../../ui/primitives/button";

interface DeleteConfluenceSourceDialogProps {
  spaceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isDeleting: boolean;
}

export const DeleteConfluenceSourceDialog: React.FC<DeleteConfluenceSourceDialogProps> = ({
  spaceName,
  open,
  onOpenChange,
  onConfirm,
  isDeleting,
}) => {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent variant="destructive" className="max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <Trash2 className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <AlertDialogTitle className="text-lg">Delete Confluence Source?</AlertDialogTitle>
              <AlertDialogDescription className="text-sm">This action cannot be undone</AlertDialogDescription>
            </div>
          </div>
          <p className="text-gray-700 dark:text-gray-300 mt-2 mb-4">
            This will remove the <strong>{spaceName}</strong> space and all synced pages from your knowledge base. The
            original content in Confluence will not be affected.
          </p>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel asChild>
            <Button onClick={() => onOpenChange(false)} variant="outline" disabled={isDeleting}>
              Cancel
            </Button>
          </AlertDialogCancel>
          <AlertDialogAction asChild>
            <Button onClick={onConfirm} variant="destructive" disabled={isDeleting}>
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
