"""Root cause analyzer - clusters findings into architectural issues."""

import asyncio
from typing import Dict, List, Set
from collections import defaultdict
from bcb.analyzer.llm_client import BobLLMClient


class RootCauseClusterer:
    """Clusters findings into root causes using LLM analysis."""
    
    def __init__(self, llm_client: BobLLMClient):
        """
        Initialize root cause clusterer.
        
        Args:
            llm_client: IBM Bob LLM client
        """
        self.llm_client = llm_client
    
    def cluster(
        self,
        findings: List[Dict],
        architecture: Dict,
    ) -> List[Dict]:
        """
        Cluster findings into root causes.

        When no API key is configured or the API is unreachable, uses
        static grouping only (by pattern ID + CWE).
        """
        if not findings:
            return []

        groups = self._group_similar_findings(findings)
        root_causes = []

        if not self.llm_client.api_key:
            # Static-only clustering — no LLM call
            for group_findings in groups.values():
                if len(group_findings) >= 2:
                    rc = self._create_group_root_cause(group_findings)
                else:
                    rc = self._create_standalone_root_cause(group_findings[0])
                root_causes.append(rc)
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for group_findings in groups.values():
                    if len(group_findings) >= 2:
                        rc = loop.run_until_complete(
                            self._analyze_root_cause(group_findings, architecture)
                        )
                    else:
                        rc = self._create_standalone_root_cause(group_findings[0])
                    root_causes.append(rc)
            except Exception:
                # API failed — fall back to static grouping for remaining groups
                pass
            finally:
                try:
                    loop.run_until_complete(self.llm_client.close())
                except Exception:
                    pass
                loop.close()
                asyncio.set_event_loop(None)

            # If LLM failed entirely and we got nothing, do static fallback
            if not root_causes:
                for group_findings in groups.values():
                    if len(group_findings) >= 2:
                        rc = self._create_group_root_cause(group_findings)
                    else:
                        rc = self._create_standalone_root_cause(group_findings[0])
                    root_causes.append(rc)

        for i, rc in enumerate(root_causes, 1):
            rc['id'] = f"RC-{i:03d}"

        return root_causes
    
    def _group_similar_findings(self, findings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group similar findings together.
        
        Groups by:
        1. Same pattern ID
        2. Same CWE
        3. Similar file patterns
        
        Args:
            findings: List of findings
            
        Returns:
            Dict mapping group ID to list of findings
        """
        groups = defaultdict(list)
        
        for finding in findings:
            # Create group key based on pattern and CWE
            pattern_id = finding.get('id', 'unknown')
            cwe = finding.get('cwe', 'unknown')
            
            # Group by pattern first
            group_key = f"{pattern_id}_{cwe}"
            groups[group_key].append(finding)
        
        return dict(groups)
    
    async def _analyze_root_cause(
        self,
        findings: List[Dict],
        architecture: Dict,
    ) -> Dict:
        """
        Analyze root cause for a group of findings using LLM.
        
        Args:
            findings: Group of similar findings
            architecture: Architecture mapping
            
        Returns:
            Root cause dict
        """
        # Call LLM to identify root cause
        response = await self.llm_client.cluster_root_cause(findings, architecture)
        
        # Build root cause dict
        root_cause = {
            'name': self._generate_root_cause_name(findings),
            'description': response.root_cause,
            'fix_strategy': response.fix_strategy,
            'confidence': response.confidence,
            'findings': findings,
            'finding_ids': [f.get('id', '') for f in findings],
            'severity': self._determine_group_severity(findings),
            'affected_files': self._get_affected_files(findings),
            'pattern_id': findings[0].get('id') if findings else None,
            'cwe': findings[0].get('cwe') if findings else None,
        }
        
        return root_cause
    
    def _create_group_root_cause(self, findings: List[Dict]) -> Dict:
        """Create a root cause for a group of similar findings without LLM."""
        first = findings[0]
        return {
            'name': self._generate_root_cause_name(findings),
            'description': first.get('description', ''),
            'fix_strategy': first.get('fix_template', 'Manual fix required'),
            'confidence': 0.5,
            'findings': findings,
            'finding_ids': [f.get('id', '') for f in findings],
            'severity': self._determine_group_severity(findings),
            'affected_files': self._get_affected_files(findings),
            'pattern_id': first.get('id'),
            'cwe': first.get('cwe'),
        }

    def _create_standalone_root_cause(self, finding: Dict) -> Dict:
        """
        Create a root cause for a standalone finding.
        
        Args:
            finding: Single finding
            
        Returns:
            Root cause dict
        """
        return {
            'name': finding.get('name', 'Unknown Issue'),
            'description': finding.get('description', ''),
            'fix_strategy': finding.get('fix_template', 'Manual fix required'),
            'confidence': finding.get('confidence', 0.5),
            'findings': [finding],
            'finding_ids': [finding.get('id', '')],
            'severity': finding.get('severity', 'MEDIUM'),
            'affected_files': [finding.get('file_path', '')],
            'pattern_id': finding.get('id'),
            'cwe': finding.get('cwe'),
        }
    
    def _generate_root_cause_name(self, findings: List[Dict]) -> str:
        """Generate a descriptive name for the root cause."""
        if not findings:
            return "Unknown Root Cause"
        
        # Use the pattern name
        pattern_name = findings[0].get('name', 'Unknown')
        count = len(findings)
        
        if count > 1:
            return f"{pattern_name} (×{count})"
        else:
            return pattern_name
    
    def _determine_group_severity(self, findings: List[Dict]) -> str:
        """
        Determine severity for a group of findings.
        Takes the highest severity in the group.
        
        Args:
            findings: List of findings
            
        Returns:
            Severity string
        """
        severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        
        highest_severity = 'LOW'
        for finding in findings:
            severity = finding.get('severity', 'MEDIUM').upper()
            if severity in severity_order:
                if severity_order.index(severity) < severity_order.index(highest_severity):
                    highest_severity = severity
        
        return highest_severity
    
    def _get_affected_files(self, findings: List[Dict]) -> List[str]:
        """Get unique list of affected files."""
        files = set()
        for finding in findings:
            file_path = finding.get('file_path')
            if file_path:
                files.add(file_path)
        return sorted(list(files))
    
    def prioritize_root_causes(self, root_causes: List[Dict]) -> List[Dict]:
        """
        Prioritize root causes by severity and impact.
        
        Args:
            root_causes: List of root causes
            
        Returns:
            Sorted list of root causes (highest priority first)
        """
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        
        def priority_key(rc):
            severity = rc.get('severity', 'MEDIUM').upper()
            severity_score = severity_order.get(severity, 2)
            finding_count = len(rc.get('findings', []))
            confidence = rc.get('confidence', 0.5)
            
            # Lower score = higher priority
            return (severity_score, -finding_count, -confidence)
        
        return sorted(root_causes, key=priority_key)
    
    def get_fixable_root_causes(
        self,
        root_causes: List[Dict],
        min_confidence: float = 0.6,
    ) -> List[Dict]:
        """
        Get root causes that are safe to auto-fix.
        
        Args:
            root_causes: List of root causes
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of fixable root causes
        """
        fixable = []
        
        for rc in root_causes:
            confidence = rc.get('confidence', 0)
            severity = rc.get('severity', '').upper()
            
            # High confidence and not critical (critical needs review)
            if confidence >= min_confidence and severity != 'CRITICAL':
                fixable.append(rc)
        
        return fixable
    
    def get_review_required_root_causes(self, root_causes: List[Dict]) -> List[Dict]:
        """
        Get root causes that require human review.
        
        Args:
            root_causes: List of root causes
            
        Returns:
            List of root causes needing review
        """
        review_required = []
        
        for rc in root_causes:
            confidence = rc.get('confidence', 0)
            severity = rc.get('severity', '').upper()
            finding_count = len(rc.get('findings', []))
            
            # Low confidence, critical severity, or affects many files
            if confidence < 0.6 or severity == 'CRITICAL' or finding_count > 10:
                review_required.append(rc)
        
        return review_required
    
    def get_statistics(self, root_causes: List[Dict]) -> Dict:
        """
        Get statistics about root causes.
        
        Args:
            root_causes: List of root causes
            
        Returns:
            Statistics dict
        """
        stats = {
            'total_root_causes': len(root_causes),
            'by_severity': {
                'CRITICAL': 0,
                'HIGH': 0,
                'MEDIUM': 0,
                'LOW': 0,
            },
            'total_findings': 0,
            'fixable': 0,
            'needs_review': 0,
            'affected_files': set(),
        }
        
        for rc in root_causes:
            # Count by severity
            severity = rc.get('severity', 'MEDIUM').upper()
            if severity in stats['by_severity']:
                stats['by_severity'][severity] += 1
            
            # Count findings
            stats['total_findings'] += len(rc.get('findings', []))
            
            # Count fixable
            if rc.get('confidence', 0) >= 0.6 and severity != 'CRITICAL':
                stats['fixable'] += 1
            else:
                stats['needs_review'] += 1
            
            # Collect affected files
            for file_path in rc.get('affected_files', []):
                stats['affected_files'].add(file_path)
        
        stats['affected_files'] = len(stats['affected_files'])
        
        return stats
