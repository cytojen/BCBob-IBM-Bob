"""Codebase scanner - walks directory tree and builds codebase model."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
import yaml
from collections import defaultdict

from bcb.scanner.patterns import PatternMatcher
from bcb.scanner.architecture import ArchitectureMapper


class CodebaseScanner:
    """Scans and analyzes codebase structure."""
    
    # Files/dirs to always skip
    SKIP_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
        'dist', 'build', '.next', 'target', 'vendor', '.idea', '.vscode',
        'coverage', '.pytest_cache', '.mypy_cache', 'out', 'bin', 'obj',
    }
    
    SKIP_FILES = {
        '.DS_Store', 'Thumbs.db', '.gitignore', '.dockerignore',
        'package-lock.json', 'yarn.lock', 'poetry.lock', 'Cargo.lock',
    }
    
    # Language detection by extension
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.rs': 'rust',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cs': 'csharp',
        '.swift': 'swift',
        '.kt': 'kotlin',
    }
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        'react': [
            r'import.*from\s+["\']react["\']',
            r'<.*/>',  # JSX
        ],
        'vue': [
            r'import.*from\s+["\']vue["\']',
            r'<template>',
        ],
        'angular': [
            r'@angular/',
            r'@Component\(',
        ],
        'express': [
            r'require\(["\']express["\']\)',
            r'import.*from\s+["\']express["\']',
        ],
        'flask': [
            r'from flask import',
            r'Flask\(__name__\)',
        ],
        'django': [
            r'from django',
            r'django\.conf',
        ],
        'fastapi': [
            r'from fastapi import',
            r'FastAPI\(',
        ],
        'spring': [
            r'@SpringBootApplication',
            r'org\.springframework',
        ],
        'nextjs': [
            r'next/.*',
            r'getServerSideProps',
        ],
    }
    
    def __init__(self, root_path: Path):
        """Initialize scanner with root path."""
        self.root_path = root_path.resolve()
        self.pattern_matcher = PatternMatcher()
        self.architecture_mapper = ArchitectureMapper()
        
    def scan(self) -> Dict:
        """
        Scan codebase and return comprehensive information.
        
        Returns:
            Dict with codebase metadata, file list, languages, frameworks, etc.
        """
        codebase_info = {
            'root_path': str(self.root_path),
            'files': [],
            'total_files': 0,
            'total_loc': 0,
            'languages': set(),
            'frameworks': set(),
            'entry_points': [],
            'config_files': [],
            'dependencies': {},
            'gitignore_patterns': [],
            'has_git': False,
        }
        
        # Check for git
        if (self.root_path / '.git').exists():
            codebase_info['has_git'] = True
            codebase_info['gitignore_patterns'] = self._load_gitignore()
        
        # Walk directory tree
        for root, dirs, files in os.walk(self.root_path):
            # Filter out skip directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            
            root_path = Path(root)
            
            for filename in files:
                if filename in self.SKIP_FILES:
                    continue
                    
                file_path = root_path / filename
                rel_path = file_path.relative_to(self.root_path)
                
                # Get file info
                file_info = self._analyze_file(file_path, rel_path)
                if file_info:
                    codebase_info['files'].append(file_info)
                    codebase_info['total_files'] += 1
                    codebase_info['total_loc'] += file_info.get('loc', 0)
                    
                    if file_info.get('language'):
                        codebase_info['languages'].add(file_info['language'])
                    
                    # Detect entry points
                    if self._is_entry_point(file_path, filename):
                        codebase_info['entry_points'].append(str(rel_path))
                    
                    # Detect config files
                    if self._is_config_file(filename):
                        codebase_info['config_files'].append(str(rel_path))
        
        # Convert sets to lists for JSON serialization
        codebase_info['languages'] = sorted(list(codebase_info['languages']))
        
        # Detect frameworks
        codebase_info['frameworks'] = self._detect_frameworks(codebase_info['files'])
        
        # Load dependencies
        codebase_info['dependencies'] = self._load_dependencies()
        
        return codebase_info
    
    def map_architecture(self, codebase_info: Dict) -> Dict:
        """
        Map codebase architecture.
        
        Args:
            codebase_info: Output from scan()
            
        Returns:
            Architecture mapping with dependencies, data flow, trust boundaries
        """
        return self.architecture_mapper.map(codebase_info, self.root_path)
    
    def scan_patterns(
        self,
        codebase_info: Dict,
        severity_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Scan for vulnerability patterns.
        
        Args:
            codebase_info: Output from scan()
            severity_filter: Optional list of severities to include
            
        Returns:
            List of findings
        """
        return self.pattern_matcher.scan(
            codebase_info,
            self.root_path,
            severity_filter
        )
    
    def _analyze_file(self, file_path: Path, rel_path: Path) -> Optional[Dict]:
        """Analyze a single file."""
        try:
            # Get file stats
            stats = file_path.stat()
            
            # Detect language
            language = self.LANGUAGE_MAP.get(file_path.suffix)
            
            # Count lines for text files
            loc = 0
            if language:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        loc = sum(1 for line in f if line.strip())
                except Exception:
                    pass
            
            return {
                'path': str(rel_path),
                'absolute_path': str(file_path),
                'name': file_path.name,
                'extension': file_path.suffix,
                'language': language,
                'size': stats.st_size,
                'loc': loc,
                'modified': stats.st_mtime,
            }
        except Exception as e:
            # Skip files we can't read
            return None
    
    def _is_entry_point(self, file_path: Path, filename: str) -> bool:
        """Check if file is an entry point."""
        entry_point_names = {
            'main.py', 'app.py', '__main__.py', 'manage.py',
            'index.js', 'index.ts', 'server.js', 'server.ts',
            'main.go', 'main.java', 'Main.java',
            'index.html', 'index.php',
        }
        
        if filename in entry_point_names:
            return True
        
        # Check for main function in Python
        if file_path.suffix == '.py':
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)  # First 5KB
                    if 'if __name__ == "__main__"' in content:
                        return True
            except Exception:
                pass
        
        return False
    
    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file."""
        config_patterns = [
            r'.*\.config\.(js|ts|json)$',
            r'.*\.conf$',
            r'.*\.ini$',
            r'.*\.yaml$',
            r'.*\.yml$',
            r'.*\.toml$',
            r'.*\.env.*',
            r'package\.json$',
            r'requirements\.txt$',
            r'Pipfile$',
            r'pyproject\.toml$',
            r'Cargo\.toml$',
            r'go\.mod$',
            r'pom\.xml$',
            r'build\.gradle$',
        ]
        
        for pattern in config_patterns:
            if re.match(pattern, filename):
                return True
        
        return False
    
    def _detect_frameworks(self, files: List[Dict]) -> List[str]:
        """Detect frameworks used in codebase."""
        frameworks = set()
        
        for file_info in files:
            if not file_info.get('language'):
                continue
            
            try:
                file_path = Path(file_info['absolute_path'])
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10000)  # First 10KB
                    
                    for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                        for pattern in patterns:
                            if re.search(pattern, content):
                                frameworks.add(framework)
                                break
            except Exception:
                continue
        
        return sorted(list(frameworks))
    
    def _load_gitignore(self) -> List[str]:
        """Load .gitignore patterns."""
        gitignore_path = self.root_path / '.gitignore'
        patterns = []
        
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.append(line)
            except Exception:
                pass
        
        return patterns
    
    def _load_dependencies(self) -> Dict[str, List[str]]:
        """Load project dependencies from various package managers."""
        dependencies = {}
        
        # Python - requirements.txt
        req_file = self.root_path / 'requirements.txt'
        if req_file.exists():
            dependencies['python'] = self._parse_requirements(req_file)
        
        # Python - pyproject.toml
        pyproject = self.root_path / 'pyproject.toml'
        if pyproject.exists():
            dependencies['python'] = self._parse_pyproject(pyproject)
        
        # JavaScript/TypeScript - package.json
        package_json = self.root_path / 'package.json'
        if package_json.exists():
            dependencies['javascript'] = self._parse_package_json(package_json)
        
        # Go - go.mod
        go_mod = self.root_path / 'go.mod'
        if go_mod.exists():
            dependencies['go'] = self._parse_go_mod(go_mod)
        
        return dependencies
    
    def _parse_requirements(self, file_path: Path) -> List[str]:
        """Parse requirements.txt."""
        deps = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before ==, >=, etc.)
                        pkg = re.split(r'[=<>!]', line)[0].strip()
                        if pkg:
                            deps.append(pkg)
        except Exception:
            pass
        return deps
    
    def _parse_pyproject(self, file_path: Path) -> List[str]:
        """Parse pyproject.toml."""
        deps = []
        try:
            import tomli
            with open(file_path, 'rb') as f:
                data = tomli.load(f)
                if 'project' in data and 'dependencies' in data['project']:
                    for dep in data['project']['dependencies']:
                        pkg = re.split(r'[=<>!]', dep)[0].strip()
                        if pkg:
                            deps.append(pkg)
        except Exception:
            pass
        return deps
    
    def _parse_package_json(self, file_path: Path) -> List[str]:
        """Parse package.json."""
        deps = []
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for dep_type in ['dependencies', 'devDependencies']:
                    if dep_type in data:
                        deps.extend(data[dep_type].keys())
        except Exception:
            pass
        return deps
    
    def _parse_go_mod(self, file_path: Path) -> List[str]:
        """Parse go.mod."""
        deps = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                in_require = False
                for line in f:
                    line = line.strip()
                    if line.startswith('require'):
                        in_require = True
                        continue
                    if in_require:
                        if line == ')':
                            break
                        if line:
                            pkg = line.split()[0]
                            deps.append(pkg)
        except Exception:
            pass
        return deps
