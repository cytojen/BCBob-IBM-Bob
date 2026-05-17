"""Architecture mapper - analyzes codebase structure and data flow."""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict


class ArchitectureMapper:
    """Maps codebase architecture including dependencies and data flow."""
    
    def __init__(self):
        """Initialize architecture mapper."""
        pass
    
    def map(self, codebase_info: Dict, root_path: Path) -> Dict:
        """
        Map codebase architecture.
        
        Args:
            codebase_info: Codebase metadata from scanner
            root_path: Root path of codebase
            
        Returns:
            Architecture mapping
        """
        architecture = {
            'module_graph': {},
            'data_flow': [],
            'trust_boundaries': [],
            'auth_flow': [],
            'entry_points': codebase_info.get('entry_points', []),
            'api_endpoints': [],
            'database_access': [],
            'external_calls': [],
            'state_management': {},
        }
        
        # Build module dependency graph
        architecture['module_graph'] = self._build_module_graph(codebase_info)
        
        # Identify API endpoints
        architecture['api_endpoints'] = self._identify_api_endpoints(codebase_info, root_path)
        
        # Identify trust boundaries
        architecture['trust_boundaries'] = self._identify_trust_boundaries(
            codebase_info,
            architecture['api_endpoints']
        )
        
        # Identify database access patterns
        architecture['database_access'] = self._identify_database_access(codebase_info, root_path)
        
        # Identify external API calls
        architecture['external_calls'] = self._identify_external_calls(codebase_info, root_path)
        
        # Analyze auth flow
        architecture['auth_flow'] = self._analyze_auth_flow(codebase_info, root_path)
        
        # Analyze state management
        architecture['state_management'] = self._analyze_state_management(codebase_info, root_path)
        
        return architecture
    
    def _build_module_graph(self, codebase_info: Dict) -> Dict[str, List[str]]:
        """Build module dependency graph."""
        graph = defaultdict(list)
        
        for file_info in codebase_info.get('files', []):
            language = file_info.get('language')
            if not language:
                continue
            
            file_path = Path(file_info['absolute_path'])
            module_name = file_info.get('path')
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Extract imports based on language
                imports = self._extract_imports(content, language)
                graph[module_name] = imports
                
            except Exception:
                continue
        
        return dict(graph)
    
    def _extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements from code."""
        imports = []
        
        if language == 'python':
            # Python imports
            patterns = [
                r'from\s+([\w.]+)\s+import',
                r'import\s+([\w.]+)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
        
        elif language in ['javascript', 'typescript']:
            # JavaScript/TypeScript imports
            patterns = [
                r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
                r'require\(["\']([^"\']+)["\']\)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
        
        elif language == 'java':
            # Java imports
            pattern = r'import\s+([\w.]+);'
            matches = re.findall(pattern, content)
            imports.extend(matches)
        
        elif language == 'go':
            # Go imports
            pattern = r'import\s+["\']([^"\']+)["\']'
            matches = re.findall(pattern, content)
            imports.extend(matches)
        
        return imports
    
    def _identify_api_endpoints(self, codebase_info: Dict, root_path: Path) -> List[Dict]:
        """Identify API endpoints in the codebase."""
        endpoints = []
        
        # Patterns for different frameworks
        endpoint_patterns = {
            'express': [
                (r'app\.(get|post|put|delete|patch)\s*\(["\']([^"\']+)["\']', 'javascript'),
                (r'router\.(get|post|put|delete|patch)\s*\(["\']([^"\']+)["\']', 'javascript'),
            ],
            'flask': [
                (r'@app\.route\(["\']([^"\']+)["\'].*methods\s*=\s*\[([^\]]+)\]', 'python'),
                (r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'python'),
            ],
            'fastapi': [
                (r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'python'),
            ],
            'django': [
                (r'path\(["\']([^"\']+)["\']', 'python'),
            ],
            'spring': [
                (r'@(Get|Post|Put|Delete|Patch)Mapping\(["\']([^"\']+)["\']', 'java'),
            ],
        }
        
        for file_info in codebase_info.get('files', []):
            language = file_info.get('language')
            if not language:
                continue
            
            file_path = Path(file_info['absolute_path'])
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Try each framework's patterns
                for framework, patterns in endpoint_patterns.items():
                    for pattern, lang in patterns:
                        if language != lang:
                            continue
                        
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            method = match.group(1).upper() if len(match.groups()) > 1 else 'GET'
                            path = match.group(2) if len(match.groups()) > 1 else match.group(1)
                            
                            endpoint = {
                                'method': method,
                                'path': path,
                                'file': file_info.get('path'),
                                'line': content[:match.start()].count('\n') + 1,
                                'framework': framework,
                            }
                            endpoints.append(endpoint)
            
            except Exception:
                continue
        
        return endpoints
    
    def _identify_trust_boundaries(
        self,
        codebase_info: Dict,
        api_endpoints: List[Dict]
    ) -> List[Dict]:
        """Identify trust boundaries where untrusted data enters."""
        boundaries = []
        
        # API endpoints are trust boundaries
        for endpoint in api_endpoints:
            boundaries.append({
                'type': 'api_endpoint',
                'location': f"{endpoint['file']}:{endpoint['line']}",
                'description': f"{endpoint['method']} {endpoint['path']}",
                'risk': 'high',
            })
        
        # File uploads
        for file_info in codebase_info.get('files', []):
            if not file_info.get('language'):
                continue
            
            try:
                file_path = Path(file_info['absolute_path'])
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for file upload patterns
                upload_patterns = [
                    r'multer\(',
                    r'FileUpload',
                    r'upload\.single',
                    r'request\.files',
                ]
                
                for pattern in upload_patterns:
                    if re.search(pattern, content):
                        boundaries.append({
                            'type': 'file_upload',
                            'location': file_info.get('path'),
                            'description': 'File upload handler',
                            'risk': 'high',
                        })
                        break
            
            except Exception:
                continue
        
        return boundaries
    
    def _identify_database_access(self, codebase_info: Dict, root_path: Path) -> List[Dict]:
        """Identify database access patterns."""
        db_access = []
        
        db_patterns = {
            'sql': [
                r'execute\s*\(',
                r'query\s*\(',
                r'cursor\.',
                r'SELECT\s+',
                r'INSERT\s+INTO',
                r'UPDATE\s+',
                r'DELETE\s+FROM',
            ],
            'mongodb': [
                r'\.find\(',
                r'\.findOne\(',
                r'\.insert\(',
                r'\.update\(',
                r'\.remove\(',
                r'db\.collection',
            ],
            'orm': [
                r'Model\.objects',
                r'\.filter\(',
                r'\.get\(',
                r'\.create\(',
                r'\.save\(',
            ],
        }
        
        for file_info in codebase_info.get('files', []):
            if not file_info.get('language'):
                continue
            
            try:
                file_path = Path(file_info['absolute_path'])
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for db_type, patterns in db_patterns.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            db_access.append({
                                'type': db_type,
                                'file': file_info.get('path'),
                                'line': content[:match.start()].count('\n') + 1,
                                'pattern': pattern,
                            })
            
            except Exception:
                continue
        
        return db_access
    
    def _identify_external_calls(self, codebase_info: Dict, root_path: Path) -> List[Dict]:
        """Identify external API calls."""
        external_calls = []
        
        call_patterns = [
            r'fetch\s*\(',
            r'axios\.',
            r'requests\.',
            r'http\.get',
            r'http\.post',
            r'urllib\.request',
        ]
        
        for file_info in codebase_info.get('files', []):
            if not file_info.get('language'):
                continue
            
            try:
                file_path = Path(file_info['absolute_path'])
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for pattern in call_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        external_calls.append({
                            'file': file_info.get('path'),
                            'line': content[:match.start()].count('\n') + 1,
                            'pattern': pattern,
                        })
            
            except Exception:
                continue
        
        return external_calls
    
    def _analyze_auth_flow(self, codebase_info: Dict, root_path: Path) -> List[Dict]:
        """Analyze authentication flow."""
        auth_flow = []
        
        auth_patterns = {
            'login': [
                r'def\s+login',
                r'function\s+login',
                r'@app\.route.*login',
                r'app\.post.*login',
            ],
            'signup': [
                r'def\s+signup',
                r'function\s+signup',
                r'@app\.route.*signup',
                r'app\.post.*signup',
            ],
            'auth_middleware': [
                r'@require_auth',
                r'@login_required',
                r'authenticate',
                r'verifyToken',
                r'checkAuth',
            ],
            'jwt': [
                r'jwt\.encode',
                r'jwt\.decode',
                r'jsonwebtoken',
            ],
            'session': [
                r'session\[',
                r'req\.session',
                r'express-session',
            ],
        }
        
        for file_info in codebase_info.get('files', []):
            if not file_info.get('language'):
                continue
            
            try:
                file_path = Path(file_info['absolute_path'])
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for auth_type, patterns in auth_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, content):
                            auth_flow.append({
                                'type': auth_type,
                                'file': file_info.get('path'),
                                'pattern': pattern,
                            })
            
            except Exception:
                continue
        
        return auth_flow
    
    def _analyze_state_management(self, codebase_info: Dict, root_path: Path) -> Dict:
        """Analyze state management patterns."""
        state_mgmt = {
            'react_state': [],
            'redux': [],
            'context': [],
            'global_vars': [],
        }
        
        for file_info in codebase_info.get('files', []):
            language = file_info.get('language')
            if language not in ['javascript', 'typescript']:
                continue
            
            try:
                file_path = Path(file_info['absolute_path'])
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # React state
                if re.search(r'useState|this\.state', content):
                    state_mgmt['react_state'].append(file_info.get('path'))
                
                # Redux
                if re.search(r'createStore|useSelector|useDispatch', content):
                    state_mgmt['redux'].append(file_info.get('path'))
                
                # Context
                if re.search(r'createContext|useContext', content):
                    state_mgmt['context'].append(file_info.get('path'))
                
                # Global variables
                if re.search(r'window\.|global\.', content):
                    state_mgmt['global_vars'].append(file_info.get('path'))
            
            except Exception:
                continue
        
        return state_mgmt
