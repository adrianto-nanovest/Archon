/**
 * SearchFilters Component Tests
 * Story 5.4: Enhance Search UI with Confluence Filters
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "../../../testing/test-utils";
import type { SearchFiltersState } from "../../types";
import { SearchFilters } from "../SearchFilters";

// Default filters for testing
const defaultFilters: SearchFiltersState = {
  sourceType: "all",
  spaceKeys: [],
  hasJiraLinks: false,
};

const mockAvailableSpaces = ["DEVDOCS", "TECHOPS", "PLATFORM"];

describe("SearchFilters", () => {
  const mockOnFiltersChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders filter header", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByText("Filters")).toBeInTheDocument();
    expect(screen.getByText("Source Type")).toBeInTheDocument();
  });

  it("renders source type toggle group with all options", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByRole("group", { name: /filter by source type/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /all sources/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /web sources/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /uploaded documents/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /confluence/i })).toBeInTheDocument();
  });

  it("calls onFiltersChange when source type changes", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    const confluenceOption = screen.getByRole("radio", { name: /confluence/i });
    fireEvent.click(confluenceOption);

    expect(mockOnFiltersChange).toHaveBeenCalledWith({
      ...defaultFilters,
      sourceType: "confluence",
    });
  });

  it("shows Confluence space selector when sourceType is all", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByText("Confluence Spaces")).toBeInTheDocument();
    expect(screen.getByText("DEVDOCS")).toBeInTheDocument();
    expect(screen.getByText("TECHOPS")).toBeInTheDocument();
    expect(screen.getByText("PLATFORM")).toBeInTheDocument();
  });

  it("shows Confluence space selector when sourceType is confluence", () => {
    render(
      <SearchFilters
        filters={{ ...defaultFilters, sourceType: "confluence" }}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByText("Confluence Spaces")).toBeInTheDocument();
  });

  it("hides Confluence filters when sourceType is web", () => {
    render(
      <SearchFilters
        filters={{ ...defaultFilters, sourceType: "web" }}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.queryByText("Confluence Spaces")).not.toBeInTheDocument();
    expect(screen.queryByText("Has JIRA Links")).not.toBeInTheDocument();
  });

  it("hides Confluence filters when sourceType is upload", () => {
    render(
      <SearchFilters
        filters={{ ...defaultFilters, sourceType: "upload" }}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.queryByText("Confluence Spaces")).not.toBeInTheDocument();
    expect(screen.queryByText("Has JIRA Links")).not.toBeInTheDocument();
  });

  it("calls onFiltersChange when space checkbox is toggled", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    const devdocsCheckbox = screen.getByRole("checkbox", { name: /select space devdocs/i });
    fireEvent.click(devdocsCheckbox);

    expect(mockOnFiltersChange).toHaveBeenCalledWith({
      ...defaultFilters,
      spaceKeys: ["DEVDOCS"],
    });
  });

  it("removes space from selection when unchecked", () => {
    const filtersWithSpace: SearchFiltersState = {
      ...defaultFilters,
      spaceKeys: ["DEVDOCS"],
    };

    render(
      <SearchFilters
        filters={filtersWithSpace}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    const devdocsCheckbox = screen.getByRole("checkbox", { name: /select space devdocs/i });
    fireEvent.click(devdocsCheckbox);

    expect(mockOnFiltersChange).toHaveBeenCalledWith({
      ...defaultFilters,
      spaceKeys: [],
    });
  });

  it("shows Clear button when spaces are selected", () => {
    const filtersWithSpaces: SearchFiltersState = {
      ...defaultFilters,
      spaceKeys: ["DEVDOCS", "TECHOPS"],
    };

    render(
      <SearchFilters
        filters={filtersWithSpaces}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByRole("button", { name: /clear space selection/i })).toBeInTheDocument();
  });

  it("clears all spaces when Clear button is clicked", () => {
    const filtersWithSpaces: SearchFiltersState = {
      ...defaultFilters,
      spaceKeys: ["DEVDOCS", "TECHOPS"],
    };

    render(
      <SearchFilters
        filters={filtersWithSpaces}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    const clearButton = screen.getByRole("button", { name: /clear space selection/i });
    fireEvent.click(clearButton);

    expect(mockOnFiltersChange).toHaveBeenCalledWith({
      ...defaultFilters,
      spaceKeys: [],
    });
  });

  it("shows All button when not all spaces are selected", () => {
    const filtersWithOneSpace: SearchFiltersState = {
      ...defaultFilters,
      spaceKeys: ["DEVDOCS"],
    };

    render(
      <SearchFilters
        filters={filtersWithOneSpace}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByRole("button", { name: /select all spaces/i })).toBeInTheDocument();
  });

  it("selects all spaces when All button is clicked", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    const allButton = screen.getByRole("button", { name: /select all spaces/i });
    fireEvent.click(allButton);

    expect(mockOnFiltersChange).toHaveBeenCalledWith({
      ...defaultFilters,
      spaceKeys: mockAvailableSpaces,
    });
  });

  it("shows JIRA links toggle", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByText("Has JIRA Links")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /filter results with jira links/i })).toBeInTheDocument();
  });

  it("calls onFiltersChange when JIRA toggle is clicked", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    const jiraToggle = screen.getByRole("switch", { name: /filter results with jira links/i });
    fireEvent.click(jiraToggle);

    expect(mockOnFiltersChange).toHaveBeenCalledWith({
      ...defaultFilters,
      hasJiraLinks: true,
    });
  });

  it("shows active filters summary when filters are active", () => {
    const activeFilters: SearchFiltersState = {
      sourceType: "confluence",
      spaceKeys: ["DEVDOCS"],
      hasJiraLinks: true,
    };

    render(
      <SearchFilters
        filters={activeFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByText("Active filters:")).toBeInTheDocument();
    expect(screen.getByText("confluence")).toBeInTheDocument();
    expect(screen.getByText("1 space")).toBeInTheDocument();
    expect(screen.getByText("JIRA")).toBeInTheDocument();
  });

  it("hides active filters summary when no filters are active", () => {
    render(
      <SearchFilters
        filters={defaultFilters}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.queryByText("Active filters:")).not.toBeInTheDocument();
  });

  it("shows space count in selection summary", () => {
    const filtersWithSpaces: SearchFiltersState = {
      ...defaultFilters,
      spaceKeys: ["DEVDOCS", "TECHOPS"],
    };

    render(
      <SearchFilters
        filters={filtersWithSpaces}
        onFiltersChange={mockOnFiltersChange}
        availableSpaces={mockAvailableSpaces}
      />,
    );

    expect(screen.getByText("2 spaces selected")).toBeInTheDocument();
  });

  it("hides space selector when no spaces available", () => {
    render(<SearchFilters filters={defaultFilters} onFiltersChange={mockOnFiltersChange} availableSpaces={[]} />);

    expect(screen.queryByText("Confluence Spaces")).not.toBeInTheDocument();
  });
});
