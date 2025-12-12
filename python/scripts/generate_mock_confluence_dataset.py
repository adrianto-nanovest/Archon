#!/usr/bin/env python3
"""
Mock Confluence Dataset Generator (Story 6.3)

Generates a realistic mock dataset of 4000 Confluence pages for load testing.

Features:
- 4000 pages with varying sizes (1KB-75KB content)
- 7-level hierarchy with realistic parent-child relationships
- Mock JIRA links (20% of pages), user mentions (30%), internal links (50%)
- Varying metadata richness (ancestors, labels, etc.)

Usage:
    cd python
    uv run python -m scripts.generate_mock_confluence_dataset

    # Custom options
    uv run python -m scripts.generate_mock_confluence_dataset --pages 1000 --output custom.json.gz
"""

import argparse
import gzip
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Realistic content templates
CONTENT_TEMPLATES = [
    """<h1>{title}</h1>
<p>This document provides comprehensive information about {topic}.</p>
<h2>Overview</h2>
<p>{overview_paragraph}</p>
<h2>Getting Started</h2>
<p>{getting_started}</p>
<h3>Prerequisites</h3>
<ul>
<li>Python 3.12 or later</li>
<li>Docker and Docker Compose</li>
<li>Access to the development environment</li>
</ul>
<h2>Configuration</h2>
<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">python</ac:parameter>
<ac:plain-text-body><![CDATA[
{code_sample}
]]></ac:plain-text-body>
</ac:structured-macro>
<h2>API Reference</h2>
<table>
<tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
<tr><td>/api/{endpoint}</td><td>GET</td><td>{api_desc}</td></tr>
</table>
{extra_content}""",
    """<h1>{title}</h1>
<ac:structured-macro ac:name="panel"><ac:parameter ac:name="type">info</ac:parameter>
<ac:rich-text-body><p>Last updated: {date}</p></ac:rich-text-body>
</ac:structured-macro>
<p>{intro_paragraph}</p>
<h2>Details</h2>
<p>{details}</p>
{extra_content}""",
    """<h1>{title}</h1>
<p>{summary}</p>
<h2>Implementation Guide</h2>
<p>{implementation_guide}</p>
<h3>Step 1: Setup</h3>
<p>{step1}</p>
<h3>Step 2: Configure</h3>
<p>{step2}</p>
<h3>Step 3: Deploy</h3>
<p>{step3}</p>
<h2>Troubleshooting</h2>
<table>
<tr><th>Error</th><th>Solution</th></tr>
<tr><td>Connection failed</td><td>Check network settings</td></tr>
<tr><td>Authentication error</td><td>Verify credentials</td></tr>
</table>
{extra_content}""",
]

# Sample topic words for generating realistic content
TOPIC_WORDS = [
    "authentication", "authorization", "API", "database", "deployment",
    "configuration", "monitoring", "logging", "caching", "security",
    "performance", "scalability", "integration", "testing", "documentation",
    "architecture", "microservices", "containers", "kubernetes", "CI/CD",
    "webhooks", "events", "messaging", "queues", "workers", "scheduler",
]

JIRA_PROJECTS = ["PROJ", "DEV", "OPS", "SEC", "DOC", "API", "SRE"]
USER_NAMES = [f"user{i:03d}" for i in range(1, 51)]


def generate_random_text(min_words: int, max_words: int) -> str:
    """Generate random realistic-looking text."""
    words = random.randint(min_words, max_words)
    word_pool = [
        "the", "a", "and", "or", "to", "from", "with", "for", "in", "on",
        "is", "are", "was", "were", "will", "can", "should", "must",
        "this", "that", "these", "those", "it", "they", "we", "you",
        "data", "system", "service", "application", "user", "request",
        "response", "configuration", "settings", "parameter", "value",
        "process", "workflow", "function", "method", "class", "module",
    ] + TOPIC_WORDS
    return " ".join(random.choices(word_pool, k=words)).capitalize() + "."


def generate_code_sample() -> str:
    """Generate a random code sample."""
    samples = [
        """def process_request(data: dict) -> Response:
    \"\"\"Process incoming request data.\"\"\"
    validated = validate_input(data)
    result = service.execute(validated)
    return Response(status=200, data=result)""",
        """class ConfigManager:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)

    def get(self, key: str, default=None):
        return self.config.get(key, default)""",
        """async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()""",
        """SETTINGS = {
    "database_url": os.getenv("DATABASE_URL"),
    "api_key": os.getenv("API_KEY"),
    "timeout": 30,
    "retry_count": 3,
}""",
    ]
    return random.choice(samples)


def generate_jira_link() -> str:
    """Generate a mock JIRA link."""
    project = random.choice(JIRA_PROJECTS)
    issue_num = random.randint(1, 9999)
    return f"{project}-{issue_num}"


def generate_user_mention() -> dict[str, str]:
    """Generate a mock user mention."""
    username = random.choice(USER_NAMES)
    return {
        "account_id": f"account-{username}-{random.randint(1000, 9999)}",
        "display_name": username.replace("user", "User "),
    }


def generate_page_content(title: str, target_size_kb: float) -> str:
    """Generate page content targeting a specific size in KB."""
    template = random.choice(CONTENT_TEMPLATES)
    topic = random.choice(TOPIC_WORDS)

    # Base content
    content = template.format(
        title=title,
        topic=topic,
        overview_paragraph=generate_random_text(50, 100),
        getting_started=generate_random_text(30, 60),
        code_sample=generate_code_sample(),
        endpoint=topic.lower(),
        api_desc=generate_random_text(10, 20),
        date=datetime.now().strftime("%Y-%m-%d"),
        intro_paragraph=generate_random_text(40, 80),
        details=generate_random_text(60, 120),
        summary=generate_random_text(20, 40),
        implementation_guide=generate_random_text(50, 100),
        step1=generate_random_text(30, 60),
        step2=generate_random_text(30, 60),
        step3=generate_random_text(30, 60),
        extra_content="",
    )

    # Add extra content to reach target size more efficiently
    current_size = len(content.encode("utf-8")) / 1024
    extra_parts = []
    while current_size < target_size_kb:
        # Generate larger chunks to be more efficient
        chunk_size = min(5, target_size_kb - current_size)
        words_needed = int(chunk_size * 150)  # ~150 words per KB
        extra_parts.append(f"<p>{generate_random_text(words_needed, words_needed + 50)}</p>")
        current_size += chunk_size

    content = content.replace("{extra_content}", "\n".join(extra_parts))
    return content


def generate_ancestors(page_id: str, hierarchy: dict[str, dict]) -> list[dict[str, Any]]:
    """Generate ancestors list for a page based on hierarchy."""
    ancestors = []
    current_id = page_id

    while current_id in hierarchy:
        parent_info = hierarchy[current_id]
        if parent_info["parent_id"] is None:
            break
        parent_id = parent_info["parent_id"]
        ancestors.insert(0, {
            "id": parent_id,
            "title": hierarchy.get(parent_id, {}).get("title", f"Page {parent_id}"),
        })
        current_id = parent_id

    return ancestors


def build_hierarchy(num_pages: int, max_depth: int = 7) -> dict[str, dict]:
    """Build a realistic page hierarchy with max_depth levels."""
    hierarchy: dict[str, dict] = {}

    # Create root pages (level 0) - about 5% of total
    num_roots = max(5, num_pages // 20)
    root_ids = [f"page-{i:05d}" for i in range(num_roots)]

    for i, page_id in enumerate(root_ids):
        hierarchy[page_id] = {
            "parent_id": None,
            "level": 0,
            "title": f"Root Section {i + 1}",
        }

    # Create remaining pages with hierarchical structure
    remaining_ids = [f"page-{i:05d}" for i in range(num_roots, num_pages)]

    # Group pages by target level (exponential distribution)
    for page_id in remaining_ids:
        # Bias towards shallower levels
        level = min(random.choices(
            range(1, max_depth + 1),
            weights=[max_depth - i for i in range(max_depth)],
        )[0], max_depth)

        # Find a parent at level-1
        potential_parents = [
            pid for pid, info in hierarchy.items()
            if info["level"] == level - 1
        ]

        if not potential_parents:
            # Fallback to any page at lower level
            potential_parents = [
                pid for pid, info in hierarchy.items()
                if info["level"] < level
            ]

        if potential_parents:
            parent_id = random.choice(potential_parents)
            parent_level = hierarchy[parent_id]["level"]
            actual_level = parent_level + 1
        else:
            parent_id = random.choice(root_ids)
            actual_level = 1

        hierarchy[page_id] = {
            "parent_id": parent_id,
            "level": actual_level,
            "title": f"Page at Level {actual_level}",
        }

    return hierarchy


def generate_mock_page(
    page_id: str,
    hierarchy: dict[str, dict],
    include_jira: bool,
    include_mentions: bool,
    include_links: bool,
) -> dict[str, Any]:
    """Generate a single mock Confluence page."""
    page_info = hierarchy.get(page_id, {"level": 0, "title": "Untitled"})
    level = page_info["level"]

    # Generate title
    title_prefix = random.choice([
        "Getting Started with", "Guide to", "Understanding",
        "How to", "Best Practices for", "Introduction to",
        "Advanced", "Configuring", "Troubleshooting", "Reference:",
    ])
    topic = random.choice(TOPIC_WORDS).title()
    title = f"{title_prefix} {topic}"
    if level > 0:
        title = f"{title} - Part {random.randint(1, 10)}"

    # Update hierarchy with actual title
    hierarchy[page_id]["title"] = title

    # Generate content with random size (1KB-75KB, weighted toward smaller)
    size_weights = [50, 30, 15, 4, 1]  # Favor smaller sizes
    size_ranges = [(1, 5), (5, 15), (15, 30), (30, 50), (50, 75)]
    size_range = random.choices(size_ranges, weights=size_weights)[0]
    target_size = random.uniform(size_range[0], size_range[1])

    content = generate_page_content(title, target_size)

    # Generate version info
    version_number = random.randint(1, 50)
    base_date = datetime.now() - timedelta(days=random.randint(1, 365))
    last_updated = base_date + timedelta(hours=random.randint(0, 24 * 30))

    # Build page object
    page = {
        "id": page_id,
        "title": title,
        "version": {
            "number": version_number,
            "when": last_updated.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        },
        "history": {
            "lastUpdated": {
                "when": last_updated.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
            "createdDate": base_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        },
        "body": {
            "storage": {
                "value": content,
            },
        },
        "ancestors": generate_ancestors(page_id, hierarchy),
        "space": {
            "key": "DEVDOCS",
            "name": "Development Documentation",
        },
        "_links": {
            "webui": f"/spaces/DEVDOCS/pages/{page_id}/{title.replace(' ', '+')}",
        },
    }

    # Add mock metadata based on flags
    mock_metadata: dict[str, Any] = {
        "labels": random.sample(TOPIC_WORDS, k=random.randint(0, 5)),
    }

    if include_jira:
        num_jira = random.randint(1, 5)
        mock_metadata["jira_issue_links"] = [generate_jira_link() for _ in range(num_jira)]

    if include_mentions:
        num_mentions = random.randint(1, 4)
        mock_metadata["user_mentions"] = [generate_user_mention() for _ in range(num_mentions)]

    if include_links:
        num_links = random.randint(1, 8)
        mock_metadata["internal_links"] = [
            {"page_id": f"page-{random.randint(0, 3999):05d}", "title": f"Linked Page {i}"}
            for i in range(num_links)
        ]

    page["_mock_metadata"] = mock_metadata

    return page


def generate_dataset(num_pages: int = 4000, max_depth: int = 7) -> dict[str, Any]:
    """Generate complete mock dataset."""
    print(f"Building hierarchy for {num_pages} pages (max depth: {max_depth})...")
    hierarchy = build_hierarchy(num_pages, max_depth)

    print("Generating pages...")
    pages = []

    # Determine which pages get special metadata
    page_ids = list(hierarchy.keys())
    jira_pages = set(random.sample(page_ids, k=int(num_pages * 0.20)))  # 20%
    mention_pages = set(random.sample(page_ids, k=int(num_pages * 0.30)))  # 30%
    link_pages = set(random.sample(page_ids, k=int(num_pages * 0.50)))  # 50%

    for i, page_id in enumerate(page_ids):
        if (i + 1) % 500 == 0:
            print(f"  Generated {i + 1}/{num_pages} pages...")

        page = generate_mock_page(
            page_id=page_id,
            hierarchy=hierarchy,
            include_jira=page_id in jira_pages,
            include_mentions=page_id in mention_pages,
            include_links=page_id in link_pages,
        )
        pages.append(page)

    # Calculate statistics
    total_size = sum(len(p["body"]["storage"]["value"].encode("utf-8")) for p in pages)
    avg_size = total_size / len(pages) / 1024

    level_counts = {}
    for info in hierarchy.values():
        level = info["level"]
        level_counts[level] = level_counts.get(level, 0) + 1

    stats = {
        "total_pages": num_pages,
        "total_size_mb": total_size / 1024 / 1024,
        "average_page_size_kb": avg_size,
        "max_hierarchy_depth": max_depth,
        "pages_by_level": level_counts,
        "pages_with_jira_links": len(jira_pages),
        "pages_with_user_mentions": len(mention_pages),
        "pages_with_internal_links": len(link_pages),
        "generated_at": datetime.now().isoformat(),
    }

    return {
        "pages": pages,
        "hierarchy_map": {
            pid: {"parent_id": info["parent_id"], "level": info["level"]}
            for pid, info in hierarchy.items()
        },
        "statistics": stats,
    }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate mock Confluence dataset for load testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pages", "-n",
        type=int,
        default=4000,
        help="Number of pages to generate (default: 4000)",
    )
    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        default=7,
        help="Maximum hierarchy depth (default: 7)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: tests/server/services/confluence/fixtures/mock_4000_pages.json.gz)",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Save as uncompressed JSON instead of gzip",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Mock Confluence Dataset Generator (Story 6.3)")
    print("=" * 60)
    print("Configuration:")
    print(f"  Pages: {args.pages}")
    print(f"  Max Depth: {args.max_depth}")
    print()

    # Generate dataset
    dataset = generate_dataset(num_pages=args.pages, max_depth=args.max_depth)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        fixtures_dir = Path(__file__).parent.parent / "tests" / "server" / "services" / "confluence" / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        output_path = fixtures_dir / f"mock_{args.pages}_pages.json.gz"

    # Write output
    print(f"\nWriting to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.no_compress or not str(output_path).endswith(".gz"):
        with open(output_path, "w") as f:
            json.dump(dataset, f)
    else:
        with gzip.open(output_path, "wt", encoding="utf-8") as f:
            json.dump(dataset, f)

    # Print statistics
    stats = dataset["statistics"]
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    print(f"Total Pages: {stats['total_pages']}")
    print(f"Total Size: {stats['total_size_mb']:.2f} MB")
    print(f"Average Page Size: {stats['average_page_size_kb']:.2f} KB")
    print(f"Max Hierarchy Depth: {stats['max_hierarchy_depth']}")
    print(f"Pages with JIRA Links: {stats['pages_with_jira_links']} ({stats['pages_with_jira_links']/stats['total_pages']*100:.0f}%)")
    print(f"Pages with User Mentions: {stats['pages_with_user_mentions']} ({stats['pages_with_user_mentions']/stats['total_pages']*100:.0f}%)")
    print(f"Pages with Internal Links: {stats['pages_with_internal_links']} ({stats['pages_with_internal_links']/stats['total_pages']*100:.0f}%)")
    print("\nPages by Hierarchy Level:")
    for level in sorted(stats["pages_by_level"].keys()):
        count = stats["pages_by_level"][level]
        print(f"  Level {level}: {count} pages ({count/stats['total_pages']*100:.1f}%)")
    print("=" * 60)
    print(f"\nDataset saved to: {output_path}")
    print("Use this fixture file in load tests.")


if __name__ == "__main__":
    main()
