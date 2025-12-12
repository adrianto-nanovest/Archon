/**
 * ChangelogModal Component Tests
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "../../../testing/test-utils";
import { ChangelogModal } from "../ChangelogModal";

describe("ChangelogModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders modal when open", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} />);

    expect(screen.getByRole("heading", { name: /What's New in v0.2.0/i })).toBeInTheDocument();
    // "Confluence Cloud Integration" appears as headline and feature title - check at least one exists
    expect(screen.getAllByText("Confluence Cloud Integration").length).toBeGreaterThan(0);
  });

  it("does not render modal when closed", () => {
    render(<ChangelogModal open={false} onOpenChange={() => {}} />);

    expect(screen.queryByRole("heading", { name: /What's New/i })).not.toBeInTheDocument();
  });

  it("displays changelog features", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} />);

    // Check for key features - use getAllByText for items that appear multiple times
    expect(screen.getAllByText("Confluence Cloud Integration").length).toBeGreaterThan(0);
    expect(screen.getByText("Incremental Smart Sync")).toBeInTheDocument();
    expect(screen.getByText("Advanced Search with Metadata")).toBeInTheDocument();
  });

  it("displays improvements list", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} />);

    expect(screen.getByText(/Multi-LLM Provider Support/i)).toBeInTheDocument();
    expect(screen.getByText(/Migration Tracking System/i)).toBeInTheDocument();
  });

  it("calls onOpenChange when dismiss button is clicked", async () => {
    const onOpenChange = vi.fn();
    render(<ChangelogModal open={true} onOpenChange={onOpenChange} />);

    const dismissButton = screen.getByRole("button", { name: /Got it, thanks!/i });
    fireEvent.click(dismissButton);

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("calls onOpenChange when close button is clicked", async () => {
    const onOpenChange = vi.fn();
    render(<ChangelogModal open={true} onOpenChange={onOpenChange} />);

    // The close button is the X in the dialog header
    const closeButton = screen.getByRole("button", { name: /Close/i });
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("contains documentation link", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} />);

    const link = screen.getByText("View full documentation");
    expect(link).toHaveAttribute(
      "href",
      "https://github.com/coleam00/Archon/blob/main/docs/bmad/confluence-user-communication-plan.md",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("displays headline feature section", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} />);

    // Check for headline feature box
    expect(
      screen.getByText("The headline feature of this release brings powerful documentation integration."),
    ).toBeInTheDocument();
  });

  it("renders correctly with custom version", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} version="0.2.0" />);

    expect(screen.getByRole("heading", { name: /What's New in v0.2.0/i })).toBeInTheDocument();
  });

  it("renders key features section heading", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} />);

    expect(screen.getByText("Key Features")).toBeInTheDocument();
  });

  it("renders improvements section heading", () => {
    render(<ChangelogModal open={true} onOpenChange={() => {}} />);

    expect(screen.getByText("Improvements")).toBeInTheDocument();
  });
});
