#!/usr/bin/env python3
"""
Search Performance Benchmark Script (Story 4.3)

Executes 100 search queries with various filter combinations and measures:
- P95 latency (target: <500ms)
- Average latency (target: <300ms)
- Memory usage delta (target: <20% increase)

This script validates Integration Verification requirements:
- IV1: 95th percentile search latency <500ms with 4000+ Confluence pages indexed
- IV3: Memory usage during search remains within 20% baseline increase

Usage:
    cd python
    uv run python -m scripts.benchmark_search_performance

    # With custom number of queries
    uv run python -m scripts.benchmark_search_performance --queries 200

    # Verbose mode (show each query timing)
    uv run python -m scripts.benchmark_search_performance --verbose

    # Target a specific space key
    uv run python -m scripts.benchmark_search_performance --space-key DEVDOCS

Requirements:
    - Supabase database with indexed content
    - Valid API key for embeddings (set in .env or via Settings API)
"""

import argparse
import asyncio
import statistics
import sys
import time
import tracemalloc
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])


# Benchmark query configurations with various filter combinations
BENCHMARK_QUERIES: list[dict[str, Any]] = [
    # Basic searches (no filters) - most common pattern
    {"query": "API documentation", "filters": None},
    {"query": "error handling", "filters": None},
    {"query": "configuration settings", "filters": None},
    {"query": "authentication", "filters": None},
    {"query": "database connection", "filters": None},
    {"query": "REST endpoints", "filters": None},
    {"query": "deployment guide", "filters": None},
    {"query": "troubleshooting", "filters": None},
    {"query": "installation", "filters": None},
    {"query": "getting started", "filters": None},
    # Space filter searches (Story 4.2)
    {"query": "deployment guide", "filters": {"space_key": "DEVDOCS"}},
    {"query": "architecture overview", "filters": {"space_key": "INTERNAL"}},
    {"query": "API reference", "filters": {"space_key": "DEVDOCS"}},
    {"query": "security policy", "filters": {"space_key": "INTERNAL"}},
    # JIRA filter searches
    {"query": "bug fix", "filters": {"jira_issue": "PROJ-123"}},
    {"query": "feature implementation", "filters": {"jira_issue": "PROJ-456"}},
    {"query": "performance improvement", "filters": {"jira_issue": "PROJ-789"}},
    # Combined filters (space + jira)
    {"query": "setup instructions", "filters": {"space_key": "DEVDOCS", "jira_issue": "PROJ-456"}},
    {"query": "migration guide", "filters": {"space_key": "INTERNAL", "jira_issue": "PROJ-123"}},
    # Hierarchy filter (path prefix matching)
    {"query": "getting started", "filters": {"hierarchy_path": "/parent123/"}},
    {"query": "advanced topics", "filters": {"hierarchy_path": "/docs/"}},
    # User mention filter
    {"query": "review comments", "filters": {"mentioned_user": "user123"}},
    # Complex combinations
    {"query": "integration guide", "filters": {"space_key": "DEVDOCS", "hierarchy_path": "/guides/"}},
    {"query": "code examples", "filters": {"space_key": "INTERNAL", "mentioned_user": "user456"}},
    # Long queries (stress test)
    {
        "query": "How do I configure the database connection settings for production deployment with SSL enabled",
        "filters": None,
    },
    {
        "query": "What are the best practices for error handling in REST API endpoints with authentication",
        "filters": {"space_key": "DEVDOCS"},
    },
]


class BenchmarkResults:
    """Container for benchmark results with analysis methods."""

    def __init__(self) -> None:
        self.latencies: list[float] = []
        self.baseline_memory: int = 0
        self.peak_memory: int = 0
        self.query_count: int = 0
        self.error_count: int = 0
        self.errors: list[str] = []

    @property
    def p95_latency(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latencies:
            return 0.0
        # statistics.quantiles returns n-1 cut points, so for 95th percentile we use n=20
        # and take the 19th element (0-indexed: 18)
        quantiles = statistics.quantiles(self.latencies, n=20)
        return quantiles[18] if len(quantiles) > 18 else self.latencies[-1]

    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def min_latency(self) -> float:
        """Calculate minimum latency."""
        return min(self.latencies) if self.latencies else 0.0

    @property
    def max_latency(self) -> float:
        """Calculate maximum latency."""
        return max(self.latencies) if self.latencies else 0.0

    @property
    def memory_delta_percent(self) -> float:
        """Calculate memory usage delta as percentage."""
        if self.baseline_memory == 0:
            return 0.0
        return ((self.peak_memory - self.baseline_memory) / self.baseline_memory) * 100

    def print_report(self) -> None:
        """Print formatted benchmark report."""
        print("\n" + "=" * 60)
        print("SEARCH PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)

        print(f"\nQueries Executed: {self.query_count}")
        print(f"Errors: {self.error_count}")

        print("\n--- Latency Metrics ---")
        p95_pass = self.p95_latency < 500
        avg_pass = self.avg_latency < 300

        print(f"P95 Latency:     {self.p95_latency:.2f}ms (target: <500ms) {'PASS' if p95_pass else 'FAIL'}")
        print(f"Avg Latency:     {self.avg_latency:.2f}ms (target: <300ms) {'PASS' if avg_pass else 'FAIL'}")
        print(f"Min Latency:     {self.min_latency:.2f}ms")
        print(f"Max Latency:     {self.max_latency:.2f}ms")

        print("\n--- Memory Metrics ---")
        mem_pass = self.memory_delta_percent < 20

        print(f"Baseline Memory: {self.baseline_memory / 1024 / 1024:.2f} MB")
        print(f"Peak Memory:     {self.peak_memory / 1024 / 1024:.2f} MB")
        print(f"Memory Delta:    {self.memory_delta_percent:.1f}% (target: <20%) {'PASS' if mem_pass else 'FAIL'}")

        print("\n--- Overall Result ---")
        all_pass = p95_pass and avg_pass and mem_pass
        print(f"Status: {'ALL TARGETS MET' if all_pass else 'TARGETS NOT MET'}")

        if self.errors:
            print("\n--- Errors ---")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more errors")

        print("=" * 60)


async def execute_search(
    rag_service: Any,
    query: str,
    filters: dict[str, str] | None,
) -> dict[str, Any]:
    """Execute a single search query using RAGService."""
    from src.server.services.search.hybrid_search_strategy import ConfluenceSearchFilters

    # Build Confluence filters if any are specified
    confluence_filters = None
    if filters:
        confluence_filters = ConfluenceSearchFilters(
            space_key=filters.get("space_key"),
            jira_issue=filters.get("jira_issue"),
            hierarchy_path=filters.get("hierarchy_path"),
            mentioned_user=filters.get("mentioned_user"),
        )

    # Perform search
    success, result = await rag_service.perform_rag_query(
        query=query,
        source=None,
        match_count=10,  # Standard match count
        return_mode="chunks",
        confluence_filters=confluence_filters,
    )

    return {"success": success, "result": result}


async def run_benchmark(
    num_queries: int = 100,
    verbose: bool = False,
    space_key: str | None = None,
) -> BenchmarkResults:
    """Execute benchmark suite and return results."""
    # Import here to avoid import errors when showing help
    from src.server.services.search.rag_service import RAGService
    from src.server.utils import get_supabase_client

    results = BenchmarkResults()

    # Initialize services
    print("Initializing services...")
    supabase = get_supabase_client()
    rag_service = RAGService(supabase)

    # Start memory tracking
    tracemalloc.start()
    results.baseline_memory = tracemalloc.get_traced_memory()[0]

    print(f"Running {num_queries} search queries...")
    print("-" * 40)

    # Apply space_key override if specified
    queries = BENCHMARK_QUERIES.copy()
    if space_key:
        for q in queries:
            if q["filters"]:
                q["filters"]["space_key"] = space_key
            else:
                q["filters"] = {"space_key": space_key}

    # Run queries
    for i in range(num_queries):
        query_config = queries[i % len(queries)]
        query = query_config["query"]
        filters = query_config["filters"]

        try:
            start_time = time.perf_counter()
            await execute_search(rag_service, query, filters)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            results.latencies.append(elapsed_ms)
            results.query_count += 1

            if verbose:
                filter_str = str(filters) if filters else "none"
                print(f"  [{i + 1:3d}] {elapsed_ms:7.2f}ms - {query[:40]}... (filters: {filter_str[:30]})")

            # Update peak memory
            current_memory = tracemalloc.get_traced_memory()[0]
            results.peak_memory = max(results.peak_memory, current_memory)

        except Exception as e:
            results.error_count += 1
            results.errors.append(f"Query {i + 1}: {str(e)}")
            if verbose:
                print(f"  [{i + 1:3d}] ERROR - {str(e)[:50]}")

        # Progress indicator
        if not verbose and (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{num_queries} queries completed")

    tracemalloc.stop()

    return results


def main() -> None:
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description="Search Performance Benchmark Script (Story 4.3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run default 100 queries
    uv run python -m scripts.benchmark_search_performance

    # Run with verbose output
    uv run python -m scripts.benchmark_search_performance --verbose

    # Run 200 queries targeting a specific space
    uv run python -m scripts.benchmark_search_performance --queries 200 --space-key DEVDOCS

Targets:
    - P95 Latency: <500ms
    - Average Latency: <300ms
    - Memory Delta: <20%
        """,
    )

    parser.add_argument(
        "--queries",
        "-n",
        type=int,
        default=100,
        help="Number of queries to execute (default: 100)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show timing for each query",
    )
    parser.add_argument(
        "--space-key",
        "-s",
        type=str,
        default=None,
        help="Override space_key filter for all queries",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Search Performance Benchmark (Story 4.3)")
    print("=" * 60)
    print("Configuration:")
    print(f"  Queries: {args.queries}")
    print(f"  Verbose: {args.verbose}")
    print(f"  Space Key Override: {args.space_key or 'none'}")
    print()

    # Run benchmark
    results = asyncio.run(
        run_benchmark(
            num_queries=args.queries,
            verbose=args.verbose,
            space_key=args.space_key,
        )
    )

    # Print results
    results.print_report()

    # Exit with appropriate code
    p95_pass = results.p95_latency < 500
    avg_pass = results.avg_latency < 300
    mem_pass = results.memory_delta_percent < 20

    sys.exit(0 if (p95_pass and avg_pass and mem_pass) else 1)


if __name__ == "__main__":
    main()
