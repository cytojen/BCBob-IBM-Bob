"""Report generator - creates markdown and JSON reports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ReportGenerator:
    """Generates audit reports in various formats."""
    
    def __init__(self, root_path: Path):
        """
        Initialize report generator.
        
        Args:
            root_path: Root path of codebase
        """
        self.root_path = root_path
    
    def generate(
        self,
        codebase_info: Dict,
        architecture: Dict,
        findings: List[Dict],
        root_causes: List[Dict],
        output_path: Path,
    ):
        """
        Generate initial audit report.
        
        Args:
            codebase_info: Codebase metadata
            architecture: Architecture mapping
            findings: List of findings
            root_causes: List of root causes
            output_path: Output file path
        """
        report = self._build_initial_report(
            codebase_info,
            architecture,
            findings,
            root_causes,
        )
        
        self._write_markdown(report, output_path)
    
    def generate_final(
        self,
        results: Dict,
        output_path: Path,
    ):
        """
        Generate final report after repair loop.
        
        Args:
            results: Repair loop results
            output_path: Output file path
        """
        report = self._build_final_report(results)
        self._write_markdown(report, output_path)
    
    def _build_initial_report(
        self,
        codebase_info: Dict,
        architecture: Dict,
        findings: List[Dict],
        root_causes: List[Dict],
    ) -> Dict:
        """Build initial report structure."""
        # Calculate severity stats
        severity_stats = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0,
        }
        
        for finding in findings:
            severity = finding.get('severity', 'MEDIUM').upper()
            if severity in severity_stats:
                severity_stats[severity] += 1
        
        return {
            'title': 'BCB Audit Report',
            'project_name': self.root_path.name,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'codebase_info': codebase_info,
            'architecture': architecture,
            'severity_stats': severity_stats,
            'findings': findings,
            'root_causes': root_causes,
            'production_readiness': self._assess_readiness(severity_stats),
        }
    
    def _build_final_report(self, results: Dict) -> Dict:
        """Build final report structure."""
        return {
            'title': 'BCB Final Audit Report',
            'project_name': self.root_path.name,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'results': results,
            'production_readiness': results.get('production_readiness', 'UNKNOWN'),
        }
    
    def _assess_readiness(self, severity_stats: Dict) -> str:
        """Assess production readiness based on severity stats."""
        critical = severity_stats.get('CRITICAL', 0)
        high = severity_stats.get('HIGH', 0)
        
        if critical > 0:
            return 'NOT_READY'
        elif high > 0:
            return 'NEEDS_REVIEW'
        else:
            return 'READY'
    
    def _write_markdown(self, report: Dict, output_path: Path):
        """Write report as markdown."""
        lines = []
        
        # Header
        lines.append(f"# {report['title']}\n")
        lines.append(f"**Project:** {report['project_name']}  ")
        lines.append(f"**Scanned:** {report['timestamp']}  ")
        
        if 'codebase_info' in report:
            codebase = report['codebase_info']
            lines.append(f"**Files analyzed:** {codebase.get('total_files', 0)}  ")
            lines.append(f"**LOC:** {codebase.get('total_loc', 0):,}  ")
        
        lines.append("\n")
        
        # Executive Summary
        lines.append("## Executive Summary\n")
        
        if 'severity_stats' in report:
            stats = report['severity_stats']
            lines.append("| Severity | Found | Fixed | Remaining |")
            lines.append("| -------- | ----- | ----- | --------- |")
            
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if isinstance(stats.get(severity), dict):
                    # Final report format
                    found = stats[severity].get('found', 0)
                    fixed = stats[severity].get('fixed', 0)
                    remaining = stats[severity].get('remaining', 0)
                else:
                    # Initial report format
                    found = stats.get(severity, 0)
                    fixed = 0
                    remaining = found
                
                lines.append(f"| {severity} | {found} | {fixed} | {remaining} |")
        
        lines.append("\n")
        
        # Production Readiness
        readiness = report.get('production_readiness', 'UNKNOWN')
        readiness_label = {
            'READY': '[OK]',
            'NEEDS_REVIEW': '[!!]',
            'NOT_READY': '[X]',
            'UNKNOWN': '[?]',
        }

        lines.append(f"**Production readiness:** {readiness_label.get(readiness, '[?]')} {readiness}\n")
        lines.append("\n")
        
        # Root Causes
        if 'root_causes' in report and report['root_causes']:
            lines.append("## Root Causes\n")
            
            for rc in report['root_causes']:
                lines.append(f"### {rc.get('id', 'RC-???')}: {rc.get('name', 'Unknown')}\n")
                lines.append(f"- **Severity:** {rc.get('severity', 'MEDIUM')}")
                lines.append(f"- **Confidence:** {rc.get('confidence', 0):.2f}")
                lines.append(f"- **Architectural cause:** {rc.get('description', 'N/A')}")
                lines.append(f"- **Symptoms:** {len(rc.get('findings', []))} findings across {len(rc.get('affected_files', []))} files")
                lines.append(f"- **Fix strategy:** {rc.get('fix_strategy', 'N/A')}")
                
                if rc.get('affected_files'):
                    lines.append(f"- **Files affected:**")
                    for file_path in rc['affected_files'][:5]:  # Limit to first 5
                        lines.append(f"  - `{file_path}`")
                    if len(rc['affected_files']) > 5:
                        lines.append(f"  - ... and {len(rc['affected_files']) - 5} more")
                
                lines.append("\n")
        
        # Detailed Findings
        if 'findings' in report and report['findings']:
            lines.append("## Detailed Findings\n")
            
            # Group by severity
            by_severity = {}
            for finding in report['findings']:
                severity = finding.get('severity', 'MEDIUM').upper()
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(finding)
            
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity not in by_severity:
                    continue
                
                findings_list = by_severity[severity]
                lines.append(f"### {severity} Severity ({len(findings_list)} findings)\n")
                
                for finding in findings_list[:10]:  # Limit to first 10 per severity
                    lines.append(f"#### [{severity}] {finding.get('name', 'Unknown')} — `{finding.get('file_path', 'unknown')}:{finding.get('line', 0)}`\n")
                    lines.append(f"- **CWE:** {finding.get('cwe', 'N/A')}")
                    lines.append(f"- **Confidence:** {finding.get('confidence', 0):.2f}")
                    lines.append(f"- **Description:** {finding.get('description', 'N/A')}")
                    
                    if finding.get('llm_reasoning'):
                        lines.append(f"- **Analysis:** {finding['llm_reasoning']}")
                    
                    if finding.get('blast_radius'):
                        lines.append(f"- **Blast radius:** {finding['blast_radius']}")
                    
                    # Show code snippet
                    if finding.get('context'):
                        lines.append("\n```")
                        lines.append(finding['context'][:500])  # Limit length
                        lines.append("```\n")
                    
                    if finding.get('fix_template'):
                        lines.append(f"**Fix:** {finding['fix_template']}\n")
                    
                    lines.append("\n")
                
                if len(findings_list) > 10:
                    lines.append(f"*... and {len(findings_list) - 10} more {severity} findings*\n\n")
        
        # Iteration Log
        if 'results' in report and report['results'].get('iterations'):
            lines.append("## Iteration Log\n")
            
            for iteration in report['results']['iterations']:
                iter_num = iteration['iteration']
                remaining = iteration['remaining_issues']
                total_remaining = sum(remaining.values())
                
                lines.append(f"- **Pass {iter_num}:** {total_remaining} issues remaining")
                
                if iteration['patches_applied']:
                    lines.append(f" → fixed {len(iteration['patches_applied'])}")
                
                if iteration['patches_failed']:
                    lines.append(f" → {len(iteration['patches_failed'])} failed")
                
                lines.append("\n")
            
            lines.append("\n")
        
        # Needs Human Review
        if 'root_causes' in report:
            review_needed = [
                rc for rc in report['root_causes']
                if rc.get('confidence', 0) < 0.6 or rc.get('severity') == 'CRITICAL'
            ]
            
            if review_needed:
                lines.append("## Needs Human Review\n")
                lines.append(f"{len(review_needed)} root causes require manual review:\n")
                
                for rc in review_needed:
                    reason = []
                    if rc.get('confidence', 0) < 0.6:
                        reason.append("low confidence")
                    if rc.get('severity') == 'CRITICAL':
                        reason.append("critical severity")
                    
                    lines.append(f"- **{rc.get('id')}:** {rc.get('name')} ({', '.join(reason)})")
                
                lines.append("\n")
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def generate_json(
        self,
        codebase_info: Dict,
        architecture: Dict,
        findings: List[Dict],
        root_causes: List[Dict],
        output_path: Path,
    ):
        """Generate JSON report."""
        report = self._build_initial_report(
            codebase_info,
            architecture,
            findings,
            root_causes,
        )
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
    
    def generate_html(
        self,
        codebase_info: Dict,
        architecture: Dict,
        findings: List[Dict],
        root_causes: List[Dict],
        output_path: Path,
    ):
        """Generate HTML report."""
        # Convert markdown to HTML (simplified)
        md_path = output_path.with_suffix('.md')
        self.generate(codebase_info, architecture, findings, root_causes, md_path)
        
        # Read markdown
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Simple HTML wrapper
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BCB Audit Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        code {{ background-color: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
        .high {{ color: #f57c00; font-weight: bold; }}
        .medium {{ color: #fbc02d; font-weight: bold; }}
        .low {{ color: #388e3c; font-weight: bold; }}
    </style>
</head>
<body>
    <pre>{md_content}</pre>
</body>
</html>"""
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
