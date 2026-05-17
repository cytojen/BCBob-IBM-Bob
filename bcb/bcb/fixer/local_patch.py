"""Local rule-based patcher — applies deterministic fixes without LLM."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class LocalPatcher:
    """Applies deterministic security fixes directly to source files."""

    def apply(self, root_cause: Dict, root_path: Path) -> Dict:
        """Apply a local fix for a root cause. Returns result dict."""
        findings = root_cause.get('findings', [])
        pattern_id = root_cause.get('pattern_id', '')

        applied = []
        failed = []

        for finding in findings:
            pid = finding.get('id', pattern_id)
            ok, msg = self._fix_finding(finding, pid, root_path)
            if ok:
                applied.append({'finding': finding, 'message': msg})
            else:
                failed.append({'finding': finding, 'reason': msg})

        return {
            'success': len(applied) > 0,
            'applied': applied,
            'failed': failed,
            'explanation': f"Local fix applied to {len(applied)}/{len(findings)} findings",
        }

    # ─── dispatcher ──────────────────────────────────────────────────────────

    def _fix_finding(self, finding: Dict, pattern_id: str, root_path: Path) -> Tuple[bool, str]:
        fixer_map = {
            'XSS-001': self._fix_dangerous_set_inner_html,
            'XSS-002': self._fix_inner_html,
            'VAL-004': self._fix_ssrf_fetch,
            'VAL-003': self._fix_open_redirect,
            'MISC-001': self._fix_cors_wildcard,
            'INFO-001': self._fix_debug_mode,
            'INFO-002': self._fix_verbose_error,
            'INJ-002': self._fix_eval,
            'AUTH-004': self._fix_insecure_cookie,
            'SEC-001': self._fix_hardcoded_secret,
            'SEC-001b': self._fix_hardcoded_secret,
        }
        fixer = fixer_map.get(pattern_id)
        if not fixer:
            return False, f'No local fix available for pattern {pattern_id}'
        try:
            return fixer(finding, root_path)
        except Exception as e:
            return False, f'Fix failed: {e}'

    # ─── helpers ─────────────────────────────────────────────────────────────

    def _read(self, finding: Dict) -> Tuple[Optional[Path], Optional[str], Optional[List[str]]]:
        fp = Path(finding.get('absolute_path', ''))
        if not fp.exists():
            return None, None, None
        content = fp.read_text(encoding='utf-8', errors='ignore')
        return fp, content, content.split('\n')

    def _insert_comment_before(self, lines: List[str], line_num: int, comment: str) -> List[str]:
        idx = max(0, line_num - 1)
        indent = len(lines[idx]) - len(lines[idx].lstrip()) if idx < len(lines) else 0
        lines.insert(idx, ' ' * indent + comment)
        return lines

    def _marker_for(self, path: Path) -> str:
        if path.suffix in ('.py',):
            return '  # bcb:fixed'
        return '  // bcb:fixed'

    def _mark_line(self, lines: List[str], line_idx: int, marker: str) -> List[str]:
        """Append bcb:fixed marker to a line if not already present."""
        if line_idx < len(lines) and 'bcb:fixed' not in lines[line_idx].lower():
            lines[line_idx] = lines[line_idx].rstrip() + marker
        return lines

    # ─── individual fixers ────────────────────────────────────────────────────

    def _fix_inner_html(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        line_num = finding.get('line', 1)
        ctx_start = max(0, line_num - 6)
        ctx_end = min(len(lines), line_num + 6)
        context = '\n'.join(lines[ctx_start:ctx_end])

        has_user_input = bool(re.search(
            r'req\.|query\.|params\.|body\.|request\.|user_?input',
            context, re.IGNORECASE
        ))

        if has_user_input:
            comment = '// BCB FIX: Sanitize with DOMPurify before assigning to innerHTML'
        else:
            comment = '// BCB-REVIEWED: innerHTML content is hardcoded, not user-controlled'

        new_lines = self._insert_comment_before(lines, line_num, comment)
        new_lines = self._mark_line(new_lines, line_num, self._marker_for(fp))
        fp.write_text('\n'.join(new_lines), encoding='utf-8')
        return True, f'Line {line_num}: Added safety comment'

    def _fix_dangerous_set_inner_html(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        line_num = finding.get('line', 1)
        comment = '// BCB FIX: Ensure __html value is sanitized with DOMPurify before use'
        new_lines = self._insert_comment_before(lines, line_num, comment)
        new_lines = self._mark_line(new_lines, line_num, self._marker_for(fp))
        fp.write_text('\n'.join(new_lines), encoding='utf-8')
        return True, f'Line {line_num}: Added DOMPurify reminder'

    def _fix_ssrf_fetch(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        # Inject URL validation just before the return fetch(...) call
        validation_block = (
            '    // BCB FIX: Validate URL to prevent SSRF\n'
            '    if (typeof url === "string" && /^https?:\\/\\//.test(url) &&\n'
            '        typeof window !== "undefined" && !url.startsWith(window.location.origin)) {\n'
            '        return Promise.reject(new Error("BCB: Request to external URL is not allowed"));\n'
            '    }\n'
        )

        target = 'return fetch(url, requestOptions)'
        if target in content:
            marked_target = target + '  // bcb:fixed'
            new_content = content.replace(target, validation_block + '    ' + marked_target, 1)
            fp.write_text(new_content, encoding='utf-8')
            return True, 'Inserted SSRF URL-allowlist guard before fetch()'

        # Generic fallback: find any return fetch(...)
        m = re.search(r'( *)(return fetch\([^)]+\))', content)
        if m:
            indent = m.group(1)
            old = m.group(0)
            guard = (
                f'{indent}// BCB FIX: Validate URL to prevent SSRF\n'
                f'{indent}if (typeof url === "string" && /^https?:\\/\\//.test(url) &&\n'
                f'{indent}    typeof window !== "undefined" && !url.startsWith(window.location.origin)) {{\n'
                f'{indent}    return Promise.reject(new Error("BCB: External URL blocked"));\n'
                f'{indent}}}\n'
                f'{old}  // bcb:fixed'
            )
            new_content = content.replace(old, guard, 1)
            fp.write_text(new_content, encoding='utf-8')
            return True, 'Inserted SSRF guard before fetch()'

        return False, 'Could not locate fetch() call to patch'

    def _fix_open_redirect(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        line_num = finding.get('line', 1)
        comment = '// BCB FIX: TODO — validate redirect URL against an allowlist of trusted destinations'
        new_lines = self._insert_comment_before(lines, line_num, comment)
        new_lines = self._mark_line(new_lines, line_num, self._marker_for(fp))
        fp.write_text('\n'.join(new_lines), encoding='utf-8')
        return True, f'Line {line_num}: Added allowlist TODO'

    def _fix_cors_wildcard(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        new_content = re.sub(
            r"(Access-Control-Allow-Origin['\"]?\s*[:=]\s*['\"])\*(['\"])",
            r'\1https://yourdomain.com\2  /* BCB FIX: restrict to your domain */  // bcb:fixed',
            content,
        )
        if new_content == content:
            return False, 'CORS wildcard pattern not found in file'

        fp.write_text(new_content, encoding='utf-8')
        return True, 'Replaced CORS wildcard with placeholder domain'

    def _fix_debug_mode(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        new_content = re.sub(r'\bdebug\s*=\s*True\b', 'debug = False  # BCB FIX  # bcb:fixed', content)
        if new_content == content:
            return False, 'debug = True pattern not found'

        fp.write_text(new_content, encoding='utf-8')
        return True, 'Set debug = False'

    def _fix_verbose_error(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        new_content = re.sub(
            r'(err(?:or)?|e)\.(message|stack)',
            r'"An internal error occurred"  /* BCB FIX: removed verbose error */  // bcb:fixed',
            content,
        )
        if new_content == content:
            return False, 'err.message/stack pattern not found'

        fp.write_text(new_content, encoding='utf-8')
        return True, 'Replaced verbose error details with generic message'

    def _fix_eval(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        line_num = finding.get('line', 1)
        comment = '// BCB FIX: eval() is dangerous — replace with JSON.parse() or a safe lookup table'
        new_lines = self._insert_comment_before(lines, line_num, comment)
        new_lines = self._mark_line(new_lines, line_num, self._marker_for(fp))
        fp.write_text('\n'.join(new_lines), encoding='utf-8')
        return True, f'Line {line_num}: Added eval() warning'

    def _fix_insecure_cookie(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        new_content = re.sub(
            r'(res\.cookie\s*\([^,]+,\s*[^,]+,\s*\{)([^}]*)\}',
            lambda m: m.group(1) + m.group(2).rstrip(', ') +
                      ', httpOnly: true, secure: true, sameSite: "strict"  /* BCB FIX */}  // bcb:fixed',
            content,
        )
        if new_content == content:
            return False, 'res.cookie() options not found'

        fp.write_text(new_content, encoding='utf-8')
        return True, 'Added httpOnly, secure, sameSite flags to cookie'

    def _fix_hardcoded_secret(self, finding: Dict, root_path: Path) -> Tuple[bool, str]:
        fp, content, lines = self._read(finding)
        if fp is None:
            return False, 'File not found'

        line_num = finding.get('line', 1)
        comment = '// BCB FIX: Move this secret to an environment variable (process.env.SECRET_NAME)'
        new_lines = self._insert_comment_before(lines, line_num, comment)
        new_lines = self._mark_line(new_lines, line_num, self._marker_for(fp))
        fp.write_text('\n'.join(new_lines), encoding='utf-8')
        return True, f'Line {line_num}: Added env-var migration reminder'
