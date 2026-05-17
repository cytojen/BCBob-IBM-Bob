"""IBM Bob LLM client - handles communication with Bob's API."""

import os
import json
import hashlib
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiohttp
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Structured LLM response."""
    is_vulnerable: bool = Field(description="Whether the code is vulnerable")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(description="Explanation of the finding")
    blast_radius: Optional[str] = Field(None, description="Impact scope")
    affected_lines: Optional[List[int]] = Field(None, description="Affected line numbers")


class RootCauseResponse(BaseModel):
    """Root cause analysis response."""
    root_cause: str = Field(description="The underlying architectural issue")
    affected_findings: List[str] = Field(description="IDs of related findings")
    fix_strategy: str = Field(description="High-level fix approach")
    confidence: float = Field(ge=0.0, le=1.0)


class PatchResponse(BaseModel):
    """Patch generation response."""
    patch: str = Field(description="Unified diff patch")
    explanation: str = Field(description="What the patch does")
    files_modified: List[str] = Field(description="List of files modified")
    confidence: float = Field(ge=0.0, le=1.0)
    risks: Optional[List[str]] = Field(None, description="Potential risks")


class ReviewResponse(BaseModel):
    """Patch review response."""
    approved: bool = Field(description="Whether patch is safe to apply")
    issues_found: List[str] = Field(description="Issues in the patch")
    confidence: float = Field(ge=0.0, le=1.0)
    suggestions: Optional[List[str]] = Field(None, description="Improvement suggestions")


class BobLLMClient:
    """Client for IBM Bob LLM API with caching and batching."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        Initialize Bob LLM client.
        
        Args:
            api_key: IBM Bob API key (defaults to BOB_API_KEY env var)
            api_url: API endpoint (defaults to BOB_API_URL env var)
            cache_dir: Directory for response cache
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv('BOB_API_KEY')
        self.api_url = api_url or os.getenv('BOB_API_URL', 'https://api.bob.build/v1')
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Setup cache
        if cache_dir is None:
            cache_dir = Path.home() / '.bcb' / 'cache'
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Session will be created when needed
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                'Content-Type': 'application/json',
            }
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
            )
        return self._session
    
    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_cache_key(self, prompt: str, context: str = "") -> str:
        """Generate cache key from prompt and context."""
        content = f"{prompt}|{context}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get response from cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, response: Dict):
        """Save response to cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(response, f, indent=2)
        except Exception:
            pass
    
    async def _call_api(
        self,
        prompt: str,
        system_prompt: str = "",
        response_format: Optional[Dict] = None,
    ) -> Dict:
        """
        Call IBM Bob API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            response_format: JSON schema for structured output
            
        Returns:
            API response
        """
        session = await self._get_session()
        
        payload = {
            'model': 'bob-1',  # Adjust based on actual Bob API
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ],
        }
        
        if response_format:
            payload['response_format'] = response_format
        
        for attempt in range(self.max_retries):
            try:
                async with session.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:  # Rate limit
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
            
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("Max retries exceeded")
    
    async def verify_finding(
        self,
        finding: Dict,
        code: str,
        context: str = "",
    ) -> LLMResponse:
        """
        Verify if a finding is a real vulnerability.
        
        Args:
            finding: Finding dict from pattern matcher
            code: Code snippet
            context: Additional context (imports, surrounding code)
            
        Returns:
            LLMResponse with verification result
        """
        # Check cache
        cache_key = self._get_cache_key(
            f"verify:{finding.get('id')}:{code}",
            context
        )
        cached = self._get_from_cache(cache_key)
        if cached:
            return LLMResponse(**cached)
        
        # Build prompt
        prompt_template = finding.get('llm_prompt', '')
        prompt = prompt_template.format(
            code=code,
            context=context,
            file_path=finding.get('file_path', ''),
        )
        
        system_prompt = f"""You are a security expert analyzing code for vulnerabilities.
Pattern: {finding.get('name')}
CWE: {finding.get('cwe')}
Description: {finding.get('description')}

Analyze the code carefully and determine if this is a real vulnerability or a false positive.
Consider the context and how the code is actually used.
"""
        
        # Call API
        response = await self._call_api(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format={'type': 'json_object'},
        )
        
        # Parse response
        try:
            content = response['choices'][0]['message']['content']
            data = json.loads(content)
            result = LLMResponse(**data)
            
            # Cache result
            self._save_to_cache(cache_key, result.model_dump())
            
            return result
        except Exception as e:
            # API unavailable — keep static finding with neutral confidence
            return LLMResponse(
                is_vulnerable=True,
                confidence=0.6,
                reasoning=f"LLM verification unavailable: {str(e)}",
            )
    
    async def verify_findings_batch(
        self,
        findings: List[Dict],
        codebase_info: Dict,
    ) -> List[LLMResponse]:
        """
        Verify multiple findings in parallel.
        
        Args:
            findings: List of findings
            codebase_info: Codebase metadata for context
            
        Returns:
            List of LLMResponse objects
        """
        tasks = []
        
        for finding in findings:
            # Get code and context
            code = finding.get('context', finding.get('matched_text', ''))
            context = self._build_context(finding, codebase_info)
            
            task = self.verify_finding(finding, code, context)
            tasks.append(task)
        
        # Run in parallel with concurrency limit
        results = []
        batch_size = 10  # Process 10 at a time
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append(LLMResponse(
                        is_vulnerable=True,
                        confidence=0.6,
                        reasoning=f"Verification failed: {str(result)}",
                    ))
                else:
                    results.append(result)
        
        return results
    
    async def cluster_root_cause(
        self,
        findings: List[Dict],
        architecture: Dict,
    ) -> RootCauseResponse:
        """
        Identify root cause for a group of similar findings.
        
        Args:
            findings: List of related findings
            architecture: Architecture mapping
            
        Returns:
            RootCauseResponse with root cause analysis
        """
        # Build prompt
        findings_summary = "\n".join([
            f"- {f.get('name')} in {f.get('file_path')}:{f.get('line')}"
            for f in findings[:10]  # Limit to first 10
        ])
        
        prompt = f"""Given these {len(findings)} similar security findings:

{findings_summary}

Architecture context:
- Entry points: {len(architecture.get('entry_points', []))}
- API endpoints: {len(architecture.get('api_endpoints', []))}
- Database access points: {len(architecture.get('database_access', []))}

What is the single underlying architectural issue causing all these findings?
What's the root cause that, if fixed, would resolve all of them?
"""
        
        system_prompt = """You are a software architect analyzing security issues.
Identify the root architectural cause, not individual symptoms.
Think about missing abstractions, shared utilities, or architectural patterns."""
        
        response = await self._call_api(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format={'type': 'json_object'},
        )
        
        try:
            content = response['choices'][0]['message']['content']
            data = json.loads(content)
            return RootCauseResponse(**data)
        except Exception:
            return RootCauseResponse(
                root_cause="Multiple similar issues detected",
                affected_findings=[f.get('id', '') for f in findings],
                fix_strategy="Fix each occurrence individually",
                confidence=0.3,
            )
    
    async def generate_patch(
        self,
        root_cause: Dict,
        findings: List[Dict],
        codebase_info: Dict,
    ) -> PatchResponse:
        """
        Generate a patch to fix a root cause.
        
        Args:
            root_cause: Root cause analysis
            findings: Related findings
            codebase_info: Codebase metadata
            
        Returns:
            PatchResponse with unified diff
        """
        # Build prompt with relevant code
        prompt = f"""Root cause: {root_cause.get('root_cause')}
Fix strategy: {root_cause.get('fix_strategy')}

Affected files:
{self._format_affected_files(findings)}

Generate a minimal unified diff patch that fixes the root cause.
The patch should be safe, idiomatic, and not break existing functionality.
"""
        
        system_prompt = """You are an expert software engineer.
Generate clean, minimal patches in unified diff format.
Focus on fixing the root cause, not individual symptoms."""
        
        response = await self._call_api(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format={'type': 'json_object'},
        )
        
        try:
            content = response['choices'][0]['message']['content']
            data = json.loads(content)
            return PatchResponse(**data)
        except Exception as e:
            return PatchResponse(
                patch="",
                explanation=f"Could not generate patch: {str(e)}",
                files_modified=[],
                confidence=0.0,
            )
    
    async def review_patch(
        self,
        patch: str,
        original_findings: List[Dict],
    ) -> ReviewResponse:
        """
        Review a generated patch for safety.
        
        Args:
            patch: Unified diff patch
            original_findings: Original findings being fixed
            
        Returns:
            ReviewResponse with approval status
        """
        prompt = f"""Review this patch for security and correctness:

{patch}

Original issues being fixed:
{self._format_findings(original_findings)}

Does this patch:
1. Fix the security issues?
2. Introduce any new vulnerabilities?
3. Break existing functionality?
4. Follow best practices?
"""
        
        system_prompt = """You are a security-focused code reviewer.
Carefully analyze patches for correctness and safety."""
        
        response = await self._call_api(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format={'type': 'json_object'},
        )
        
        try:
            content = response['choices'][0]['message']['content']
            data = json.loads(content)
            return ReviewResponse(**data)
        except Exception:
            return ReviewResponse(
                approved=False,
                issues_found=["Could not review patch"],
                confidence=0.0,
            )
    
    def _build_context(self, finding: Dict, codebase_info: Dict) -> str:
        """Build context for a finding."""
        # Get file info
        file_path = finding.get('absolute_path')
        if not file_path:
            return ""
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Get imports (first 50 lines)
            imports = ''.join(lines[:50])
            
            # Get surrounding context
            line_num = finding.get('line', 1)
            start = max(0, line_num - 10)
            end = min(len(lines), line_num + 10)
            context = ''.join(lines[start:end])
            
            return f"Imports:\n{imports}\n\nContext:\n{context}"
        except Exception:
            return ""
    
    def _format_affected_files(self, findings: List[Dict]) -> str:
        """Format affected files for prompt."""
        files = {}
        for f in findings:
            path = f.get('file_path', '')
            if path not in files:
                files[path] = []
            files[path].append(f.get('line', 0))
        
        result = []
        for path, lines in files.items():
            result.append(f"- {path}: lines {', '.join(map(str, sorted(lines)))}")
        
        return '\n'.join(result)
    
    def _format_findings(self, findings: List[Dict]) -> str:
        """Format findings for prompt."""
        return '\n'.join([
            f"- {f.get('name')} ({f.get('severity')}) in {f.get('file_path')}:{f.get('line')}"
            for f in findings[:5]  # Limit to first 5
        ])
