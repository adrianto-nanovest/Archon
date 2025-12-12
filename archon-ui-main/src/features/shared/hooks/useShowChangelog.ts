/**
 * Hook for managing changelog modal visibility
 * Shows changelog on first visit after upgrade to a new version
 */

import { useCallback, useEffect, useState } from "react";
import { useCurrentVersion } from "@/features/settings/version/hooks/useVersionQueries";

const CHANGELOG_DISMISSED_KEY_PREFIX = "archon-changelog-dismissed-v";

/**
 * Get the localStorage key for a specific version
 */
function getStorageKey(version: string): string {
  return `${CHANGELOG_DISMISSED_KEY_PREFIX}${version}`;
}

/**
 * Check if changelog has been dismissed for a specific version
 */
function isChangelogDismissed(version: string): boolean {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(getStorageKey(version)) === "true";
}

/**
 * Mark changelog as dismissed for a specific version
 */
function dismissChangelog(version: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(getStorageKey(version), "true");
}

interface UseShowChangelogResult {
  /** Whether the changelog modal should be shown */
  shouldShow: boolean;
  /** Current version string */
  version: string | undefined;
  /** Function to dismiss the changelog */
  dismiss: () => void;
  /** Function to manually show the changelog */
  show: () => void;
  /** Whether changelog has been dismissed for current version */
  isDismissed: boolean;
}

/**
 * Hook to manage changelog modal visibility
 *
 * Shows the changelog modal when:
 * 1. Current version is 0.2.0 or higher
 * 2. User hasn't dismissed it for this version
 *
 * @returns Object with shouldShow, version, dismiss, show, and isDismissed
 */
export function useShowChangelog(): UseShowChangelogResult {
  const { data: versionData } = useCurrentVersion();
  const version = versionData?.version;

  const [shouldShow, setShouldShow] = useState(false);
  const [isDismissed, setIsDismissed] = useState(true);

  // Check if we should show changelog on mount or version change
  useEffect(() => {
    if (!version) return;

    // Only show for 0.2.0+ versions
    const [major, minor] = version.split(".").map(Number);
    const isRelevantVersion = major > 0 || (major === 0 && minor >= 2);

    if (!isRelevantVersion) {
      setShouldShow(false);
      setIsDismissed(true);
      return;
    }

    const dismissed = isChangelogDismissed(version);
    setIsDismissed(dismissed);
    setShouldShow(!dismissed);
  }, [version]);

  const dismiss = useCallback(() => {
    if (version) {
      dismissChangelog(version);
      setIsDismissed(true);
    }
    setShouldShow(false);
  }, [version]);

  const show = useCallback(() => {
    setShouldShow(true);
  }, []);

  return {
    shouldShow,
    version,
    dismiss,
    show,
    isDismissed,
  };
}
