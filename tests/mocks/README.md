# Hugo Template Dependencies - Test Mock Structures

This directory contains pattern-based mock Hugo projects for testing the dependency analyzer. Each subdirectory represents a specific Hugo template pattern or construct.

## 📋 Pattern Overview

| Pattern                                           | Purpose                  | Nodes | Edges | Key Features                     |
| ------------------------------------------------- | ------------------------ | ----- | ----- | -------------------------------- |
| [`basic_partial_pattern`](#basic_partial_pattern) | Simple partial inclusion | 2     | 1     | Basic `{{ partial }}` call       |
| [`nested_partial_chain`](#nested_partial_chain)   | Multi-level hierarchy    | 5     | 4     | 3-level nested partials          |
| [`conditional_partials`](#conditional_partials)   | Dynamic selection        | 4     | 0     | `templates.Exists` checks        |
| [`context_passing`](#context_passing)             | Data passing             | 3     | 2     | `dict()` context examples        |
| [`cached_partials`](#cached_partials)             | Caching patterns         | 3     | 2     | `partialCached` function         |
| [`template_blocks`](#template_blocks)             | Block inheritance        | 2     | 0     | `{{ block }}` and `{{ define }}` |
| [`inline_partials`](#inline_partials)             | Inline definitions       | 1     | 0     | `{{ define "_partials/..." }}`   |
| [`function_integration`](#function_integration)   | Hugo functions           | 3     | 2     | `printf`, `dict`, `slice`, `add` |
| [`shortcode_templates`](#shortcode_templates)     | Shortcode patterns       | 4     | 2     | `layouts/shortcodes/` directory  |
| [`real_world_complex`](#real_world_complex)       | Realistic structure      | 12    | 11    | Multi-level article hierarchy    |

---

## 🎯 Pattern Details

### basic_partial_pattern

**Purpose:** Test basic partial inclusion pattern  
**Structure:**
```
layouts/
├── single.html              # Template calling header partial
└── _partials/
    └── header.html          # Simple header partial
```

**Key Construct:**
```go
{{ partial "header.html" . }}
```

**Expected Analysis:**
- 2 nodes: single.html → header.html
- 1 edge: includes relationship
- Tests basic partial resolution

---

### nested_partial_chain

**Purpose:** Test multi-level partial hierarchy  
**Structure:**
```
layouts/
├── index.html               # Entry point
└── _partials/
    ├── layout/
    │   └── main.html        # Layout wrapper
    └── components/
        ├── sidebar.html     # Sidebar component
        ├── content.html     # Content area (leaf)
        └── widgets/
            └── navigation.html  # Navigation widget (leaf)
```

**Key Pattern:**
```
index.html → layout/main.html → components/sidebar.html → widgets/navigation.html
                              → components/content.html
```

**Expected Analysis:**
- 5 nodes: 3-level hierarchy
- 4 edges: nested includes
- Tests deep partial chains

---

### conditional_partials

**Purpose:** Test dynamic partial selection with fallbacks  
**Structure:**
```
layouts/
├── list.html                # Template with conditional logic
└── _partials/
    ├── card-layout.html     # Conditional option 1
    ├── list-layout.html     # Conditional option 2
    └── default-layout.html  # Fallback option
```

**Key Construct:**
```go
{{ if templates.Exists "partials/card-layout.html" }}
  {{ partial "card-layout.html" . }}
{{ else if templates.Exists "partials/list-layout.html" }}
  {{ partial "list-layout.html" . }}
{{ else }}
  {{ partial "default-layout.html" . }}
{{ end }}
```

**Expected Analysis:**
- 4 nodes: 1 template + 3 partials
- 0 edges: conditional calls may not create static edges
- Tests `templates.Exists` pattern

---

### context_passing

**Purpose:** Test complex context and data passing  
**Structure:**
```
layouts/
├── single.html              # Template passing context
└── _partials/
    └── meta/
        ├── article-info.html    # Uses .context and .scope
        └── author-info.html     # Uses .Author directly
```

**Key Constructs:**
```go
{{ partial "meta/article-info.html" (dict "context" . "scope" "single") }}
{{ partial "meta/author-info.html" .Author }}
```

**Expected Analysis:**
- 3 nodes: single.html → 2 meta partials
- 2 edges: includes with context
- Tests `dict()` and direct data passing

---

### cached_partials

**Purpose:** Test `partialCached` function calls  
**Structure:**
```
layouts/
├── baseof.html              # Base template with caching
└── _partials/
    ├── head-meta.html       # Cached per page
    └── analytics.html       # Cached per site
```

**Key Construct:**
```go
{{ partialCached "head-meta.html" . }}
{{ partialCached "analytics.html" .Site }}
```

**Expected Analysis:**
- 3 nodes: baseof + 2 cached partials
- 2 edges: cached includes
- Tests `partialCached` detection

---

### template_blocks

**Purpose:** Test block inheritance pattern  
**Structure:**
```
layouts/_default/
├── baseof.html              # Base template with blocks
└── single.html              # Template defining blocks
```

**Key Constructs:**
```go
# baseof.html
{{ block "main" . }}{{ end }}
{{ block "sidebar" . }}{{ end }}

# single.html
{{ define "main" }}...{{ end }}
{{ define "sidebar" }}...{{ end }}
```

**Expected Analysis:**
- 2 nodes: baseof.html and single.html
- 0 edges: block inheritance is not a traditional include
- Tests `{{ block }}` and `{{ define }}` detection

---

### inline_partials

**Purpose:** Test inline partial definitions  
**Structure:**
```
layouts/
└── home.html                # Template with inline partials
```

**Key Construct:**
```go
{{ define "_partials/inline-helper.html" }}
  <div>Inline helper content</div>
{{ end }}

{{ partial "inline-helper.html" (dict "message" "test") }}
```

**Expected Analysis:**
- 1 node: home.html
- 0 edges: inline partials are defined in same file
- Tests `{{ define "_partials/..." }}` syntax
- **Note:** Analyzer treats inline partials as unresolved (expected behavior)

---

### function_integration

**Purpose:** Test Hugo function usage in templates  
**Structure:**
```
layouts/
├── taxonomy.html            # Template using multiple functions
└── _partials/
    ├── term-links.html      # Partial receiving processed data
    └── badge.html           # Partial for UI components
```

**Key Functions:**
```go
{{ printf "%s: %s" .Data.Singular .Title }}
{{ $terms := slice }}
{{ $terms = $terms | append (dict "Name" $key "Count" $value.Count) }}
{{ $totalPosts = add $totalPosts .Count }}
```

**Expected Analysis:**
- 3 nodes: taxonomy.html → 2 partials
- 2 edges: includes with function-processed data
- Tests `printf`, `dict`, `slice`, `append`, `add` functions

---

### shortcode_templates

**Purpose:** Test shortcode patterns  
**Structure:**
```
layouts/
├── shortcodes/
│   ├── alert.html           # Alert shortcode
│   └── figure.html          # Figure shortcode
└── _partials/
    ├── icon.html            # Icon partial
    └── image-processor.html # Image processing partial
```

**Key Pattern:**
```go
# In shortcode
{{ partial "icon.html" $type }}
{{ partial "image-processor.html" . }}
```

**Expected Analysis:**
- 4 nodes: 2 shortcodes + 2 partials
- 2 edges: shortcode → partial dependencies
- Tests `layouts/shortcodes/` directory pattern

---

### real_world_complex

**Purpose:** Realistic Hugo site structure based on Blowfish theme  
**Structure:**
```
layouts/
├── _default/
│   └── single.html          # Article template
└── _partials/
    ├── article/
    │   ├── header.html      # Article header
    │   ├── content.html     # Article content
    │   └── footer.html      # Article footer
    ├── meta/
    │   ├── main.html        # Meta aggregator
    │   ├── author.html      # Author info
    │   ├── published.html   # Publication date
    │   └── tags.html        # Tag list
    ├── analytics/
    │   ├── tracker.html     # Analytics tracker
    │   └── events.html      # Event tracking
    └── shared/
        ├── button.html      # Reusable button
        └── icon.html        # Reusable icon
```

**Dependency Graph:**
```
single.html
├── article/header.html
│   └── meta/main.html
│       ├── meta/author.html
│       ├── meta/published.html
│       └── meta/tags.html
├── article/content.html
├── article/footer.html
│   ├── shared/button.html
│   └── shared/icon.html
└── analytics/tracker.html
    └── analytics/events.html
```

**Expected Analysis:**
- 12 nodes: realistic multi-level hierarchy
- 11 edges: complex dependency graph
- Tests real-world Hugo site patterns

---

## 🧪 Testing Guidelines

### Running Analysis on Individual Patterns

```bash
# Analyze a specific pattern
uv run hugo-template-dependencies analyze tests/mocks/basic_partial_pattern --format json

# With different output formats
uv run hugo-template-dependencies analyze tests/mocks/nested_partial_chain --format mermaid
uv run hugo-template-dependencies analyze tests/mocks/real_world_complex --format dot
```

### Running Integration Tests

```bash
# Test all Phase 2 patterns (basic, nested, conditional, context)
uv run python -m pytest tests/integration/test_complete_pipeline.py::TestIntegrationPipeline::test_new_pattern_mock_structures -v

# Test all Phase 3 patterns (cached, blocks, inline, functions, shortcodes)
uv run python -m pytest tests/integration/test_complete_pipeline.py::TestIntegrationPipeline::test_phase3_advanced_patterns -v

# Run all integration tests
uv run python -m pytest tests/integration/test_complete_pipeline.py -v
```

### Expected Node Counts

| Pattern               | Expected Nodes | Notes                                         |
| --------------------- | -------------- | --------------------------------------------- |
| basic_partial_pattern | 2              | single.html + header.html                     |
| nested_partial_chain  | 5              | index + main + sidebar + content + navigation |
| conditional_partials  | 4              | list + 3 conditional partials                 |
| context_passing       | 3              | single + 2 meta partials                      |
| cached_partials       | 3              | baseof + 2 cached partials                    |
| template_blocks       | 2              | baseof + single                               |
| inline_partials       | 1-3            | home.html + possibly unresolved inline refs   |
| function_integration  | 3              | taxonomy + 2 partials                         |
| shortcode_templates   | 4              | 2 shortcodes + 2 partials                     |
| real_world_complex    | 12             | Full article hierarchy                        |

---

## 🔍 Pattern Selection Guide

**Use this pattern when testing:**

- **Basic partial resolution** → `basic_partial_pattern`
- **Deep nesting** → `nested_partial_chain`
- **Conditional logic** → `conditional_partials`
- **Context passing** → `context_passing`
- **Caching behavior** → `cached_partials`
- **Block inheritance** → `template_blocks`
- **Inline definitions** → `inline_partials`
- **Hugo functions** → `function_integration`
- **Shortcodes** → `shortcode_templates`
- **Real-world scenarios** → `real_world_complex`

---

## 📚 References

- **Hugo Partial Documentation:** https://gohugo.io/templates/partials/
- **Hugo Block Templates:** https://gohugo.io/templates/base/
- **Hugo Shortcodes:** https://gohugo.io/templates/shortcode-templates/
- **Blowfish Theme:** https://github.com/nunocoracao/blowfish (inspiration for real_world_complex)

---

## 🗑️ Deprecated Patterns

### nested_partials_project (REMOVED)

**Status:** ⚠️ Deprecated - Replaced by pattern-based mocks  
**Reason:** Calendar-themed naming was domain-specific and didn't clearly indicate Hugo constructs being tested  
**Replacement:** Use `nested_partial_chain` for similar testing scenarios

---

**Last Updated:** 2026-02-10  
**Maintainer:** Hugo Template Dependencies Project
