"""Security analyzer - verifies findings using LLM."""

import asyncio
from typing import Dict, List
from bcb.analyzer.llm_client import BobLLMClient


class SecurityAnalyzer:
    """Analyzes and verifies security findings using IBM Bob LLM."""

    def __init__(self, llm_client: BobLLMClient):
        self.llm_client = llm_client

    def verify_findings(
        self,
        findings: List[Dict],
        codebase_info: Dict,
    ) -> List[Dict]:
        """
        Verify findings using LLM.

        When no API key is configured or the API is unreachable, returns
        all static findings unchanged (confidence stays at 0.5).
        """
        if not findings:
            return []

        # Skip LLM if no API key — return all static findings as-is
        if not self.llm_client.api_key:
            return findings

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            verified = loop.run_until_complete(
                self._verify_async(findings, codebase_info)
            )
            return verified
        except Exception:
            # API unreachable — fall back to static findings
            return findings
        finally:
            try:
                loop.run_until_complete(self.llm_client.close())
            except Exception:
                pass
            loop.close()
            asyncio.set_event_loop(None)
    
    async def _verify_async(
        self,
        findings: List[Dict],
        codebase_info: Dict,
    ) -> List[Dict]:
        """Async verification of findings."""
        # Verify in batches
        responses = await self.llm_client.verify_findings_batch(
            findings,
            codebase_info,
        )
        
        # Update findings with verification results
        verified_findings = []
        
        for finding, response in zip(findings, responses):
            if response.is_vulnerable:
                # Update finding with LLM results
                finding['verified'] = True
                finding['confidence'] = response.confidence
                finding['llm_reasoning'] = response.reasoning
                
                if response.blast_radius:
                    finding['blast_radius'] = response.blast_radius
                
                if response.affected_lines:
                    finding['affected_lines'] = response.affected_lines
                
                # Only include high-confidence findings
                if response.confidence >= 0.5:
                    verified_findings.append(finding)
        
        return verified_findings
    
    def categorize_by_severity(self, findings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize findings by severity.
        
        Args:
            findings: List of findings
            
        Returns:
            Dict mapping severity to list of findings
        """
        categories = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': [],
        }
        
        for finding in findings:
            severity = finding.get('severity', 'MEDIUM').upper()
            if severity in categories:
                categories[severity].append(finding)
        
        return categories
    
    def get_severity_stats(self, findings: List[Dict]) -> Dict[str, int]:
        """
        Get statistics by severity.
        
        Args:
            findings: List of findings
            
        Returns:
            Dict with counts per severity
        """
        stats = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0,
            'total': len(findings),
        }
        
        for finding in findings:
            severity = finding.get('severity', 'MEDIUM').upper()
            if severity in stats:
                stats[severity] += 1
        
        return stats
    
    def filter_by_confidence(
        self,
        findings: List[Dict],
        min_confidence: float = 0.5,
    ) -> List[Dict]:
        """
        Filter findings by confidence threshold.
        
        Args:
            findings: List of findings
            min_confidence: Minimum confidence score (0-1)
            
        Returns:
            Filtered list of findings
        """
        return [
            f for f in findings
            if f.get('confidence', 0) >= min_confidence
        ]
    
    def group_by_file(self, findings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group findings by file.
        
        Args:
            findings: List of findings
            
        Returns:
            Dict mapping file path to list of findings
        """
        grouped = {}
        
        for finding in findings:
            file_path = finding.get('file_path', 'unknown')
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append(finding)
        
        return grouped
    
    def group_by_pattern(self, findings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group findings by pattern ID.
        
        Args:
            findings: List of findings
            
        Returns:
            Dict mapping pattern ID to list of findings
        """
        grouped = {}
        
        for finding in findings:
            pattern_id = finding.get('id', 'unknown')
            if pattern_id not in grouped:
                grouped[pattern_id] = []
            grouped[pattern_id].append(finding)
        
        return grouped
    
    def get_high_priority_findings(self, findings: List[Dict]) -> List[Dict]:
        """
        Get high-priority findings (CRITICAL and HIGH severity with high confidence).
        
        Args:
            findings: List of findings
            
        Returns:
            List of high-priority findings
        """
        high_priority = []
        
        for finding in findings:
            severity = finding.get('severity', '').upper()
            confidence = finding.get('confidence', 0)
            
            if severity in ['CRITICAL', 'HIGH'] and confidence >= 0.7:
                high_priority.append(finding)
        
        # Sort by severity then confidence
        severity_order = {'CRITICAL': 0, 'HIGH': 1}
        high_priority.sort(
            key=lambda f: (
                severity_order.get(f.get('severity', '').upper(), 2),
                -f.get('confidence', 0)
            )
        )
        
        return high_priority
    
    def needs_human_review(self, finding: Dict) -> bool:
        """
        Determine if a finding needs human review.
        
        Args:
            finding: Finding dict
            
        Returns:
            True if human review is needed
        """
        # Low confidence findings need review
        if finding.get('confidence', 0) < 0.6:
            return True
        
        # Critical findings always need review before auto-fix
        if finding.get('severity', '').upper() == 'CRITICAL':
            return True
        
        # Findings with high blast radius need review
        blast_radius = finding.get('blast_radius', '')
        if 'high' in blast_radius.lower() or 'critical' in blast_radius.lower():
            return True
        
        return False
    
    def calculate_risk_score(self, finding: Dict) -> float:
        """
        Calculate overall risk score for a finding.
        
        Args:
            finding: Finding dict
            
        Returns:
            Risk score (0-10)
        """
        # Base score from severity
        severity_scores = {
            'CRITICAL': 10.0,
            'HIGH': 7.5,
            'MEDIUM': 5.0,
            'LOW': 2.5,
        }
        
        severity = finding.get('severity', 'MEDIUM').upper()
        base_score = severity_scores.get(severity, 5.0)
        
        # Adjust by confidence
        confidence = finding.get('confidence', 0.5)
        adjusted_score = base_score * confidence
        
        # Adjust by blast radius
        blast_radius = finding.get('blast_radius', '').lower()
        if 'high' in blast_radius or 'critical' in blast_radius:
            adjusted_score *= 1.2
        elif 'low' in blast_radius or 'minimal' in blast_radius:
            adjusted_score *= 0.8
        
        return min(10.0, adjusted_score)
