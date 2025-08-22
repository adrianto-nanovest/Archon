# Fork Sync Strategy for Active Repositories

**Last Updated:** 2025-08-22  
**Context:** Archon V2 Alpha - High-velocity upstream development

## Core Principle: Regular Incremental Rebases

The key to managing a fork of an active repository is **staying close to upstream** through frequent, small rebases rather than infrequent, large ones.

## Essential Workflow

### 1. Weekly Maintenance (Even Without Changes)

```bash
# Every 1-2 weeks - keep fork synchronized
git fetch upstream
git rebase upstream/main
git push origin main --force-with-lease
```

**Why This Works:**
- Small conflicts are easier to resolve
- Maintains clean linear history
- Prevents "integration debt" from accumulating

### 2. Pre-Work Synchronization

```bash
# ALWAYS sync before starting new features
git fetch upstream
git rebase upstream/main  # Resolve any conflicts first
git push origin main --force-with-lease

# Now start your work on a clean base
```

### 3. Commit Organization Strategy

**✅ Good - Atomic Commits:**
```bash
git commit -m "fix: Google provider async context handling"
git commit -m "fix: sentence-transformers import in reranking strategy"  
git commit -m "feat: add Confluence integration planning docs"
git commit -m "refactor: improve source type detection logic"
```

**❌ Avoid - Mixed Purpose Commits:**
```bash
git commit -m "various fixes and improvements"  # Nightmare to rebase
git commit -m "WIP - multiple changes"         # Creates conflict complexity
```

## Advanced Strategies by Development Pattern

### Pattern A: Small Targeted Improvements
**Best for:** Bug fixes, performance improvements, configuration tweaks

```bash
# Direct rebase approach (what we used successfully)
git fetch upstream
git rebase upstream/main
git push origin main --force-with-lease
```

**Advantages:**
- Simple workflow
- Easy conflict resolution
- Quick to execute

### Pattern B: Feature Development
**Best for:** New functionality, significant additions

```bash
# Feature branch strategy
git checkout -b feature/confluence-integration upstream/main

# Develop feature in focused commits
git commit -m "feat: add Confluence API client"
git commit -m "feat: implement Confluence source type"
git commit -m "test: add Confluence integration tests"

# Keep feature branch updated with upstream
git fetch upstream
git rebase upstream/main

# Integrate when ready
git checkout main
git rebase upstream/main      # Ensure main is current
git rebase feature/confluence-integration  # Clean integration
git push origin main --force-with-lease
```

### Pattern C: High-Velocity Upstream (Current Scenario)
**Best for:** Very active repositories with daily changes

```bash
# Daily upstream monitoring
git fetch upstream

# If you have uncommitted work
git stash
git rebase upstream/main
git push origin main --force-with-lease
git stash pop

# If you have committed work ready for integration
git rebase upstream/main
git push origin main --force-with-lease
```

## Conflict Prevention Strategies

### 1. Strategic File Selection

**High-Risk Files (Avoid Modifying):**
- Core service files (`main.py`, primary APIs)
- Build configurations (`requirements.txt`, `package.json`)
- Database migrations
- CI/CD configurations

**Low-Risk Files (Safe to Modify):**
- New feature files
- Documentation
- Configuration extensions
- Isolated utility functions

### 2. Code Change Best Practices

**ALWAYS use Serena MCP for code operations:**
```bash
# Research first
serena:find_symbol(name_path="ClassName", include_body=true)
serena:find_referencing_symbols(name_path="methodName")

# Make targeted changes
serena:replace_symbol_body(name_path="functionName", body="...")
serena:insert_after_symbol(name_path="className", body="...")

# Think before committing
serena:think_about_collected_information()
```

**Benefits:**
- Creates cleaner, more targeted commits
- Easier conflict resolution during rebase
- Better code quality and maintainability

### 3. Commit Message Standards

```bash
# Template for clear commit messages
git commit -m "<type>(<scope>): <description>

<detailed explanation of what and why>
<any breaking changes or migration notes>

Refs: #issue-number"
```

**Examples:**
```bash
git commit -m "fix(google-provider): resolve async context timeout

- Add proper async/await to provider initialization  
- Fix embedding model default for Gemini (gemini-embedding-001)
- Handle Google API rate limiting gracefully

Resolves timeout issues during high-volume operations
Refs: #issue-123"
```

## Emergency Strategies

### When Rebase Becomes Too Complex

```bash
# Create safety backup
git branch backup-complex-rebase

# Option 1: Reset and cherry-pick approach
git reset --hard upstream/main
git cherry-pick <commit-hash>  # Pick your important commits one by one

# Option 2: Merge strategy (if rebase is too complex)
git fetch upstream
git merge upstream/main  # Creates merge commit but preserves history
```

### Recovery from Failed Rebase

```bash
# If rebase goes wrong
git rebase --abort  # Back to starting state

# Alternative approach
git reset --hard backup-before-rebase  # Use your backup
git rebase upstream/main --strategy=ours  # Favor your changes
```

## Tools and Automation

### Git Aliases for Efficiency

```bash
# Add to ~/.gitconfig
[alias]
    sync = "!git fetch upstream && git rebase upstream/main && git push origin main --force-with-lease"
    backup = "!git branch backup-$(date +%Y%m%d-%H%M%S)"
    conflicts = "diff --name-only --diff-filter=U"
```

Usage:
```bash
git backup  # Creates timestamped backup branch
git sync    # Full sync workflow in one command
```

### GitHub CLI Integration

```bash
# Check for upstream updates
gh repo sync owner/repo --source upstream-owner/original-repo

# View upstream changes before syncing  
gh repo diff upstream/main...main
```

## Validation Checklist

After each successful rebase, validate these areas:

### 1. Critical Functionality Tests
```bash
# Check your key improvements are intact
serena:search_for_pattern(substring_pattern="google.*provider")
serena:search_for_pattern(substring_pattern="sentence.transformers")
```

### 2. Build and Test Validation
```bash
# Run relevant tests
uv run pytest tests/test_key_functionality.py -v

# Check for linting issues
uv run ruff check python/src/
```

### 3. Configuration Integrity
```bash
# Verify configuration files weren't broken
git diff HEAD~1 -- "*.json" "*.yaml" "*.toml"
```

## Your Optimal Workflow Summary

1. **Weekly sync** (even without local changes)
2. **Pre-work sync** (always start from latest upstream)
3. **Atomic commits** with clear, descriptive messages
4. **Serena MCP** for all code operations
5. **Strategic file selection** (avoid high-conflict areas)
6. **Test validation** after each successful rebase
7. **Safety backups** before complex operations

This approach ensures your fork remains healthy, conflicts stay manageable, and your valuable improvements are preserved through the project's evolution.

---

**Remember:** The goal isn't to avoid conflicts entirely—it's to make them small, predictable, and easy to resolve. Regular maintenance is far less work than emergency repairs!