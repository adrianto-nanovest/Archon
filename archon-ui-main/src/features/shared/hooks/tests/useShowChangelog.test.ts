/**
 * useShowChangelog Hook Tests
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useShowChangelog } from "../useShowChangelog";

// Mock useCurrentVersion hook
const mockUseCurrentVersion = vi.fn();

vi.mock("@/features/settings/version/hooks/useVersionQueries", () => ({
  useCurrentVersion: () => mockUseCurrentVersion(),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

describe("useShowChangelog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    // Default to version 0.2.0
    mockUseCurrentVersion.mockReturnValue({ data: { version: "0.2.0" } });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should return shouldShow=true when version is 0.2.0 and not dismissed", () => {
    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(true);
    expect(result.current.version).toBe("0.2.0");
    expect(result.current.isDismissed).toBe(false);
  });

  it("should return shouldShow=false when changelog has been dismissed", () => {
    // Pre-set localStorage to indicate dismissed
    localStorageMock.getItem.mockReturnValue("true");

    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(false);
    expect(result.current.isDismissed).toBe(true);
  });

  it("should return shouldShow=false when version is below 0.2.0", () => {
    mockUseCurrentVersion.mockReturnValue({ data: { version: "0.1.0" } });

    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(false);
    expect(result.current.version).toBe("0.1.0");
  });

  it("should return shouldShow=true for versions 0.2.0 and above", () => {
    const versions = ["0.2.0", "0.2.1", "0.3.0", "1.0.0"];

    versions.forEach((version) => {
      localStorageMock.clear();
      localStorageMock.getItem.mockReturnValue(null);
      mockUseCurrentVersion.mockReturnValue({ data: { version } });

      const { result } = renderHook(() => useShowChangelog());

      expect(result.current.shouldShow).toBe(true);
      expect(result.current.version).toBe(version);
    });
  });

  it("should dismiss changelog when dismiss is called", () => {
    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(true);

    act(() => {
      result.current.dismiss();
    });

    expect(result.current.shouldShow).toBe(false);
    expect(result.current.isDismissed).toBe(true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith("archon-changelog-dismissed-v0.2.0", "true");
  });

  it("should show changelog when show is called", () => {
    // Pre-dismiss the changelog
    localStorageMock.getItem.mockReturnValue("true");

    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(false);

    act(() => {
      result.current.show();
    });

    expect(result.current.shouldShow).toBe(true);
  });

  it("should return undefined version when version data is not available", () => {
    mockUseCurrentVersion.mockReturnValue({ data: undefined });

    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.version).toBeUndefined();
    expect(result.current.shouldShow).toBe(false);
  });

  it("should use version-specific localStorage key", () => {
    mockUseCurrentVersion.mockReturnValue({ data: { version: "0.3.0" } });

    const { result } = renderHook(() => useShowChangelog());

    act(() => {
      result.current.dismiss();
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith("archon-changelog-dismissed-v0.3.0", "true");
  });

  it("should not show changelog for version 0.1.x", () => {
    mockUseCurrentVersion.mockReturnValue({ data: { version: "0.1.5" } });

    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(false);
  });

  it("should show changelog for major version 1.x.x", () => {
    // Reset localStorage mock to return null (not dismissed)
    localStorageMock.clear();
    localStorageMock.getItem.mockReturnValue(null);
    mockUseCurrentVersion.mockReturnValue({ data: { version: "1.0.0" } });

    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(true);
  });

  it("should handle version data loading gracefully", () => {
    mockUseCurrentVersion.mockReturnValue({ data: null });

    const { result } = renderHook(() => useShowChangelog());

    expect(result.current.shouldShow).toBe(false);
    expect(result.current.version).toBeUndefined();
    expect(result.current.isDismissed).toBe(true);
  });
});
