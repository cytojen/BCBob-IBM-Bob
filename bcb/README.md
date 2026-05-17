# BCB (Better Call Bob)

An autonomous CLI tool that audits and repairs codebases produced through "vibe coding" (rapid LLM-assisted development).

## Features

- 🔍 **Root Cause Analysis** - Traces architectural issues, not just symptoms
- 🤖 **LLM-Powered Verification** - Uses IBM Bob for intelligent analysis
- 🔄 **Iterative Repair Loop** - Scans, fixes, and verifies until clean
- 📊 **Comprehensive Reports** - Grouped by root cause, not by file

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Scan and fix a codebase
bcb scan <path>

# Generate report only (no fixes)
bcb scan <path> --report-only

# Fix with custom iteration limit
bcb fix <path> --max-iterations 5

# Verify fixes
bcb verify <path>

# Generate report
bcb report <path> --format markdown
```

## Architecture

BCB uses a multi-phase approach:

1. **Discovery** - Walk codebase, detect languages/frameworks
2. **Architecture Mapping** - Build dependency graph and data flow
3. **Static Pattern Scan** - Apply vulnerability patterns
4. **LLM Verification** - Confirm findings with IBM Bob
5. **Root Cause Clustering** - Group related issues
6. **Repair Phase** - Generate and apply patches
7. **Verification Loop** - Re-scan until clean

## Vulnerability Coverage

- **Critical**: Secrets, SQL injection, auth bypasses
- **High**: CORS misconfig, input validation, SSRF
- **Medium**: Rate limiting, info disclosure
- **Low**: Code quality, architectural smells

## Requirements

- Python 3.11+
- Git (for patch management)
- IBM Bob API access
</content>
</write_to_file>

<write_to_file>
<file_path>C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb\pyproject.toml</file_path>
<content>[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "bcb"
version = "0.1.0"
description = "Better Call Bob - Autonomous codebase security auditor"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    {name = "BCB Team"}
]
dependencies = [
    "typer[all]>=0.9.0",
    "pyyaml>=6.0",
    "tree-sitter>=0.20.0",
    "tree-sitter-python>=0.20.0",
    "tree-sitter-javascript>=0.20.0",
    "aiohttp>=3.9.0",
    "rich>=13.0.0",
    "gitpython>=3.1.0",
    "pydantic>=2.0.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
bcb = "bcb.cli:app"

[tool.setuptools.packages.find]
where = ["."]
include = ["bcb*"]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
</content>
</write_to_file>

<write_to_file>
<file_path>C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb\bcb\__init__.py</file_path>
<content>"""BCB (Better Call Bob) - Autonomous codebase security auditor."""

__version__ = "0.1.0"
