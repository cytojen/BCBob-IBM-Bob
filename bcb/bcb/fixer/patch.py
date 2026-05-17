"""Patch generator and applier - creates and applies code fixes."""

import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import asyncio

from bcb.analyzer.llm_client import BobLLMClient


class PatchGenerator:
    """Generates and applies patches to fix security issues."""
    
    def __init__(self, llm_client: BobLLMClient):
        """
        Initialize patch generator.
        
        Args:
            llm_client: IBM Bob LLM client
        """
        self.llm_client = llm_client
    
    def generate_patch(
        self,
        root_cause: Dict,
        codebase_info: Dict,
    ) -> Optional[Dict]:
        """
        Generate a patch for a root cause.
        
        Args:
            root_cause: Root cause dict
            codebase_info: Codebase metadata
            
        Returns:
            Patch dict or None if generation failed
        """
        findings = root_cause.get('findings', [])
        if not findings:
            return None
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                self.llm_client.generate_patch(root_cause, findings, codebase_info)
            )

            if response.confidence < 0.5:
                return None

            return {
                'root_cause_id': root_cause.get('id'),
                'patch_content': response.patch,
                'explanation': response.explanation,
                'files_modified': response.files_modified,
                'confidence': response.confidence,
                'risks': response.risks or [],
                'applied': False,
                'verified': False,
            }

        except Exception as e:
            print(f"Error generating patch: {e}")
            return None
        finally:
            try:
                loop.run_until_complete(self.llm_client.close())
            except Exception:
                pass
            loop.close()
            asyncio.set_event_loop(None)
    
    def apply_patch(
        self,
        patch: Dict,
        root_path: Path,
        dry_run: bool = False,
    ) -> Tuple[bool, str]:
        """
        Apply a patch to the codebase.
        
        Args:
            patch: Patch dict
            root_path: Root path of codebase
            dry_run: If True, don't actually apply the patch
            
        Returns:
            Tuple of (success, message)
        """
        patch_content = patch.get('patch_content', '')
        if not patch_content:
            return False, "Empty patch content"
        
        if dry_run:
            return True, "Dry run - patch not applied"
        
        # Create temporary patch file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.patch',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(patch_content)
            patch_file = f.name
        
        try:
            # Apply patch using git apply
            result = subprocess.run(
                ['git', 'apply', '--check', patch_file],
                cwd=root_path,
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                return False, f"Patch validation failed: {result.stderr}"
            
            # Actually apply the patch
            result = subprocess.run(
                ['git', 'apply', patch_file],
                cwd=root_path,
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                return False, f"Patch application failed: {result.stderr}"
            
            patch['applied'] = True
            return True, "Patch applied successfully"
        
        except Exception as e:
            return False, f"Error applying patch: {str(e)}"
        
        finally:
            # Clean up temp file
            try:
                Path(patch_file).unlink()
            except Exception:
                pass
    
    def verify_patch(
        self,
        patch: Dict,
        root_path: Path,
    ) -> Tuple[bool, List[str]]:
        """
        Verify that a patch doesn't break the codebase.
        
        Args:
            patch: Patch dict
            root_path: Root path of codebase
            
        Returns:
            Tuple of (success, list of issues)
        """
        issues = []
        
        # 1. Check syntax for modified files
        for file_path in patch.get('files_modified', []):
            full_path = root_path / file_path
            if not full_path.exists():
                issues.append(f"File not found: {file_path}")
                continue
            
            # Check syntax based on file type
            if file_path.endswith('.py'):
                if not self._check_python_syntax(full_path):
                    issues.append(f"Python syntax error in {file_path}")
            
            elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                if not self._check_javascript_syntax(full_path):
                    issues.append(f"JavaScript/TypeScript syntax error in {file_path}")
        
        # 2. Run existing tests if available
        test_result = self._run_tests(root_path)
        if test_result:
            issues.extend(test_result)
        
        # 3. LLM review of the patch (skip if no API key)
        if self.llm_client.api_key:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(
                    self.llm_client.review_patch(
                        patch.get('patch_content', ''),
                        [],
                    )
                )
                if not response.approved:
                    issues.extend(response.issues_found)
            except Exception as e:
                issues.append(f"LLM review failed: {str(e)}")
            finally:
                try:
                    loop.run_until_complete(self.llm_client.close())
                except Exception:
                    pass
                loop.close()
                asyncio.set_event_loop(None)
        
        success = len(issues) == 0
        if success:
            patch['verified'] = True
        
        return success, issues
    
    def _check_python_syntax(self, file_path: Path) -> bool:
        """Check Python file syntax."""
        try:
            result = subprocess.run(
                ['python', '-m', 'py_compile', str(file_path)],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_javascript_syntax(self, file_path: Path) -> bool:
        """Check JavaScript/TypeScript file syntax."""
        try:
            # Try using node to check syntax
            result = subprocess.run(
                ['node', '--check', str(file_path)],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            # If node is not available, assume syntax is OK
            return True
    
    def _run_tests(self, root_path: Path) -> List[str]:
        """Run existing test suite."""
        issues = []
        
        # Try common test commands
        test_commands = [
            (['pytest', '-x'], 'pytest'),
            (['npm', 'test'], 'npm'),
            (['python', '-m', 'unittest', 'discover'], 'unittest'),
            (['cargo', 'test'], 'cargo'),
        ]
        
        for cmd, name in test_commands:
            # Check if test framework is available
            if name == 'npm' and not (root_path / 'package.json').exists():
                continue
            if name == 'cargo' and not (root_path / 'Cargo.toml').exists():
                continue
            
            try:
                result = subprocess.run(
                    cmd,
                    cwd=root_path,
                    capture_output=True,
                    text=True,
                    timeout=60,  # 1 minute timeout
                )
                
                if result.returncode != 0:
                    issues.append(f"Tests failed ({name}): {result.stderr[:200]}")
                    break  # Stop after first test failure
            
            except subprocess.TimeoutExpired:
                issues.append(f"Tests timed out ({name})")
                break
            
            except FileNotFoundError:
                # Test framework not available
                continue
            
            except Exception as e:
                # Ignore other errors
                continue
        
        return issues
    
    def revert_patch(
        self,
        patch: Dict,
        root_path: Path,
    ) -> Tuple[bool, str]:
        """
        Revert a previously applied patch.
        
        Args:
            patch: Patch dict
            root_path: Root path of codebase
            
        Returns:
            Tuple of (success, message)
        """
        if not patch.get('applied'):
            return False, "Patch was not applied"
        
        patch_content = patch.get('patch_content', '')
        if not patch_content:
            return False, "Empty patch content"
        
        # Create temporary patch file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.patch',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(patch_content)
            patch_file = f.name
        
        try:
            # Revert using git apply --reverse
            result = subprocess.run(
                ['git', 'apply', '--reverse', patch_file],
                cwd=root_path,
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                return False, f"Patch revert failed: {result.stderr}"
            
            patch['applied'] = False
            patch['verified'] = False
            return True, "Patch reverted successfully"
        
        except Exception as e:
            return False, f"Error reverting patch: {str(e)}"
        
        finally:
            # Clean up temp file
            try:
                Path(patch_file).unlink()
            except Exception:
                pass
    
    def create_git_stash(self, root_path: Path) -> Tuple[bool, str]:
        """
        Create a git stash before applying patches.
        
        Args:
            root_path: Root path of codebase
            
        Returns:
            Tuple of (success, stash_id)
        """
        try:
            result = subprocess.run(
                ['git', 'stash', 'push', '-m', 'BCB: Before applying patches'],
                cwd=root_path,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                # Get stash ID
                result = subprocess.run(
                    ['git', 'rev-parse', 'stash@{0}'],
                    cwd=root_path,
                    capture_output=True,
                    text=True,
                )
                stash_id = result.stdout.strip()
                return True, stash_id
            else:
                return False, "Failed to create stash"
        
        except Exception as e:
            return False, f"Error creating stash: {str(e)}"
    
    def restore_git_stash(self, root_path: Path, stash_id: str) -> Tuple[bool, str]:
        """
        Restore a git stash.
        
        Args:
            root_path: Root path of codebase
            stash_id: Stash ID to restore
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ['git', 'stash', 'pop'],
                cwd=root_path,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                return True, "Stash restored successfully"
            else:
                return False, f"Failed to restore stash: {result.stderr}"
        
        except Exception as e:
            return False, f"Error restoring stash: {str(e)}"
