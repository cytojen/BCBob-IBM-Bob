# BCB Architecture Overview

## System Design

BCB (Better Call Bob) is an autonomous CLI tool that audits and repairs codebases using IBM Bob LLM for intelligent analysis.

## Core Components

### 1. Scanner Module (`bcb/scanner/`)

**codebase.py** - Codebase Discovery
- Walks directory tree
- Detects languages and frameworks
- Identifies entry points and config files
- Loads dependencies from package managers
- Respects .gitignore patterns

**patterns.py** - Pattern Matching
- Loads vulnerability patterns from YAML
- Applies regex-based pattern matching
- Filters by language and severity
- Supports file-level checks (e.g., .env in git)

**architecture.py** - Architecture Mapping
- Builds module dependency graph
- Identifies API endpoints
- Maps trust boundaries
- Tracks database access patterns
- Analyzes authentication flow
- Detects state management patterns

### 2. Analyzer Module (`bcb/analyzer/`)

**llm_client.py** - IBM Bob Integration
- Async HTTP client with retry logic
- Response caching (SHA256-based)
- Batch processing for efficiency
- Structured output parsing (Pydantic models)
- Four main operations:
  - `verify_finding()` - Confirm vulnerabilities
  - `cluster_root_cause()` - Identify architectural issues
  - `generate_patch()` - Create fixes
  - `review_patch()` - Validate patches

**security.py** - Security Analysis
- Verifies findings using LLM
- Filters by confidence threshold
- Categorizes by severity
- Groups by file/pattern
- Identifies high-priority issues
- Determines if human review needed

**root_cause.py** - Root Cause Clustering
- Groups similar findings
- Uses LLM to identify architectural causes
- Prioritizes by severity and impact
- Distinguishes fixable vs. review-required
- Generates statistics

### 3. Fixer Module (`bcb/fixer/`)

**patch.py** - Patch Management
- Generates patches via LLM
- Applies patches using `git apply`
- Verifies syntax (Python, JavaScript)
- Runs existing test suites
- Supports revert operations
- Creates/restores git stashes

**repair_loop.py** - Iterative Repair
- Implements scan-fix-verify cycle
- Maximum iteration limit (default: 5)
- Tracks progress per iteration
- Stops when no critical/high remain
- Handles patch failures gracefully
- Maintains git stash for safety

### 4. Reporter Module (`bcb/reporter/`)

**report.py** - Report Generation
- Markdown format (primary)
- JSON format (for CI/CD)
- HTML format (for viewing)
- Executive summary with stats
- Root cause grouping
- Detailed findings with code snippets
- Iteration log
- Human review section

### 5. CLI (`bcb/cli.py`)

**Commands:**
- `bcb scan <path>` - Main command
- `bcb fix <path>` - Fix existing issues
- `bcb report <path>` - Generate report
- `bcb verify <path>` - Re-scan after fixes
- `bcb version` - Show version

**Options:**
- `--severity` - Filter by severity
- `--report-only` - No fixes
- `--no-fix` - Scan only
- `--max-iterations` - Iteration limit
- `--output` - Custom report path
- `--dry-run` - Preview fixes

## Data Flow

```
1. Discovery Phase
   ├─> Walk directory tree
   ├─> Detect languages/frameworks
   ├─> Load dependencies
   └─> Identify entry points

2. Architecture Mapping
   ├─> Build module graph
   ├─> Map API endpoints
   ├─> Identify trust boundaries
   └─> Analyze auth/data flow

3. Static Scan
   ├─> Load patterns from YAML
   ├─> Apply regex matching
   ├─> Filter by language/severity
   └─> Generate candidate findings

4. LLM Verification
   ├─> Batch findings
   ├─> Call IBM Bob API
   ├─> Parse structured responses
   ├─> Filter by confidence
   └─> Update findings

5. Root Cause Analysis
   ├─> Group similar findings
   ├─> LLM clustering
   ├─> Prioritize by severity
   └─> Generate fix strategies

6. Report Generation
   ├─> Calculate statistics
   ├─> Group by root cause
   ├─> Format as markdown
   └─> Save to file

7. Repair Loop (if enabled)
   ├─> Create git stash
   ├─> For each root cause:
   │   ├─> Generate patch (LLM)
   │   ├─> Apply patch (git)
   │   ├─> Verify syntax
   │   ├─> Run tests
   │   └─> Revert if failed
   ├─> Re-scan codebase
   ├─> Check for new issues
   └─> Iterate until clean
```

## Pattern Database

Located in `bcb/config/patterns.yaml`:

**Structure:**
```yaml
patterns:
  - id: SEC-001
    name: Pattern Name
    severity: CRITICAL|HIGH|MEDIUM|LOW
    cwe: CWE-XXX
    languages: [python, javascript, ...]
    pattern_type: regex|ast|file_check
    pattern: "regex or AST query"
    description: "What this detects"
    fix_template: "How to fix"
    llm_prompt: "Verification prompt"
```

**Categories:**
1. Secrets & Credentials (SEC-001 to SEC-006)
2. Injection Vulnerabilities (INJ-001 to INJ-007)
3. Authentication & Authorization (AUTH-001 to AUTH-008)
4. CORS, CSP, Headers (CORS-001 to CORS-003)
5. Input Validation (VAL-001 to VAL-004)
6. Information Disclosure (INFO-001 to INFO-004)
7. Rate Limiting & DoS (RATE-001 to RATE-003)
8. Logic Bugs - State (LOGIC-001 to LOGIC-003)
9. Logic Bugs - Async (ASYNC-001 to ASYNC-003)
10. Architectural Smells (ARCH-001)

## LLM Integration

**Caching Strategy:**
- Cache key: SHA256(prompt + context)
- Cache location: `~/.bcb/cache/`
- Cache format: JSON files
- Reduces API calls by ~70% on re-scans

**Batching:**
- Process 10 findings concurrently
- Prevents rate limiting
- Improves performance

**Structured Outputs:**
- All LLM responses use Pydantic models
- Type-safe parsing
- Validation built-in

**Error Handling:**
- Exponential backoff on failures
- Max 3 retries
- Graceful degradation (low confidence)

## Security Considerations

**Safe by Default:**
- Never deletes files
- Always creates git stash
- Runs tests before accepting patches
- Requires high confidence for auto-fix
- Critical issues need human review

**Guardrails:**
- Syntax validation after patches
- Test suite execution
- LLM patch review
- Revert on verification failure
- Maximum iteration limit

## Performance

**Optimizations:**
- Async LLM calls
- Response caching
- Batch processing
- Skip generated code (node_modules, etc.)
- Configurable severity filters

**Typical Scan Times:**
- Small project (<100 files): 1-2 minutes
- Medium project (100-1000 files): 5-10 minutes
- Large project (>1000 files): 15-30 minutes

## Extensibility

**Adding New Patterns:**
1. Edit `bcb/config/patterns.yaml`
2. Add pattern with regex/AST query
3. Include LLM verification prompt
4. Test with sample code

**Custom Analyzers:**
1. Create new module in `bcb/analyzer/`
2. Implement analysis logic
3. Integrate into CLI workflow

**New Report Formats:**
1. Add method to `ReportGenerator`
2. Implement format-specific logic
3. Add CLI option

## Testing

**Test App:**
- Located in `test_app/`
- Deliberately vulnerable Flask app
- Contains 10+ vulnerability types
- Use for validation and demos

**Manual Testing:**
```bash
# Scan test app
bcb scan test_app --report-only

# Check report
cat test_app/bcb-report.md

# Verify patterns detected
grep -c "CRITICAL" test_app/bcb-report.md
```

## Future Enhancements

**Planned Features:**
1. Tree-sitter AST pattern matching
2. Dependency vulnerability scanning (OSV API)
3. CI/CD integration (GitHub Actions, GitLab CI)
4. Web dashboard for reports
5. Custom rule engine
6. Multi-language support expansion
7. Machine learning for pattern detection
8. Incremental scanning (only changed files)

**Potential Integrations:**
- SAST tools (Semgrep, CodeQL)
- Secret scanners (TruffleHog, GitLeaks)
- Dependency checkers (Snyk, Dependabot)
- IDE plugins (VS Code, JetBrains)

## Dependencies

**Core:**
- typer - CLI framework
- pyyaml - Pattern loading
- aiohttp - Async HTTP
- pydantic - Data validation
- rich - Terminal UI
- gitpython - Git operations

**Optional:**
- tree-sitter - AST parsing (future)
- pytest - Testing
- black/ruff - Code quality

## Configuration

**Environment Variables:**
- `BOB_API_KEY` - IBM Bob API key (required)
- `BOB_API_URL` - API endpoint (optional)
- `BCB_CACHE_DIR` - Cache directory (optional)

**Files:**
- `patterns.yaml` - Vulnerability patterns
- `.gitignore` - Respect in scans
- `.bobignore` - Custom ignore patterns (future)

## Deployment

**Installation:**
```bash
pip install -e .
```

**Usage:**
```bash
export BOB_API_KEY="your-key"
bcb scan /path/to/project
```

**CI/CD:**
```yaml
# GitHub Actions example
- name: Security Audit
  run: |
    pip install bcb
    bcb scan . --report-only --severity critical --severity high
    cat bcb-report.md
```

## License & Credits

Built for IBM Bob Hackathon 2026.
Uses IBM Bob LLM for intelligent code analysis.
