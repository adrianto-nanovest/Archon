# Serena MCP Command Reference for Code Operations

**CRITICAL REMINDER: ALWAYS USE Serena MCP for all code operations**

This reference documents the essential Serena MCP commands used during successful fork syncing and general code operations.

## Core Analysis Commands

### 1. **Directory and File Exploration**

```bash
# List directory contents
serena:list_dir(relative_path="python/src/server/services", recursive=false)

# Find specific files
serena:find_file(file_mask="*provider*", relative_path="python/src/server/services")

# Search for patterns across codebase
serena:search_for_pattern(
    substring_pattern="google.*provider",
    relative_path="python/src/server/services",
    context_lines_before=2,
    context_lines_after=2
)
```

### 2. **Code Structure Analysis**

```bash
# Get overview of file symbols (classes, functions, etc.)
serena:get_symbols_overview(relative_path="python/src/server/services/llm_provider_service.py")

# Find specific symbol with body
serena:find_symbol(
    name_path="ClassName",
    relative_path="python/src/server/services",
    include_body=true,
    depth=1
)

# Find references to a symbol
serena:find_referencing_symbols(
    name_path="methodName",
    relative_path="python/src/server/services/source_management_service.py"
)
```

## Code Modification Commands

### 3. **Targeted Code Changes**

```bash
# Replace entire symbol (function, class, method)
serena:replace_symbol_body(
    name_path="functionName",
    relative_path="python/src/server/services/example.py",
    body="def functionName():\n    # new implementation\n    pass"
)

# Insert code after a symbol
serena:insert_after_symbol(
    name_path="ClassName",
    relative_path="python/src/server/services/example.py",
    body="\n\nclass NewClass:\n    pass"
)

# Insert code before a symbol  
serena:insert_before_symbol(
    name_path="firstFunction",
    relative_path="python/src/server/services/example.py",
    body="import new_module\n"
)
```

## Analysis and Planning Commands

### 4. **Cognitive Operations**

```bash
# Think about collected information (use after searches)
serena:think_about_collected_information()

# Think about task adherence (use before major changes)
serena:think_about_task_adherence()

# Think about completion status
serena:think_about_whether_you_are_done()
```

## Successful Fork Sync Patterns

### Pattern 1: **Conflict Analysis**

```bash
# 1. Understand file structure
serena:get_symbols_overview(relative_path="conflicted_file.py")

# 2. Find specific symbols involved
serena:find_symbol(name_path="ConflictedClass", include_body=true)

# 3. Search for related patterns
serena:search_for_pattern(substring_pattern="related_pattern")

# 4. Think about what you learned
serena:think_about_collected_information()
```

### Pattern 2: **Feature Validation**

```bash
# 1. Search for your key improvements
serena:search_for_pattern(
    substring_pattern="google.*provider|sentence.transformers",
    context_lines_before=1,
    context_lines_after=1
)

# 2. Verify functionality is intact
serena:find_symbol(name_path="YourImprovedFunction", include_body=true)

# 3. Check references still work
serena:find_referencing_symbols(name_path="YourImprovedFunction")
```

### Pattern 3: **Code Integration**

```bash
# 1. Understand existing structure
serena:get_symbols_overview(relative_path="target_file.py")

# 2. Find insertion points
serena:find_symbol(name_path="ExistingClass", depth=1)

# 3. Make targeted changes
serena:insert_after_symbol(name_path="ExistingMethod", body="new_code")

# 4. Validate the changes
serena:think_about_task_adherence()
```

## Advanced Search Patterns

### 5. **Complex Pattern Matching**

```bash
# Find async patterns
serena:search_for_pattern(substring_pattern="async def.*provider")

# Find imports
serena:search_for_pattern(substring_pattern="^from.*import", context_lines_after=0)

# Find specific configurations
serena:search_for_pattern(
    substring_pattern="google.*api.*key",
    paths_include_glob="*.py",
    restrict_search_to_code_files=true
)

# Find error handling patterns
serena:search_for_pattern(substring_pattern="except.*Exception")
```

### 6. **Multi-File Operations**

```bash
# Search across specific directories
serena:search_for_pattern(
    substring_pattern="TARGET_PATTERN",
    relative_path="python/src/server",
    context_lines_before=2
)

# Find symbols across multiple files
serena:find_symbol(
    name_path="CommonInterface",
    relative_path="python/src",  # Broader search
    substring_matching=true
)
```

## Best Practices from Successful Rebase

### 7. **Workflow Integration**

**Before Making Changes:**
```bash
# 1. Research the codebase
serena:search_for_pattern(substring_pattern="relevant_pattern")
serena:get_symbols_overview(relative_path="target_file.py")

# 2. Understand existing code
serena:find_symbol(name_path="ExistingCode", include_body=true)

# 3. Plan your changes
serena:think_about_collected_information()
```

**During Conflict Resolution:**
```bash
# 1. Understand both versions
serena:search_for_pattern(substring_pattern="conflicted_pattern")

# 2. Find the best integration approach
serena:find_symbol(name_path="ConflictedSymbol", include_body=true)

# 3. Make targeted merge
serena:replace_symbol_body(name_path="Symbol", body="merged_version")

# 4. Validate result
serena:think_about_task_adherence()
```

**After Changes:**
```bash
# 1. Verify functionality
serena:search_for_pattern(substring_pattern="your_key_features")

# 2. Check integration
serena:find_referencing_symbols(name_path="ModifiedSymbol")

# 3. Confirm completion
serena:think_about_whether_you_are_done()
```

## Memory Management Commands

### 8. **Project Knowledge**

```bash
# Write important information for future reference
serena:write_memory(
    memory_name="rebase_insights_2025_08",
    content="Key findings from successful rebase process..."
)

# Read previous insights
serena:read_memory(memory_file_name="rebase_insights_2025_08")

# List available memories
serena:list_memories()
```

## Error Prevention Tips

### 9. **Common Pitfalls to Avoid**

**❌ Don't do this:**
```bash
# Reading entire large files
Read(file_path="/path/to/large_file.py")  # Inefficient

# Generic searches without context
serena:search_for_pattern(substring_pattern="class")  # Too broad
```

**✅ Do this instead:**
```bash
# Targeted symbol reading
serena:find_symbol(name_path="SpecificClass", include_body=true)

# Focused pattern searches
serena:search_for_pattern(
    substring_pattern="class.*Provider",
    relative_path="python/src/server/services"
)
```

### 10. **Performance Optimization**

**Efficient Patterns:**
```bash
# Use specific paths to narrow search scope
relative_path="python/src/server/services"  # Not just "python/"

# Use appropriate context lines
context_lines_before=1, context_lines_after=1  # Not 10+

# Restrict search when possible
restrict_search_to_code_files=true  # When only looking for code

# Use depth appropriately  
depth=1  # Don't go deeper than needed
```

---

**Remember:** Serena MCP provides intelligent, efficient code operations that are far superior to manual file reading and editing. Always use these tools for cleaner commits, better conflict resolution, and more successful rebases!