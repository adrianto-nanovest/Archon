/**
 * NewConfluenceSourceModal Component Tests
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "../../../testing/test-utils";
import { NewConfluenceSourceModal } from "../NewConfluenceSourceModal";

// Mock dependencies
const mockMutateAsync = vi.fn();

vi.mock("../../hooks/useConfluenceQueries", () => ({
  useCreateSource: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

describe("NewConfluenceSourceModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form fields correctly", () => {
    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    expect(screen.getByRole("heading", { name: "Add Confluence Source" })).toBeInTheDocument();
    expect(screen.getByText("Confluence Cloud URL")).toBeInTheDocument();
    expect(screen.getByText("Atlassian Email")).toBeInTheDocument();
    expect(screen.getByText("API Token")).toBeInTheDocument();
    expect(screen.getByText("Space Key")).toBeInTheDocument();
    expect(screen.getByText("Deletion Detection")).toBeInTheDocument();
  });

  it("shows validation errors for empty required fields", async () => {
    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    const submitButton = screen.getByText("Add Confluence Source", { selector: "button" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Confluence URL is required")).toBeInTheDocument();
      expect(screen.getByText("Email is required")).toBeInTheDocument();
      expect(screen.getByText("API token is required")).toBeInTheDocument();
      expect(screen.getByText("Space key is required")).toBeInTheDocument();
    });
  });

  it("validates URL must start with https://", async () => {
    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    const urlInput = screen.getByPlaceholderText("https://your-company.atlassian.net/wiki");
    fireEvent.change(urlInput, { target: { value: "http://company.atlassian.net/wiki" } });

    const submitButton = screen.getByText("Add Confluence Source", { selector: "button" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("URL must start with https://")).toBeInTheDocument();
    });
  });

  it("validates email format", async () => {
    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    const emailInput = screen.getByPlaceholderText("your-email@company.com");
    fireEvent.change(emailInput, { target: { value: "invalid-email" } });

    const urlInput = screen.getByPlaceholderText("https://your-company.atlassian.net/wiki");
    fireEvent.change(urlInput, { target: { value: "https://company.atlassian.net/wiki" } });

    const submitButton = screen.getByText("Add Confluence Source", { selector: "button" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Please enter a valid email address")).toBeInTheDocument();
    });
  });

  it("validates space key pattern (uppercase only)", async () => {
    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    const spaceKeyInput = screen.getByPlaceholderText("DEVDOCS");
    fireEvent.change(spaceKeyInput, { target: { value: "dev-docs" } });

    const urlInput = screen.getByPlaceholderText("https://your-company.atlassian.net/wiki");
    fireEvent.change(urlInput, { target: { value: "https://company.atlassian.net/wiki" } });

    const submitButton = screen.getByText("Add Confluence Source", { selector: "button" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Space key must be uppercase letters and numbers only")).toBeInTheDocument();
    });
  });

  it("auto-uppercases space key input", () => {
    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    const spaceKeyInput = screen.getByPlaceholderText("DEVDOCS") as HTMLInputElement;
    fireEvent.change(spaceKeyInput, { target: { value: "devdocs" } });

    expect(spaceKeyInput.value).toBe("DEVDOCS");
  });

  it("submits form with valid data", async () => {
    mockMutateAsync.mockResolvedValue({
      source_id: "new-source",
      space_key: "TESTSPACE",
    });

    const onSuccess = vi.fn();
    const onOpenChange = vi.fn();

    render(<NewConfluenceSourceModal open={true} onOpenChange={onOpenChange} onSuccess={onSuccess} />);

    // Fill in the form
    fireEvent.change(screen.getByPlaceholderText("https://your-company.atlassian.net/wiki"), {
      target: { value: "https://company.atlassian.net/wiki" },
    });
    fireEvent.change(screen.getByPlaceholderText("your-email@company.com"), {
      target: { value: "user@company.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter your Atlassian API token"), {
      target: { value: "valid-api-token-123" },
    });
    fireEvent.change(screen.getByPlaceholderText("DEVDOCS"), {
      target: { value: "TESTSPACE" },
    });

    const submitButton = screen.getByText("Add Confluence Source", { selector: "button" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        base_url: "https://company.atlassian.net/wiki",
        email: "user@company.com",
        api_token: "valid-api-token-123",
        space_key: "TESTSPACE",
        deletion_strategy: "weekly_reconciliation",
      });
      expect(onSuccess).toHaveBeenCalled();
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("shows token generation link", () => {
    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    const link = screen.getByText("Generate token at id.atlassian.com");
    expect(link).toHaveAttribute("href", "https://id.atlassian.com/manage-profile/security/api-tokens");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("handles submission error", async () => {
    const error = new Error("Failed to create source");
    mockMutateAsync.mockRejectedValue(error);

    render(<NewConfluenceSourceModal open={true} onOpenChange={() => {}} onSuccess={() => {}} />);

    // Fill in valid data
    fireEvent.change(screen.getByPlaceholderText("https://your-company.atlassian.net/wiki"), {
      target: { value: "https://company.atlassian.net/wiki" },
    });
    fireEvent.change(screen.getByPlaceholderText("your-email@company.com"), {
      target: { value: "user@company.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter your Atlassian API token"), {
      target: { value: "valid-api-token-123" },
    });
    fireEvent.change(screen.getByPlaceholderText("DEVDOCS"), {
      target: { value: "TESTSPACE" },
    });

    const submitButton = screen.getByText("Add Confluence Source", { selector: "button" });
    fireEvent.click(submitButton);

    // Error is handled by toast (through ToastProvider), just verify mutation was called
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalled();
    });
  });
});
