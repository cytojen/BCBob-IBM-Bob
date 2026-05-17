"""Pattern matcher - applies vulnerability patterns to codebase."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import yaml


class PatternMatcher:
    """Matches vulnerability patterns against code."""

    def __init__(self):
        self.patterns = self._load_patterns()
        self._warned_patterns: Set[str] = set()
        
    def _load_patterns(self) -> List[Dict]:
        """Load patterns from patterns.yaml."""
        patterns_file = Path(__file__).parent.parent / 'config' / 'patterns.yaml'
        
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('patterns', [])
        except Exception as e:
            print(f"Warning: Could not load patterns.yaml: {e}")
            return []
    
    def scan(
        self,
        codebase_info: Dict,
        root_path: Path,
        severity_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Scan codebase for vulnerability patterns.
        
        Args:
            codebase_info: Codebase metadata from scanner
            root_path: Root path of codebase
            severity_filter: Optional list of severities to include
            
        Returns:
            List of findings
        """
        findings = []
        
        # Normalize severity filter
        if severity_filter:
            severity_filter = [s.upper() for s in severity_filter]
        
        # Scan each file
        for file_info in codebase_info.get('files', []):
            language = file_info.get('language')
            if not language:
                continue
            
            file_path = Path(file_info['absolute_path'])
            
            # Get applicable patterns for this language
            applicable_patterns = self._get_applicable_patterns(
                language,
                file_info,
                severity_filter
            )
            
            if not applicable_patterns:
                continue
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue
            
            # Apply each pattern
            for pattern in applicable_patterns:
                matches = self._apply_pattern(pattern, content, file_info)
                findings.extend(matches)
        
        # Check for file-level patterns (e.g., .env in git)
        findings.extend(self._check_file_patterns(codebase_info, root_path, severity_filter))
        
        return findings
    
    def _get_applicable_patterns(
        self,
        language: str,
        file_info: Dict,
        severity_filter: Optional[List[str]]
    ) -> List[Dict]:
        """Get patterns applicable to this file."""
        applicable = []
        
        for pattern in self.patterns:
            # Check severity filter
            if severity_filter and pattern.get('severity') not in severity_filter:
                continue
            
            # Check language
            pattern_langs = pattern.get('languages', [])
            if 'all' not in pattern_langs and language not in pattern_langs:
                continue
            
            # Check file patterns (if specified)
            file_patterns = pattern.get('file_patterns', [])
            if file_patterns:
                file_path = file_info.get('path', '')
                if not any(self._matches_glob(file_path, fp) for fp in file_patterns):
                    continue
            
            applicable.append(pattern)
        
        return applicable
    
    def _apply_pattern(
        self,
        pattern: Dict,
        content: str,
        file_info: Dict
    ) -> List[Dict]:
        """Apply a single pattern to content."""
        findings = []
        
        pattern_type = pattern.get('pattern_type', 'regex')
        
        if pattern_type == 'regex':
            findings = self._apply_regex_pattern(pattern, content, file_info)
        elif pattern_type == 'ast':
            # TODO: Implement AST-based pattern matching with tree-sitter
            pass
        elif pattern_type == 'file_check':
            # Handled separately in _check_file_patterns
            pass
        
        return findings
    
    def _apply_regex_pattern(
        self,
        pattern: Dict,
        content: str,
        file_info: Dict
    ) -> List[Dict]:
        """Apply regex pattern to content."""
        findings = []
        
        regex = pattern.get('pattern')
        if not regex:
            return findings
        
        try:
            # Compile regex
            compiled = re.compile(regex, re.MULTILINE | re.IGNORECASE)

            # Pre-split for line lookup
            lines = content.split('\n')

            # Find all matches
            for match in compiled.finditer(content):
                # Get line number
                line_num = content[:match.start()].count('\n') + 1

                # Skip lines already marked as fixed by BCB
                matched_line = lines[line_num - 1] if line_num <= len(lines) else ''
                if 'bcb:fixed' in matched_line.lower():
                    continue

                # Get context (3 lines before and after)
                start_line = max(0, line_num - 4)
                end_line = min(len(lines), line_num + 3)
                context_lines = lines[start_line:end_line]
                context = '\n'.join(context_lines)
                
                # Get matched text
                matched_text = match.group(0)
                
                # Create finding
                finding = {
                    'id': pattern.get('id'),
                    'name': pattern.get('name'),
                    'severity': pattern.get('severity'),
                    'cwe': pattern.get('cwe'),
                    'description': pattern.get('description'),
                    'file_path': file_info.get('path'),
                    'absolute_path': file_info.get('absolute_path'),
                    'line': line_num,
                    'matched_text': matched_text[:200],  # Limit length
                    'context': context,
                    'fix_template': pattern.get('fix_template'),
                    'llm_prompt': pattern.get('llm_prompt'),
                    'confidence': 0.5,  # Initial confidence, will be updated by LLM
                    'verified': False,
                }
                
                findings.append(finding)
                
        except re.error as e:
            pid = pattern.get('id', '?')
            if pid not in self._warned_patterns:
                self._warned_patterns.add(pid)
                print(f"Warning: Invalid regex in pattern {pid}: {e}")
        
        return findings
    
    def _check_file_patterns(
        self,
        codebase_info: Dict,
        root_path: Path,
        severity_filter: Optional[List[str]]
    ) -> List[Dict]:
        """Check file-level patterns (e.g., .env in git)."""
        findings = []
        
        for pattern in self.patterns:
            if pattern.get('pattern_type') != 'file_check':
                continue
            
            # Check severity filter
            if severity_filter and pattern.get('severity') not in severity_filter:
                continue
            
            # Check for .env files
            if pattern.get('id') == 'SEC-005':
                findings.extend(self._check_env_in_git(pattern, codebase_info, root_path))
        
        return findings
    
    def _check_env_in_git(
        self,
        pattern: Dict,
        codebase_info: Dict,
        root_path: Path
    ) -> List[Dict]:
        """Check if .env files are tracked in git."""
        findings = []
        
        if not codebase_info.get('has_git'):
            return findings
        
        gitignore_patterns = codebase_info.get('gitignore_patterns', [])
        
        # Check if .env is in gitignore
        env_ignored = any('.env' in p for p in gitignore_patterns)
        
        # Find .env files
        for file_info in codebase_info.get('files', []):
            if '.env' in file_info.get('name', ''):
                # Check if file is tracked in git
                file_path = Path(file_info['absolute_path'])
                
                # If .env is not in gitignore, it's likely tracked
                if not env_ignored:
                    finding = {
                        'id': pattern.get('id'),
                        'name': pattern.get('name'),
                        'severity': pattern.get('severity'),
                        'cwe': pattern.get('cwe'),
                        'description': pattern.get('description'),
                        'file_path': file_info.get('path'),
                        'absolute_path': file_info.get('absolute_path'),
                        'line': 1,
                        'matched_text': '.env file',
                        'context': f'.env file found and not in .gitignore',
                        'fix_template': pattern.get('fix_template'),
                        'llm_prompt': pattern.get('llm_prompt'),
                        'confidence': 0.8,
                        'verified': False,
                        'metadata': {
                            'in_gitignore': env_ignored,
                        }
                    }
                    findings.append(finding)
        
        return findings
    
    def _matches_glob(self, path: str, glob_pattern: str) -> bool:
        """Check if path matches glob pattern (cross-platform)."""
        import fnmatch
        # Normalize to forward slashes so patterns work on Windows too
        normalized = path.replace('\\', '/')
        return fnmatch.fnmatch(normalized, glob_pattern)
    
    def get_pattern_by_id(self, pattern_id: str) -> Optional[Dict]:
        """Get pattern by ID."""
        for pattern in self.patterns:
            if pattern.get('id') == pattern_id:
                return pattern
        return None
    
    def get_patterns_by_severity(self, severity: str) -> List[Dict]:
        """Get all patterns of a given severity."""
        severity = severity.upper()
        return [p for p in self.patterns if p.get('severity') == severity]
    
    def get_patterns_by_cwe(self, cwe: str) -> List[Dict]:
        """Get all patterns for a given CWE."""
        return [p for p in self.patterns if p.get('cwe') == cwe]
