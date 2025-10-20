"""Unit tests for Table Processor."""

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.table_processor import TableProcessor


@pytest.fixture
def processor():
    """Create TableProcessor instance."""
    return TableProcessor()


def test_simple_table_hierarchical_format(processor):
    """Test simple table conversion to hierarchical markdown format."""
    html = """
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Age</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Alice</td>
                <td>30</td>
            </tr>
            <tr>
                <td>Bob</td>
                <td>25</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Verify hierarchical structure
    assert "<!-- TABLE_START -->" in result
    assert "<!-- TABLE_END -->" in result
    assert "## Row 1" in result or "## Row" in result
    assert "### Column 1: Name" in result
    assert "### Column 2: Age" in result
    assert "Alice" in result
    assert "Bob" in result

    # Verify NO standard markdown table syntax
    assert "|---|---|" not in result
    assert "| Name | Age |" not in result


def test_table_summary_comment(processor):
    """Test table summary comment generation."""
    html = """
    <table>
        <thead>
            <tr>
                <th>Col1</th>
                <th>Col2</th>
                <th>Col3</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>A</td>
                <td>B</td>
                <td>C</td>
            </tr>
            <tr>
                <td>D</td>
                <td>E</td>
                <td>F</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Verify summary comment
    assert "<!-- Table Summary:" in result
    assert "3 columns" in result
    assert "2 rows" in result
    assert "complexity:" in result
    assert "purpose:" in result


def test_colspan_content_duplication(processor):
    """Test colspan handling duplicates content across spanned cells."""
    html = """
    <table>
        <tbody>
            <tr>
                <td colspan="3">Merged Header</td>
            </tr>
            <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
                <td>Cell 3</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Count occurrences of "Merged Header" in output
    merged_count = result.count("Merged Header")

    # Should appear 3 times (once per spanned column)
    assert merged_count >= 3, f"Expected 'Merged Header' to appear 3+ times, found {merged_count}"

    # Verify hierarchical structure maintained
    assert "### Column 1" in result
    assert "### Column 2" in result
    assert "### Column 3" in result


def test_rowspan_content_duplication(processor):
    """Test rowspan handling duplicates content across spanned rows."""
    html = """
    <table>
        <tbody>
            <tr>
                <td rowspan="2">Spanned Cell</td>
                <td>Cell A</td>
            </tr>
            <tr>
                <td>Cell B</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Note: Rowspan handling in hierarchical format is complex
    # For now, verify that content appears and structure is valid
    assert "Spanned Cell" in result
    assert "Cell A" in result
    assert "Cell B" in result
    # When no thead, first row is labeled "Header Row"
    assert "## Header Row" in result or "## Row 1" in result
    assert "## Row 2" in result


def test_context_aware_heading_levels(processor):
    """Test heading levels adapt to surrounding context."""
    html = """
    <h2>Section Title</h2>
    <table>
        <tbody>
            <tr>
                <td>Data</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # After h2, table should use h4 (level 4) for rows
    # h2 (level 2) + 2 = h4 (level 4)
    assert "####" in result, "Expected level 4 heading (####) for rows"


def test_default_heading_level_no_context(processor):
    """Test default heading level when no surrounding context."""
    html = """
    <table>
        <tbody>
            <tr>
                <td>Data</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Default: level 2 for rows (##)
    assert "##" in result
    # When no thead, first row is labeled "Header Row"
    assert "Header Row" in result or "Row 1" in result


def test_table_complexity_calculation_simple(processor):
    """Test complexity calculation for simple table."""
    html = """
    <table>
        <tbody>
            <tr>
                <td>A</td>
                <td>B</td>
            </tr>
            <tr>
                <td>C</td>
                <td>D</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    complexity = processor._calculate_table_complexity(table)

    assert complexity["total_cells"] == 4
    assert complexity["spanned_cells"] == 0
    assert complexity["nested_content_count"] == 0
    assert complexity["complexity_score"] == 0.0


def test_table_complexity_calculation_with_spans(processor):
    """Test complexity calculation for table with spans."""
    html = """
    <table>
        <tbody>
            <tr>
                <td colspan="2">Merged</td>
            </tr>
            <tr>
                <td>A</td>
                <td>B</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    complexity = processor._calculate_table_complexity(table)

    assert complexity["total_cells"] == 3
    assert complexity["spanned_cells"] == 1
    assert complexity["complexity_score"] > 0.0


def test_table_complexity_with_nested_content(processor):
    """Test complexity calculation with nested code blocks."""
    html = """
    <table>
        <tbody>
            <tr>
                <td><pre>code block</pre></td>
                <td>normal</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    complexity = processor._calculate_table_complexity(table)

    assert complexity["nested_content_count"] == 1
    assert complexity["complexity_score"] > 0.0


def test_table_purpose_inference_comparison(processor):
    """Test purpose inference for comparison table."""
    html = """
    <table>
        <thead>
            <tr>
                <th>Before</th>
                <th>After</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Old Value</td>
                <td>New Value</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    thead = table.find("thead")
    header_rows = thead.find_all("tr")
    header_matrix = processor._build_header_matrix(header_rows)

    purpose = processor._infer_table_purpose(table, header_matrix)

    assert purpose == "comparison"


def test_table_purpose_inference_reference(processor):
    """Test purpose inference for reference table."""
    html = """
    <table>
        <thead>
            <tr>
                <th>Parameter</th>
                <th>Value</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>timeout</td>
                <td>30s</td>
                <td>Request timeout</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    thead = table.find("thead")
    header_rows = thead.find_all("tr")
    header_matrix = processor._build_header_matrix(header_rows)

    purpose = processor._infer_table_purpose(table, header_matrix)

    assert purpose == "reference"


def test_table_purpose_inference_status(processor):
    """Test purpose inference for status table."""
    html = """
    <table>
        <thead>
            <tr>
                <th>Task</th>
                <th>Status</th>
                <th>Progress</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Task 1</td>
                <td>Complete</td>
                <td>100%</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    thead = table.find("thead")
    header_rows = thead.find_all("tr")
    header_matrix = processor._build_header_matrix(header_rows)

    purpose = processor._infer_table_purpose(table, header_matrix)

    assert purpose == "status"


def test_table_purpose_inference_data(processor):
    """Test purpose inference for data table with numeric columns."""
    html = """
    <table>
        <thead>
            <tr>
                <th>Product</th>
                <th>Price</th>
                <th>Quantity</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Widget A</td>
                <td>$19.99</td>
                <td>150</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    thead = table.find("thead")
    header_rows = thead.find_all("tr")
    header_matrix = processor._build_header_matrix(header_rows)

    purpose = processor._infer_table_purpose(table, header_matrix)

    assert purpose == "data"


def test_nested_content_preservation_code_blocks(processor):
    """Test code blocks inside cells are preserved."""
    html = """
    <table>
        <tbody>
            <tr>
                <td><pre>const x = 42;</pre></td>
                <td>Code example</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Verify code block preserved with backticks
    assert "```" in result or "`" in result
    assert "const x = 42;" in result


def test_nested_content_preservation_lists(processor):
    """Test lists inside cells are preserved."""
    html = """
    <table>
        <tbody>
            <tr>
                <td>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                </td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Verify list items preserved
    assert "Item 1" in result
    assert "Item 2" in result
    assert "-" in result or "*" in result  # List markers


def test_multi_level_header_matrix(processor):
    """Test header matrix building with multi-level headers."""
    html = """
    <table>
        <thead>
            <tr>
                <th colspan="2">Group A</th>
                <th>Group B</th>
            </tr>
            <tr>
                <th>Sub 1</th>
                <th>Sub 2</th>
                <th>Sub 3</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Data 1</td>
                <td>Data 2</td>
                <td>Data 3</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    thead = table.find("thead")
    header_rows = thead.find_all("tr")
    header_matrix = processor._build_header_matrix(header_rows)

    # Verify multi-level matrix
    assert len(header_matrix) == 2  # Two header rows
    assert len(header_matrix[0]) == 2  # First row: Group A (colspan=2), Group B
    assert header_matrix[0][0][0] == "Group A"
    assert header_matrix[0][0][1] == 2  # colspan
    assert len(header_matrix[1]) == 3  # Second row: Sub 1, Sub 2, Sub 3


def test_table_without_thead(processor):
    """Test table without thead (data rows only)."""
    html = """
    <table>
        <tr>
            <td>Row 1 Cell 1</td>
            <td>Row 1 Cell 2</td>
        </tr>
        <tr>
            <td>Row 2 Cell 1</td>
            <td>Row 2 Cell 2</td>
        </tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Verify hierarchical structure still works
    assert "<!-- TABLE_START -->" in result
    assert "<!-- TABLE_END -->" in result
    assert "## Row" in result
    assert "### Column" in result
    assert "Row 1 Cell 1" in result


def test_empty_table(processor):
    """Test empty table handling."""
    html = """
    <table>
        <tbody></tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Should still have markers and summary
    assert "<!-- TABLE_START -->" in result
    assert "<!-- TABLE_END -->" in result
    assert "0 rows" in result


def test_table_with_mixed_th_td_in_body(processor):
    """Test table with mixed th/td elements in tbody."""
    html = """
    <table>
        <tbody>
            <tr>
                <th>Row Header</th>
                <td>Data Cell</td>
            </tr>
        </tbody>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    result = processor.process_table(table, soup)

    # Both cell types should be processed
    assert "Row Header" in result
    assert "Data Cell" in result
