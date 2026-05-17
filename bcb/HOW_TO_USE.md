# How to Use BCB on Your Own App

## Complete Step-by-Step Guide

### Prerequisites

1. **Python 3.11+** installed
2. **Git** installed (for patch management)
3. **IBM Bob API Key** (required for LLM features)

---

## Step 1: Install BCB

```bash
# Navigate to BCB directory
cd "C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb"

# Install BCB and dependencies
py -m pip install -e .
```

**Expected output:** `Successfully installed bcb-0.1.0`

---

## Step 2: Set Up API Key

```bash
# Windows PowerShell
$env:BOB_API_KEY = "your-actual-ibm-bob-api-key"

# Or Windows CMD
set BOB_API_KEY=your-actual-ibm-bob-api-key

# Or add to your environment variables permanently:
# System Properties > Environment Variables > New
# Variable name: BOB_API_KEY
# Variable value: your-actual-ibm-bob-api-key
```

**Verify it's set:**
```bash
echo $env:BOB_API_KEY
```

---

## Step 3: Navigate to Your App

```bash
# Go to your vibe-coded app directory
cd "C:\path\to\your\app"

# Make sure it's a git repository (BCB uses git for safety)
git init  # if not already a git repo
git add .
git commit -m "Before BCB scan"  # commit your current state
```

---

## Step 4: Run Initial Scan (Report Only)

```bash
# Run BCB scan without making any changes
py "C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb\run_bcb.py" scan . --report-only
```

**What happens:**
1. 🔍 Discovers your codebase structure
2. 🏗️ Maps architecture (API endpoints, auth flow, etc.)
3. 🔎 Scans for vulnerability patterns
4. 🤖 Verifies findings with IBM Bob LLM
5. 🎯 Clusters issues into root causes
6. 📄 Generates `bcb-report.md` in your app directory

**Time:** 1-5 minutes depending on codebase size

---

## Step 5: Review the Report

```bash
# Open the generated report
notepad bcb-report.md

# Or view in terminal
type bcb-report.md
```

**What to look for:**
- **Executive Summary** - Severity breakdown
- **Production Readiness** - ✅ Ready / ⚠️ Needs Review / ❌ Not Ready
- **Root Causes** - Architectural issues (not just symptoms)
- **Detailed Findings** - Individual vulnerabilities with code snippets
- **Needs Human Review** - Critical issues or low-confidence findings

---

## Step 6: Understand the Findings

The report groups issues by **root cause**, not by file. For example:

**Instead of:**
- SQL injection in file1.py line 42
- SQL injection in file2.py line 89
- SQL injection in file3.py line 156

**You get:**
- **Root Cause RC-001:** Missing parameterized query helper
  - Affects 3 files
  - Fix: Create a database utility module with safe query methods

---

## Step 7: Decide on Auto-Fix vs Manual Fix

**Auto-fix is safe for:**
- ✅ High confidence findings (>0.7)
- ✅ HIGH and MEDIUM severity
- ✅ Well-understood patterns (hardcoded secrets, SQL injection)

**Manual review required for:**
- ⚠️ CRITICAL severity (always needs review)
- ⚠️ Low confidence (<0.6)
- ⚠️ Complex architectural changes
- ⚠️ Business logic decisions

---

## Step 8: Run Auto-Fix (Optional)

```bash
# BCB will automatically fix issues iteratively
py "C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb\run_bcb.py" scan . --max-iterations 5
```

**What happens:**
1. 🔒 Creates git stash (your code is safe!)
2. 🔧 Generates patches for each root cause
3. ✅ Applies patch
4. 🧪 Verifies syntax and runs tests
5. 🔄 Re-scans to check for new issues
6. 🔁 Repeats until clean or max iterations

**Safety features:**
- Git stash created before any changes
- Syntax validation after each patch
- Test suite execution (if you have tests)
- Automatic revert if verification fails
- Maximum iteration limit (default: 5)

**Time:** 5-15 minutes depending on issues found

---

## Step 9: Review Applied Changes

```bash
# See what BCB changed
git diff

# Or use your favorite diff tool
git difftool

# Check the updated report
type bcb-report.md
```

**Look for:**
- Files modified
- Lines changed
- New code added (e.g., environment variable usage)
- Removed code (e.g., hardcoded secrets)

---

## Step 10: Test Your App

```bash
# Run your test suite
pytest  # or npm test, or whatever you use

# Manually test critical functionality
# - Authentication
# - Database operations
# - API endpoints
# - File uploads
```

**If tests fail:**
```bash
# Revert BCB changes
git stash pop  # restores your original code

# Or review specific changes
git checkout -- path/to/file.py  # revert specific file
```

---

## Step 11: Handle "Needs Human Review" Items

Open `bcb-report.md` and find the "Needs Human Review" section.

**For each item:**

1. **Read the reasoning** - Why does it need review?
2. **Check the code** - Navigate to the file and line
3. **Understand the context** - Is it a real issue?
4. **Make a decision:**
   - Fix manually
   - Accept the risk (document why)
   - Refactor the architecture

**Example:**
```
RC-003: Client-side authentication checks (CRITICAL)
- Confidence: 0.85
- Needs review: Critical severity
- Files: src/components/AdminPanel.jsx

Decision: Add backend authentication middleware
```

---

## Step 12: Iterate if Needed

If BCB didn't fix everything (or you reverted some changes):

```bash
# Run another scan
py "C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb\run_bcb.py" scan . --report-only

# Check remaining issues
type bcb-report.md
```

**Common reasons for remaining issues:**
- Low confidence (BCB won't auto-fix)
- Critical severity (requires human review)
- Complex architectural changes
- Business logic decisions

---

## Step 13: Commit Your Changes

```bash
# Review all changes one more time
git diff

# Stage the changes
git add .

# Commit with descriptive message
git commit -m "Security fixes from BCB scan

- Fixed SQL injection vulnerabilities (parameterized queries)
- Moved hardcoded secrets to environment variables
- Added authentication middleware to API routes
- Disabled debug mode for production

BCB Report: bcb-report.md"
```

---

## Step 14: Final Verification

```bash
# Run one final scan to confirm
py "C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb\run_bcb.py" verify .

# Check production readiness
type bcb-report.md | findstr "Production readiness"
```

**Expected output:**
```
Production readiness: ✅ READY
```

Or:
```
Production readiness: ⚠️ NEEDS_REVIEW
```

---

## Advanced Usage

### Scan Only Specific Severity

```bash
# Only critical and high severity
py run_bcb.py scan . --severity critical --severity high --report-only
```

### Custom Iteration Limit

```bash
# More iterations for complex codebases
py run_bcb.py scan . --max-iterations 10
```

### Dry Run (See What Would Be Fixed)

```bash
py run_bcb.py fix . --dry-run
```

### Generate Different Report Formats

```bash
# JSON for CI/CD
py run_bcb.py report . --format json --output report.json

# HTML for viewing in browser
py run_bcb.py report . --format html --output report.html
```

---

## Troubleshooting

### "No module named 'bcb'"
```bash
# Reinstall BCB
cd "C:\Users\hikme\Desktop\Programming Projects\Hackathon Projects\IBM Bob Hackathon\bcb"
py -m pip install -e .
```

### "BOB_API_KEY not set"
```bash
# Set the environment variable
$env:BOB_API_KEY = "your-key"
```

### "Git not found"
```bash
# Install git from https://git-scm.com/
# Or use GitHub Desktop
```

### Scan Takes Too Long
```bash
# Use severity filter
py run_bcb.py scan . --severity critical --severity high --report-only
```

### Too Many False Positives
- Check confidence scores in report
- Low confidence findings are marked for review
- BCB won't auto-fix low confidence issues

### Patches Break Tests
```bash
# Revert changes
git stash pop

# Review the patch manually
# Fix the issue yourself
# Or adjust the code and re-run BCB
```

---

## Best Practices

1. **Always commit before scanning** - BCB creates stashes, but commit first
2. **Start with --report-only** - Review before auto-fixing
3. **Use severity filters** - Focus on critical/high first
4. **Review "Needs Human Review"** - Don't ignore these
5. **Test after fixes** - Run your test suite
6. **Iterate** - BCB may need multiple passes
7. **Document decisions** - Why you accepted certain risks
8. **Keep BCB updated** - New patterns are added regularly

---

## Example Complete Workflow

```bash
# 1. Setup
cd "C:\path\to\your\app"
git add . && git commit -m "Before BCB"
$env:BOB_API_KEY = "your-key"

# 2. Initial scan
py "C:\...\bcb\run_bcb.py" scan . --report-only

# 3. Review report
notepad bcb-report.md

# 4. Auto-fix safe issues
py "C:\...\bcb\run_bcb.py" scan . --severity high --severity medium

# 5. Test
pytest

# 6. Review changes
git diff

# 7. Manual fixes for critical issues
# (edit files as needed)

# 8. Final scan
py "C:\...\bcb\run_bcb.py" verify .

# 9. Commit
git add . && git commit -m "Security fixes from BCB"
```

---

## What to Expect

**Small app (<100 files):**
- Scan: 1-2 minutes
- Auto-fix: 3-5 minutes
- Total: ~10 minutes

**Medium app (100-1000 files):**
- Scan: 5-10 minutes
- Auto-fix: 10-20 minutes
- Total: ~30 minutes

**Large app (>1000 files):**
- Scan: 15-30 minutes
- Auto-fix: 30-60 minutes
- Total: ~1-2 hours

**Typical findings:**
- 5-20 issues in small apps
- 20-100 issues in medium apps
- 100+ issues in large apps
- 3-10 root causes typically

---

## Success Criteria

Your app is ready when:
- ✅ Production readiness: READY or NEEDS_REVIEW
- ✅ 0 CRITICAL issues remaining
- ✅ 0 HIGH issues remaining (or documented exceptions)
- ✅ All tests passing
- ✅ Manual review completed for flagged items
- ✅ Changes committed to git

---

## Getting Help

If you encounter issues:
1. Check QUICKSTART.md for common problems
2. Review ARCHITECTURE.md for technical details
3. Check the patterns.yaml file for pattern definitions
4. Test with the sample test_app first
5. Adjust confidence thresholds if needed

---

## Summary

**The complete flow:**
1. Install BCB → 2. Set API key → 3. Navigate to app → 4. Commit code → 5. Scan (report-only) → 6. Review report → 7. Auto-fix (optional) → 8. Test → 9. Manual fixes → 10. Final scan → 11. Commit

**Time investment:** 30 minutes to 2 hours depending on app size

**Result:** Production-ready codebase with security issues fixed! 🎉
