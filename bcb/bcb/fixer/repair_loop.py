"""Repair loop - iterative scan-fix-verify cycle."""

from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from bcb.scanner.codebase import CodebaseScanner
from bcb.analyzer.llm_client import BobLLMClient
from bcb.analyzer.security import SecurityAnalyzer
from bcb.analyzer.root_cause import RootCauseClusterer
from bcb.fixer.patch import PatchGenerator
from bcb.fixer.local_patch import LocalPatcher
from bcb.reporter.report import ReportGenerator


console = Console(legacy_windows=False)


class RepairLoop:
    """Iterative repair loop that scans, fixes, and verifies until clean."""
    
    def __init__(
        self,
        scanner: CodebaseScanner,
        llm_client: BobLLMClient,
        security_analyzer: SecurityAnalyzer,
        clusterer: RootCauseClusterer,
        report_gen: ReportGenerator,
        max_iterations: int = 5,
    ):
        """
        Initialize repair loop.
        
        Args:
            scanner: Codebase scanner
            llm_client: IBM Bob LLM client
            security_analyzer: Security analyzer
            clusterer: Root cause clusterer
            report_gen: Report generator
            max_iterations: Maximum repair iterations
        """
        self.scanner = scanner
        self.llm_client = llm_client
        self.security_analyzer = security_analyzer
        self.clusterer = clusterer
        self.report_gen = report_gen
        self.max_iterations = max_iterations
        self.patch_generator = PatchGenerator(llm_client)
        self.local_patcher = LocalPatcher()
    
    def run(
        self,
        path: Path,
        root_causes: List[Dict],
        codebase_info: Dict,
        architecture: Dict,
    ) -> Dict:
        """
        Run the repair loop.
        
        Args:
            path: Root path of codebase
            root_causes: Initial root causes
            codebase_info: Codebase metadata
            architecture: Architecture mapping
            
        Returns:
            Final results dict
        """
        results = {
            'iterations': [],
            'patches_applied': [],
            'patches_failed': [],
            'severity_stats': {},
            'production_readiness': 'NOT_READY',
        }
        
        # Create git stash before starting
        success, stash_id = self.patch_generator.create_git_stash(path)
        if success:
            safe_id = stash_id[:8].replace("[", "\\[")
            console.print(f"[green][OK][/green] Created git stash: {safe_id}")
            results['stash_id'] = stash_id
        else:
            console.print("[yellow][!!][/yellow] Could not create git stash")
        
        # Prioritize root causes
        prioritized = self.clusterer.prioritize_root_causes(root_causes)
        
        # Iteration loop
        for iteration in range(1, self.max_iterations + 1):
            console.print(f"\n[bold cyan]Iteration {iteration}/{self.max_iterations}[/bold cyan]")
            
            iteration_result = self._run_iteration(
                iteration,
                prioritized,
                path,
                codebase_info,
                architecture,
            )
            
            results['iterations'].append(iteration_result)
            results['patches_applied'].extend(iteration_result['patches_applied'])
            results['patches_failed'].extend(iteration_result['patches_failed'])
            
            # Check if we're done
            remaining_critical = iteration_result['remaining_issues']['CRITICAL']
            remaining_high = iteration_result['remaining_issues']['HIGH']
            
            if remaining_critical == 0 and remaining_high == 0:
                console.print("\n[bold green][OK] All critical and high severity issues resolved![/bold green]")
                results['production_readiness'] = 'READY'
                break
            
            # If no progress, stop
            if iteration > 1:
                prev_total = sum(results['iterations'][-2]['remaining_issues'].values())
                curr_total = sum(iteration_result['remaining_issues'].values())
                
                if curr_total >= prev_total:
                    console.print("\n[yellow]No progress made, stopping iterations[/yellow]")
                    break
            
            # Update root causes for next iteration
            prioritized = iteration_result.get('new_root_causes', [])
            if not prioritized:
                break
        
        # Calculate final stats
        results['severity_stats'] = self._calculate_final_stats(results)
        
        # Determine production readiness
        if results['production_readiness'] != 'READY':
            final_critical = results['severity_stats']['CRITICAL']['remaining']
            final_high = results['severity_stats']['HIGH']['remaining']
            
            if final_critical == 0 and final_high == 0:
                results['production_readiness'] = 'READY'
            elif final_critical == 0:
                results['production_readiness'] = 'NEEDS_REVIEW'
            else:
                results['production_readiness'] = 'NOT_READY'
        
        return results
    
    def _run_iteration(
        self,
        iteration: int,
        root_causes: List[Dict],
        path: Path,
        codebase_info: Dict,
        architecture: Dict,
    ) -> Dict:
        """Run a single iteration of the repair loop."""
        iteration_result = {
            'iteration': iteration,
            'patches_applied': [],
            'patches_failed': [],
            'remaining_issues': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            'new_root_causes': [],
        }
        
        with Progress(
            SpinnerColumn("line"),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Fix each root cause
            for i, root_cause in enumerate(root_causes, 1):
                task = progress.add_task(
                    f"Fixing {i}/{len(root_causes)}: {root_cause.get('name')}...",
                    total=None
                )
                
                result = self._fix_root_cause(root_cause, path, codebase_info)
                
                if result['success']:
                    iteration_result['patches_applied'].append(result)
                    console.print(f"[green][OK][/green] Fixed: {root_cause.get('name')}")
                else:
                    iteration_result['patches_failed'].append(result)
                    console.print(f"[red][X][/red] Failed: {root_cause.get('name')} - {result.get('error')}")
                
                progress.update(task, completed=True)
            
            # Re-scan to check for remaining issues
            task = progress.add_task("Re-scanning codebase...", total=None)
            
            findings = self.scanner.scan_patterns(codebase_info)
            verified_findings = self.security_analyzer.verify_findings(findings, codebase_info)
            
            progress.update(task, completed=True)
            
            # Count remaining issues by severity
            for finding in verified_findings:
                severity = finding.get('severity', 'MEDIUM').upper()
                if severity in iteration_result['remaining_issues']:
                    iteration_result['remaining_issues'][severity] += 1
            
            # Cluster new root causes if there are remaining issues
            if verified_findings:
                task = progress.add_task("Analyzing remaining issues...", total=None)
                new_root_causes = self.clusterer.cluster(verified_findings, architecture)
                iteration_result['new_root_causes'] = self.clusterer.prioritize_root_causes(
                    new_root_causes
                )
                progress.update(task, completed=True)
        
        return iteration_result
    
    def _fix_root_cause(
        self,
        root_cause: Dict,
        path: Path,
        codebase_info: Dict,
    ) -> Dict:
        result = {
            'root_cause_id': root_cause.get('id'),
            'root_cause_name': root_cause.get('name'),
            'success': False,
            'patch': None,
            'error': None,
        }

        confidence = root_cause.get('confidence', 0)
        severity = root_cause.get('severity', '').upper()

        if confidence < 0.5:
            result['error'] = "Confidence too low for auto-fix"
            return result

        if severity == 'CRITICAL':
            result['error'] = "Critical issues require manual review"
            return result

        # ── Try LLM-generated patch first (only if API key is set) ──────────
        if self.llm_client.api_key:
            patch = self.patch_generator.generate_patch(root_cause, codebase_info)
            if patch:
                success, message = self.patch_generator.apply_patch(patch, path)
                if success:
                    result['success'] = True
                    result['patch'] = patch
                    return result
                result['error'] = message

        # ── Fall back to local rule-based patcher ────────────────────────────
        local_result = self.local_patcher.apply(root_cause, path)
        if local_result['success']:
            result['success'] = True
            result['patch'] = {'explanation': local_result['explanation']}
            result['error'] = None
        else:
            failed_reasons = [f['reason'] for f in local_result.get('failed', [])]
            result['error'] = (
                result.get('error') or
                ('; '.join(failed_reasons) if failed_reasons else 'No fix available')
            )

        return result
    
    def _calculate_final_stats(self, results: Dict) -> Dict:
        """Calculate final statistics."""
        stats = {
            'CRITICAL': {'found': 0, 'fixed': 0, 'remaining': 0},
            'HIGH': {'found': 0, 'fixed': 0, 'remaining': 0},
            'MEDIUM': {'found': 0, 'fixed': 0, 'remaining': 0},
            'LOW': {'found': 0, 'fixed': 0, 'remaining': 0},
        }
        
        if not results['iterations']:
            return stats
        
        # Get initial counts from first iteration
        first_iteration = results['iterations'][0]
        
        # Count fixed issues from successful patches
        for patch_result in results['patches_applied']:
            patch = patch_result.get('patch', {})
            root_cause_id = patch_result.get('root_cause_id')
            
            # Find the root cause to get severity
            # This is simplified - in real implementation would track better
            severity = 'MEDIUM'  # Default
            
            if severity in stats:
                stats[severity]['fixed'] += 1
        
        # Get remaining from last iteration
        if results['iterations']:
            last_iteration = results['iterations'][-1]
            for severity, count in last_iteration['remaining_issues'].items():
                if severity in stats:
                    stats[severity]['remaining'] = count
                    stats[severity]['found'] = stats[severity]['fixed'] + count
        
        return stats
