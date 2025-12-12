/**
 * Progress Primitive Tests
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "../../../testing/test-utils";
import { Progress } from "../progress";

describe("Progress", () => {
  it("renders with default props", () => {
    render(<Progress value={50} />);

    const progressBar = screen.getByRole("progressbar");
    expect(progressBar).toBeInTheDocument();
  });

  it("has correct accessibility attributes", () => {
    render(<Progress value={75} label="Loading progress" />);

    const progressBar = screen.getByRole("progressbar");
    expect(progressBar).toHaveAttribute("aria-valuenow", "75");
    expect(progressBar).toHaveAttribute("aria-valuemin", "0");
    expect(progressBar).toHaveAttribute("aria-valuemax", "100");
    expect(progressBar).toHaveAttribute("aria-label", "Loading progress");
  });

  it("clamps value between 0 and 100", () => {
    const { rerender } = render(<Progress value={-10} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");

    rerender(<Progress value={150} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  describe("size variants", () => {
    it("renders sm size with correct class", () => {
      const { container } = render(<Progress value={50} size="sm" />);
      const root = container.querySelector("[role='progressbar']");
      expect(root).toHaveClass("h-1");
    });

    it("renders md size with correct class (default)", () => {
      const { container } = render(<Progress value={50} />);
      const root = container.querySelector("[role='progressbar']");
      expect(root).toHaveClass("h-2");
    });

    it("renders lg size with correct class", () => {
      const { container } = render(<Progress value={50} size="lg" />);
      const root = container.querySelector("[role='progressbar']");
      expect(root).toHaveClass("h-3");
    });
  });

  describe("color variants", () => {
    it("renders cyan color with correct class (default)", () => {
      const { container } = render(<Progress value={50} />);
      const progressBar = container.querySelector("[role='progressbar']");
      const indicator = progressBar?.querySelector("[data-state]");
      expect(indicator).toHaveClass("bg-cyan-500");
    });

    it("renders green color with correct class", () => {
      const { container } = render(<Progress value={50} color="green" />);
      const progressBar = container.querySelector("[role='progressbar']");
      const indicator = progressBar?.querySelector("[data-state]");
      expect(indicator).toHaveClass("bg-green-500");
    });

    it("renders orange color with correct class", () => {
      const { container } = render(<Progress value={50} color="orange" />);
      const progressBar = container.querySelector("[role='progressbar']");
      const indicator = progressBar?.querySelector("[data-state]");
      expect(indicator).toHaveClass("bg-orange-500");
    });

    it("renders red color with correct class", () => {
      const { container } = render(<Progress value={50} color="red" />);
      const progressBar = container.querySelector("[role='progressbar']");
      const indicator = progressBar?.querySelector("[data-state]");
      expect(indicator).toHaveClass("bg-red-500");
    });

    it("renders purple color with correct class", () => {
      const { container } = render(<Progress value={50} color="purple" />);
      const progressBar = container.querySelector("[role='progressbar']");
      const indicator = progressBar?.querySelector("[data-state]");
      expect(indicator).toHaveClass("bg-purple-500");
    });

    it("renders blue color with correct class", () => {
      const { container } = render(<Progress value={50} color="blue" />);
      const progressBar = container.querySelector("[role='progressbar']");
      const indicator = progressBar?.querySelector("[data-state]");
      expect(indicator).toHaveClass("bg-blue-500");
    });
  });

  it("applies custom className", () => {
    const { container } = render(<Progress value={50} className="custom-class" />);
    const root = container.querySelector("[role='progressbar']");
    expect(root).toHaveClass("custom-class");
  });

  it("sets indicator width based on value", () => {
    const { container } = render(<Progress value={33} />);
    const progressBar = container.querySelector("[role='progressbar']");
    const indicator = progressBar?.querySelector("[data-state]");
    expect(indicator).toHaveStyle({ width: "33%" });
  });
});
