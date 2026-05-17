# BCB Quick Start Guide

## Installation

1. **Install BCB:**
```bash
cd bcb
pip install -e .
```

2. **Set up IBM Bob API credentials:**
```bash
# Set your IBM Bob API key
export BOB_API_KEY="your-api-key-here"

# Optional: Set custom API URL
export BOB_API_URL="https://api.bob.build/v1"
```

## Basic Usage

### Scan a Codebase

```bash
# Scan and generate report (no fixes)
bcb scan /path/to/project --report-only

# Scan and auto-fix issues
bcb scan /path/to/project

# Scan only critical and high severity
bcb scan /path/to/project --severity critical --severity high

# Custom output location
bcb scan /path/to/project --output /path/to/report.md
```

### Test with Sample Vulnerable App

We've included a deliberately vulnerable Flask app for testing:

```bash
# Navigate to test app
cd test_app

# Install dependencies
pip install -r requirements.txt

# Scan the vulnerable app
cd ..
bcb scan test_app --report-only

# View the report
cat test_app/bcb-report.md
```

The test app contains:
- ✗ Hardcoded secrets (API keys, passwords)
- ✗ SQL injection vulnerabilities
- ✗ XSS vulnerabilities
- ✗ Command injection
- ✗ Open redirect
- ✗ SSRF vulnerability
- ✗ Missing authentication
- ✗ Mass assignment
- ✗ Unrestricted file upload
- ✗ Debug mode enabled

### Scan and Fix

```bash
# Scan and automatically fix issues
bcb scan test_app

# This will:
# 1. Discover vulnerabilities
# 2. Verify with IBM Bob LLM
# 3. Cluster into root causes
# 4. Generate patches
# 5. Apply and verify fixes
# 6. Iterate until clean or max iterations
```

### Advanced Options

```bash
# Dry run (show what would be fixed)
bcb fix /path/to/project --dry-run

# Custom iteration limit
bcb scan /path/to/project --max-iterations 10

# Generate different report formats
bcb report /path/to/project --format json
bcb report /path/to/project --format html

# Verify fixes after manual changes
bcb verify /path/to/project
```

## Understanding the Report

BCB generates a comprehensive markdown report with:

### Executive Summary
- Severity breakdown (Critical, High, Medium, Low)
- Production readiness assessment
- Fix statistics

### Root Causes
- Architectural issues causing multiple symptoms
- Fix strategies
- Affected files

### Detailed Findings
- Individual vulnerabilities
- CWE mappings
- Code snippets
- Fix recommendations

### Iteration Log
- What was fixed in each iteration
- Remaining issues
- Failed fixes

### Needs Human Review
- Low-confidence findings
- Critical issues requiring manual review
- Complex architectural decisions

## Configuration

### Custom Patterns

Add custom vulnerability patterns to `bcb/config/patterns.yaml`:

```yaml
patterns:
  - id: CUSTOM-001
    name: Custom Vulnerability
    severity: HIGH
    cwe: CWE-XXX
    languages: [python, javascript]
    pattern_type: regex
    pattern: 'your-regex-pattern'
    description: "Description of the vulnerability"
    fix_template: "How to fix it"
    llm_prompt: |
      Prompt for IBM Bob to verify this finding
```

### Environment Variables

- `BOB_API_KEY` - IBM Bob API key (required)
- `BOB_API_URL` - API endpoint (optional)
- `BCB_CACHE_DIR` - Cache directory (optional, defaults to ~/.bcb/cache)

## Troubleshooting

### "No module named 'bcb'"
```bash
# Make sure you installed in editable mode
pip install -e .
```

### "BOB_API_KEY not set"
```bash
# Set your API key
export BOB_API_KEY="your-key"
```

### "Git not found"
```bash
# BCB requires git for patch management
# Install git for your platform
```

### Scan takes too long
```bash
# Use severity filter to focus on critical issues
bcb scan /path/to/project --severity critical --severity high
```

### False positives
BCB uses IBM Bob LLM to verify findings and reduce false positives. If you still see false positives:
- Check the confidence score in the report
- Low confidence findings are marked for human review
- You can adjust the confidence threshold in the code

## Best Practices

1. **Always review before auto-fix**: Use `--report-only` first
2. **Start with high severity**: Use `--severity critical --severity high`
3. **Commit before scanning**: BCB creates git stashes, but commit your work first
4. **Review the report**: Check "Needs Human Review" section
5. **Test after fixes**: Run your test suite after BCB applies patches
6. **Iterate**: BCB may need multiple passes for complex codebases

## Examples

### Scan a React/Node.js project
```bash
bcb scan my-react-app --severity critical --severity high
```

### Scan a Python/Flask project
```bash
bcb scan my-flask-app --report-only
```

### Scan and fix with custom iterations
```bash
bcb scan my-project --max-iterations 3
```

### Generate JSON report for CI/CD
```bash
bcb scan my-project --report-only
bcb report my-project --format json --output report.json
```

## Next Steps

- Read the full documentation in README.md
- Explore the patterns.yaml file
- Customize for your tech stack
- Integrate into CI/CD pipeline
- Contribute new patterns

## Support

For issues, questions, or contributions:
- Check the documentation
- Review existing patterns
- Test with the sample vulnerable app
- Adjust confidence thresholds as needed
