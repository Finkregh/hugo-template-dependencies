# Hugo Template Dependencies Mock Patterns

This directory contains comprehensive test patterns for the Hugo template dependency analyzer. Each pattern demonstrates specific Hugo template constructs and dependency relationships.

## Pattern Overview

### Phase 1 & 2: Core Patterns
- **`basic_partial_pattern/`** - Simple partial inclusion (1 level)
- **`nested_partial_chain/`** - Multi-level partial hierarchy (3 levels)  
- **`conditional_partials/`** - Dynamic partial selection with templates.Exists
- **`context_passing/`** - Complex context passing with dict() and direct parameters

### Phase 3: Advanced Patterns  
- **`cached_partials/`** - Performance optimization with partialCached
- **`template_blocks/`** - Template inheritance with baseof.html and blocks
- **`inline_partials/`** - Inline partial definitions within templates
- **`function_integration/`** - Hugo functions (print, printf, dict, slice, etc.)
- **`shortcode_templates/`** - Shortcode templates calling partials

### Phase 4: Real-World Validation
- **`real_world_complex/`** - Production-realistic theme complexity (coming soon)

---

## Pattern Details

### basic_partial_pattern (2 nodes, 1 edge)
**Purpose:** Test simple partial inclusion and basic dependency tracking

**Structure:**
```
layouts/single.html → calls partial "header.html"
layouts/_partials/header.html (no dependencies)
```

**Dependencies:**
- `single.html` → `header.html`

**Usage:** Basic template calling a simple header partial

---

### nested_partial_chain (5 nodes, 4 edges)  
**Purpose:** Test multi-level partial dependencies and context passing

**Structure:**
```
layouts/index.html → calls partial "layout/main.html"
layouts/_partials/layout/main.html → calls "components/sidebar.html" + "components/content.html"
layouts/_partials/components/sidebar.html → calls "components/widgets/navigation.html" 
layouts/_partials/components/content.html (leaf)
layouts/_partials/components/widgets/navigation.html (leaf)
```

**Dependencies:**
- `index.html` → `layout/main.html`
- `layout/main.html` → `components/sidebar.html`
- `layout/main.html` → `components/content.html` 
- `components/sidebar.html` → `components/widgets/navigation.html`

**Usage:** Complex nested layout with 3-level partial hierarchy

---

### conditional_partials (4 nodes, 1 edge)
**Purpose:** Test dynamic partial selection and existence checking

**Structure:**
```
layouts/list.html → conditional selection of partials
layouts/_partials/card-layout.html
layouts/_partials/list-layout.html  
layouts/_partials/default-layout.html (fallback)
```

**Dependencies:**
- `list.html` → `default-layout.html` (fallback detected)

**Logic:** Uses `templates.Exists` to conditionally select layout partials

**Usage:** Dynamic layout selection based on parameters with fallback

---

### context_passing (3 nodes, 2 edges)
**Purpose:** Test various context and dictionary passing methods

**Structure:**
```
layouts/single.html → calls partials with dict() and direct context
layouts/_partials/meta/article-info.html (uses .context and .scope)
layouts/_partials/meta/author-info.html (uses direct parameter data)
```

**Dependencies:**
- `single.html` → `meta/article-info.html`
- `single.html` → `meta/author-info.html`

**Context Patterns:**
- `dict("context" . "scope" "single" "showDate" true)` 
- Direct parameter passing with `.Params.author`

**Usage:** Complex data passing to partials with structured contexts

---

### cached_partials (3 nodes, 0 edges)
**Purpose:** Test partialCached function and caching behavior

**Structure:**
```
layouts/baseof.html → calls partialCached "head-meta.html" and "analytics.html"
layouts/_partials/head-meta.html (cached per page)
layouts/_partials/analytics.html (cached per site)
```

**Dependencies:**
- No traditional edges (partialCached is performance optimization, not dependency)

**Caching:**
- `head-meta.html` cached per page context
- `analytics.html` cached per site context

**Usage:** Performance-optimized partial inclusion with caching

---

### template_blocks (2 nodes, 0 edges)
**Purpose:** Test block definitions and template inheritance

**Structure:**
```
layouts/_default/baseof.html → defines blocks (main, sidebar, title, head, footer)
layouts/_default/single.html → overrides blocks with {{ define "blockname" }}
```

**Dependencies:**
- No traditional edges (inheritance relationship, not partial calls)

**Blocks:**
- `title`, `head`, `main`, `sidebar`, `footer` blocks defined in baseof
- `single.html` overrides `title`, `head`, `main`, `sidebar` blocks

**Usage:** Hugo template inheritance with block definitions and overrides

---

### inline_partials (1+ nodes, varies)
**Purpose:** Test inline partial definitions within templates

**Structure:**
```
layouts/home.html → defines and calls inline partials
  {{ define "_partials/inline-helper.html" }}
  {{ define "_partials/icon-renderer.html" }}
```

**Dependencies:**
- Analyzer limitation: inline partials not detected as separate nodes
- Documents potential enhancement area

**Inline Definitions:**
- `inline-helper.html` for dynamic messages with timestamps
- `icon-renderer.html` for emoji-based icons

**Usage:** Template-specific helper partials defined inline

---

### function_integration (3 nodes, 3 edges)
**Purpose:** Test partials using Hugo functions and complex logic

**Structure:**
```
layouts/taxonomy.html → calls partials with complex data structures
layouts/_partials/term-links.html → processes slices and dicts
layouts/_partials/badge.html → uses dict lookups and conditionals
```

**Dependencies:**
- `taxonomy.html` → `term-links.html`
- `taxonomy.html` → `badge.html`
- `term-links.html` → `badge.html`

**Hugo Functions:**
- `print`, `printf`, `dict`, `slice`, `append`, `len`, `add`, `cond`, `index`
- Complex data manipulation and conditional logic

**Usage:** Advanced Hugo template programming with function integration

---

### shortcode_templates (4 nodes, 2 edges)
**Purpose:** Test shortcode template patterns

**Structure:**
```
layouts/shortcodes/figure.html → calls partial "image-processor.html"
layouts/shortcodes/alert.html → calls partial "icon.html"  
layouts/_partials/image-processor.html (image processing logic)
layouts/_partials/icon.html (icon rendering)
```

**Dependencies:**
- `shortcodes/figure.html` → `image-processor.html`
- `shortcodes/alert.html` → `icon.html`

**Shortcode Features:**
- Parameter processing with `.Get`
- Inner content with `.Inner`
- Conditional logic and defaults

**Usage:** Shortcode templates that delegate to reusable partials

---

## Testing Guidelines

### Running Individual Pattern Analysis
```bash
uv run python -m hugo_template_dependencies.cli analyze tests/mocks/PATTERN_NAME --format json
```

### Expected Performance
All patterns should complete analysis in < 1 second (target: < 5 seconds for full suite)

### Validation Commands
```bash
# Test all patterns
make test

# Test specific integration
uv run python -m pytest tests/integration/test_complete_pipeline.py::TestIntegrationPipeline::test_new_pattern_mock_structures -v
uv run python -m pytest tests/integration/test_complete_pipeline.py::TestIntegrationPipeline::test_phase3_advanced_patterns -v
```

---

## Pattern Statistics

| Pattern | Nodes | Edges | Complexity Level | Primary Feature |
|---------|--------|--------|------------------|-----------------|
| basic_partial_pattern | 2 | 1 | Beginner | Simple partial call |
| nested_partial_chain | 5 | 4 | Intermediate | Multi-level nesting |
| conditional_partials | 4 | 1 | Intermediate | Dynamic selection |
| context_passing | 3 | 2 | Intermediate | Complex data passing |
| cached_partials | 3 | 0 | Advanced | Performance optimization |
| template_blocks | 2 | 0 | Advanced | Template inheritance |
| inline_partials | 1+ | varies | Advanced | Inline definitions |
| function_integration | 3 | 3 | Advanced | Hugo functions |
| shortcode_templates | 4 | 2 | Advanced | Shortcode patterns |

**Total Coverage:** 26+ nodes, 13+ edges across all Hugo template constructs

---

## Pattern Evolution

### Naming Convention Change
These patterns replace the legacy calendar-themed structure:

**Old (Calendar-themed):**
- `nested_partials_project/recurrence_human_readable.html`
- `recurrence/daily_frequency.html`
- `recurrence/weekly_frequency.html`

**New (Pattern-based):**
- `nested_partial_chain/layout/main.html`
- `components/sidebar.html`  
- `components/widgets/navigation.html`

### Advantages of Pattern-based Naming
1. **Clear Intent** - File names indicate template construct being tested
2. **Educational** - Serves as Hugo template pattern documentation  
3. **Maintainable** - Easy to add new patterns or modify existing ones
4. **Comprehensive** - Covers all major Hugo template features

---

## Contributing New Patterns

### Pattern Requirements
1. **Clear Purpose** - Document what specific Hugo construct is being tested
2. **Realistic Structure** - Based on real-world theme patterns
3. **Comprehensive Testing** - Include integration test validation
4. **Performance** - Analysis should complete quickly (< 1 second target)

### Pattern Template
```
tests/mocks/new_pattern/
├── layouts/
│   └── [template files]
└── layouts/_partials/
    └── [partial files]
```

### Documentation Update
Add pattern details to this README with:
- Purpose and structure
- Dependencies and node/edge counts  
- Usage examples
- Integration test expectations

---

**Last Updated:** 2026-02-02  
**Pattern Coverage:** All major Hugo template constructs  
**Status:** Comprehensive test suite for Hugo template dependency analysis