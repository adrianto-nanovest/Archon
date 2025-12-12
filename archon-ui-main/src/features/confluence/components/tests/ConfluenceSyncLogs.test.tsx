/**
 * ConfluenceSyncLogs Component Tests
 * Story 6.2: Implement Frontend Component Tests
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "../../../testing/test-utils";
import { ConfluenceSyncLogs } from "../ConfluenceSyncLogs";

describe("ConfluenceSyncLogs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when logs array is empty", () => {
    render(<ConfluenceSyncLogs logs={[]} />);

    // The component returns null, so there should be no collapsible trigger
    expect(screen.queryByText(/Show logs/)).not.toBeInTheDocument();
  });

  it("renders collapsible trigger with log count", () => {
    const logs = ["Log entry 1", "Log entry 2", "Log entry 3"];
    render(<ConfluenceSyncLogs logs={logs} />);

    expect(screen.getByText("Show logs (3 entries)")).toBeInTheDocument();
  });

  it("shows singular 'entry' for single log", () => {
    render(<ConfluenceSyncLogs logs={["Single log"]} />);

    expect(screen.getByText("Show logs (1 entry)")).toBeInTheDocument();
  });

  it("is closed by default", () => {
    const logs = ["Log entry 1"];
    render(<ConfluenceSyncLogs logs={logs} />);

    // Content should not be visible
    expect(screen.queryByText("Log entry 1")).not.toBeInTheDocument();
  });

  it("can be opened by default with defaultOpen prop", () => {
    const logs = ["Log entry 1"];
    render(<ConfluenceSyncLogs logs={logs} defaultOpen={true} />);

    // Content should be visible
    expect(screen.getByText("Log entry 1")).toBeInTheDocument();
  });

  it("expands to show logs when trigger is clicked", () => {
    const logs = ["Log entry 1", "Log entry 2"];
    render(<ConfluenceSyncLogs logs={logs} />);

    // Initially closed
    expect(screen.queryByText("Log entry 1")).not.toBeInTheDocument();

    // Click to open
    fireEvent.click(screen.getByText("Show logs (2 entries)"));

    // Content should now be visible
    expect(screen.getByText("Log entry 1")).toBeInTheDocument();
    expect(screen.getByText("Log entry 2")).toBeInTheDocument();
  });

  it("limits displayed logs to maxLogs prop", () => {
    const logs = ["Log 1", "Log 2", "Log 3", "Log 4", "Log 5"];
    render(<ConfluenceSyncLogs logs={logs} maxLogs={3} defaultOpen={true} />);

    // Should only show last 3 logs
    expect(screen.queryByText("Log 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Log 2")).not.toBeInTheDocument();
    expect(screen.getByText("Log 3")).toBeInTheDocument();
    expect(screen.getByText("Log 4")).toBeInTheDocument();
    expect(screen.getByText("Log 5")).toBeInTheDocument();
  });

  it("extracts and displays timestamps from log entries", () => {
    const logs = ["10:30:45 - Processing page 1", "10:31:00 - Processing page 2"];
    render(<ConfluenceSyncLogs logs={logs} defaultOpen={true} />);

    // Timestamps should be rendered separately
    expect(screen.getByText("10:30:45")).toBeInTheDocument();
    expect(screen.getByText("10:31:00")).toBeInTheDocument();
    expect(screen.getByText("Processing page 1")).toBeInTheDocument();
    expect(screen.getByText("Processing page 2")).toBeInTheDocument();
  });

  it("handles logs without timestamps", () => {
    const logs = ["No timestamp log", "Another plain log"];
    render(<ConfluenceSyncLogs logs={logs} defaultOpen={true} />);

    expect(screen.getByText("No timestamp log")).toBeInTheDocument();
    expect(screen.getByText("Another plain log")).toBeInTheDocument();
  });

  it("handles mixed logs with and without timestamps", () => {
    const logs = ["12:00:00 - Timestamped entry", "Plain entry without timestamp"];
    render(<ConfluenceSyncLogs logs={logs} defaultOpen={true} />);

    expect(screen.getByText("12:00:00")).toBeInTheDocument();
    expect(screen.getByText("Timestamped entry")).toBeInTheDocument();
    expect(screen.getByText("Plain entry without timestamp")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const logs = ["Log entry"];
    const { container } = render(<ConfluenceSyncLogs logs={logs} className="custom-class" />);

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("defaults maxLogs to 10", () => {
    // Create 12 logs to verify only last 10 are shown
    const logs = Array.from({ length: 12 }, (_, i) => `Log ${i + 1}`);
    render(<ConfluenceSyncLogs logs={logs} defaultOpen={true} />);

    // First 2 logs should not be shown
    expect(screen.queryByText("Log 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Log 2")).not.toBeInTheDocument();

    // Logs 3-12 should be shown
    expect(screen.getByText("Log 3")).toBeInTheDocument();
    expect(screen.getByText("Log 12")).toBeInTheDocument();
  });

  it("toggles between open and closed states", () => {
    const logs = ["Toggle test log"];
    render(<ConfluenceSyncLogs logs={logs} />);

    const trigger = screen.getByText("Show logs (1 entry)");

    // Initially closed
    expect(screen.queryByText("Toggle test log")).not.toBeInTheDocument();

    // Open
    fireEvent.click(trigger);
    expect(screen.getByText("Toggle test log")).toBeInTheDocument();

    // Close again
    fireEvent.click(trigger);
    expect(screen.queryByText("Toggle test log")).not.toBeInTheDocument();
  });
});
