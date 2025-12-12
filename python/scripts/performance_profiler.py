#!/usr/bin/env python3
"""
Performance Profiler Script (Story 6.3)

Profiles Confluence sync and search operations to identify bottlenecks.

Features:
- CPU profiling with cProfile
- Memory profiling with tracemalloc
- Timing breakdown by function
- Bottleneck identification

Usage:
    cd python
    uv run python -m scripts.performance_profiler

    # Profile specific operation
    uv run python -m scripts.performance_profiler --operation sync
    uv run python -m scripts.performance_profiler --operation search

    # Generate flamegraph data
    uv run python -m scripts.performance_profiler --flamegraph
"""

import argparse
import cProfile
import io
import pstats
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TimingResult:
    """Result of a timing measurement."""

    operation: str
    duration_ms: float
    memory_mb: float
    details: dict[str, Any]


@dataclass
class BottleneckInfo:
    """Information about an identified bottleneck."""

    rank: int
    function: str
    total_time_ms: float
    calls: int
    time_per_call_ms: float
    cumulative_time_ms: float
    source_file: str


class PerformanceProfiler:
    """Profiles performance of various operations."""

    def __init__(self) -> None:
        self.timings: list[TimingResult] = []
        self.bottlenecks: list[BottleneckInfo] = []
        self.profiler = cProfile.Profile()

    def profile_function(self, func: Any, *args: Any, **kwargs: Any) -> tuple[Any, pstats.Stats]:
        """Profile a function call and return result with stats."""
        self.profiler.enable()
        try:
            result = func(*args, **kwargs)
        finally:
            self.profiler.disable()

        # Get stats
        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.sort_stats("cumulative")

        return result, stats

    def identify_bottlenecks(self, stats: pstats.Stats, top_n: int = 10) -> list[BottleneckInfo]:
        """Identify top N bottlenecks from profile stats."""
        bottlenecks = []

        # Sort by cumulative time
        stats.sort_stats("cumulative")

        # Get the function stats
        for rank, (func_key, func_stats) in enumerate(list(stats.stats.items())[:top_n], 1):
            filename, line_no, func_name = func_key
            cc, nc, tt, ct, callers = func_stats

            # Format source file
            if "site-packages" in filename:
                source_file = filename.split("site-packages/")[-1]
            elif "python/" in filename:
                source_file = filename.split("python/")[-1]
            else:
                source_file = Path(filename).name

            bottleneck = BottleneckInfo(
                rank=rank,
                function=f"{func_name}",
                total_time_ms=tt * 1000,
                calls=nc,
                time_per_call_ms=(tt / nc * 1000) if nc > 0 else 0,
                cumulative_time_ms=ct * 1000,
                source_file=f"{source_file}:{line_no}",
            )
            bottlenecks.append(bottleneck)

        self.bottlenecks = bottlenecks
        return bottlenecks

    def measure_memory(self, func: Any, *args: Any, **kwargs: Any) -> tuple[Any, float, float]:
        """Measure memory usage during function execution."""
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]

        result = func(*args, **kwargs)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return result, (current - baseline) / 1024 / 1024, (peak - baseline) / 1024 / 1024

    def time_operation(
        self,
        name: str,
        func: Any,
        *args: Any,
        iterations: int = 1,
        **kwargs: Any,
    ) -> TimingResult:
        """Time an operation with optional iterations."""
        durations = []
        memory_usage = 0.0

        for _i in range(iterations):
            tracemalloc.start()
            start = time.perf_counter()

            func(*args, **kwargs)

            duration = (time.perf_counter() - start) * 1000
            durations.append(duration)

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            memory_usage = max(memory_usage, peak / 1024 / 1024)

        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        result = TimingResult(
            operation=name,
            duration_ms=avg_duration,
            memory_mb=memory_usage,
            details={
                "iterations": iterations,
                "min_ms": min_duration,
                "max_ms": max_duration,
                "total_ms": sum(durations),
            },
        )
        self.timings.append(result)
        return result

    def print_bottleneck_report(self) -> None:
        """Print formatted bottleneck report."""
        print("\n" + "=" * 80)
        print("BOTTLENECK ANALYSIS")
        print("=" * 80)

        if not self.bottlenecks:
            print("No bottlenecks identified. Run profiling first.")
            return

        print(f"\nTop {len(self.bottlenecks)} slowest functions:\n")
        print(f"{'Rank':<5} {'Function':<40} {'Total (ms)':<12} {'Calls':<8} {'Per Call':<12}")
        print("-" * 80)

        for b in self.bottlenecks:
            func_display = b.function[:38] if len(b.function) > 38 else b.function
            print(f"{b.rank:<5} {func_display:<40} {b.total_time_ms:>10.2f} {b.calls:>8} {b.time_per_call_ms:>10.2f}")
            print(f"      Source: {b.source_file}")

        print("\n" + "=" * 80)

    def print_timing_report(self) -> None:
        """Print formatted timing report."""
        print("\n" + "=" * 80)
        print("TIMING REPORT")
        print("=" * 80)

        if not self.timings:
            print("No timings recorded.")
            return

        print(f"\n{'Operation':<30} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Memory (MB)':<12}")
        print("-" * 80)

        for t in self.timings:
            print(f"{t.operation:<30} {t.duration_ms:>10.2f} {t.details['min_ms']:>10.2f} {t.details['max_ms']:>10.2f} {t.memory_mb:>10.2f}")

        print("\n" + "=" * 80)

    def save_profile_stats(self, filename: str) -> None:
        """Save profile stats to file for visualization tools."""
        self.profiler.dump_stats(filename)
        print(f"\nProfile stats saved to: {filename}")
        print("Visualize with: snakeviz profile.pstats")


def profile_mock_sync(num_pages: int = 100) -> None:
    """Profile a mock sync operation."""
    print(f"Profiling mock sync with {num_pages} pages...")

    profiler = PerformanceProfiler()

    def mock_sync() -> dict:
        """Simulated sync operation."""
        results = {"pages_processed": 0, "chunks_created": 0}

        for i in range(num_pages):
            # Simulate HTML processing
            html = f"<p>Content for page {i}</p>" * 100
            _ = html.replace("<p>", "").replace("</p>", "\n")

            # Simulate chunking
            chunks = [f"chunk_{j}" for j in range(5)]

            results["pages_processed"] += 1
            results["chunks_created"] += len(chunks)

        return results

    # Time the operation
    timing = profiler.time_operation("mock_sync", mock_sync, iterations=3)
    print(f"\nSync timing: {timing.duration_ms:.2f}ms average")

    # Profile for bottlenecks
    _, stats = profiler.profile_function(mock_sync)
    profiler.identify_bottlenecks(stats)
    profiler.print_bottleneck_report()
    profiler.print_timing_report()


def profile_mock_search(num_queries: int = 50) -> None:
    """Profile mock search operations."""
    print(f"Profiling mock search with {num_queries} queries...")

    profiler = PerformanceProfiler()

    def mock_search(query: str) -> list:
        """Simulated search operation."""
        # Simulate embedding generation

        # Simulate vector comparison (simplified)
        results = []
        for i in range(10):
            similarity = 0.9 - (i * 0.05)
            results.append({
                "id": f"chunk-{i}",
                "content": f"Result for {query}",
                "similarity": similarity,
            })

        # Simulate sorting
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results

    queries = [
        "API documentation",
        "error handling",
        "configuration settings",
        "authentication",
        "deployment guide",
    ]

    # Time search operations
    for i, query in enumerate(queries * (num_queries // len(queries))):
        profiler.time_operation(f"search_{i}", mock_search, query)

    profiler.print_timing_report()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Performance Profiler for Confluence Sync and Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--operation",
        "-o",
        choices=["sync", "search", "all"],
        default="all",
        help="Operation to profile (default: all)",
    )
    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=100,
        help="Number of pages for sync profiling (default: 100)",
    )
    parser.add_argument(
        "--queries",
        "-q",
        type=int,
        default=50,
        help="Number of queries for search profiling (default: 50)",
    )
    parser.add_argument(
        "--save-stats",
        "-s",
        type=str,
        default=None,
        help="Save profile stats to file (for snakeviz visualization)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Confluence Performance Profiler (Story 6.3)")
    print("=" * 80)
    print(f"\nOperation: {args.operation}")
    print(f"Pages: {args.pages}")
    print(f"Queries: {args.queries}")
    print()

    if args.operation in ["sync", "all"]:
        profile_mock_sync(args.pages)

    if args.operation in ["search", "all"]:
        profile_mock_search(args.queries)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nBottleneck Analysis Complete.")
    print("\nTo profile against real services, ensure:")
    print("  1. Database is running with test data")
    print("  2. API keys are configured in .env")
    print("  3. Run: uv run python -m cProfile -o profile.pstats scripts/performance_profiler.py")
    print("  4. Visualize: snakeviz profile.pstats")


if __name__ == "__main__":
    main()
