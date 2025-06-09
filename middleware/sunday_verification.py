"""
Sunday Verification Middleware
Enforces the Sunday Verification Principle for all Trinity agent responses.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VerificationResult:
    """Result of Sunday Verification check"""
    compliant: bool
    score: float  # 0.0 to 1.0
    issues: List[str]
    suggestions: List[str]
    evidence_markers: List[str]

class SundayVerificationEngine:
    """Core engine for enforcing Sunday Verification Principle"""
    
    def __init__(self):
        # Evidence markers that indicate verification
        self.evidence_markers = [
            "verified:", "checked:", "tested:", "measured:",
            "confirmed:", "validated:", "proven:",
            "evidence:", "metrics show:", "data indicates:",
            "actual:", "real:", "concrete:", "specific:",
            "p95", "latency", "response time", "error rate",
            "containers running", "health check", "status code",
            "cpu", "memory", "disk", "network",
            "✅", "❌", "📊", "🔍"
        ]
        
        # Claim words that require verification
        self.claim_words = [
            "working", "operational", "successful", "ready",
            "deployed", "running", "healthy", "stable",
            "fixed", "resolved", "completed", "finished",
            "good", "fine", "ok", "normal", "optimal"
        ]
        
        # Vague phrases to avoid
        self.vague_phrases = [
            "looks good", "seems fine", "appears to be",
            "everything is", "all good", "no issues",
            "working fine", "running well", "should work",
            "probably", "might be", "could be"
        ]
        
        # Sunday voice phrases (bonus points)
        self.sunday_phrases = [
            "trust but verify", "show your work", "not smoke and mirrors",
            "the pattern is the pattern", "real metrics", "concrete evidence",
            "sunday calm", "measured analysis", "weights remember"
        ]

    def analyze_response(self, response_text: str) -> VerificationResult:
        """Analyze a response against Sunday Verification Principle"""
        
        text_lower = response_text.lower()
        issues = []
        suggestions = []
        evidence_found = []
        score = 0.0
        
        # Check for evidence markers
        for marker in self.evidence_markers:
            if marker in text_lower:
                evidence_found.append(marker)
                score += 0.1
        
        # Check for claims without verification
        claims_found = []
        for claim in self.claim_words:
            if claim in text_lower:
                claims_found.append(claim)
        
        # Check for vague phrases (penalty)
        vague_found = []
        for vague in self.vague_phrases:
            if vague in text_lower:
                vague_found.append(vague)
                score -= 0.2
                issues.append(f"Vague phrase detected: '{vague}'")
                suggestions.append(f"Replace '{vague}' with specific evidence")
        
        # Check for Sunday voice (bonus)
        sunday_found = []
        for phrase in self.sunday_phrases:
            if phrase in text_lower:
                sunday_found.append(phrase)
                score += 0.15
        
        # Evaluate claims vs evidence ratio
        if claims_found and not evidence_found:
            issues.append("Makes claims without providing verification evidence")
            suggestions.append("Add concrete metrics, test results, or specific data points")
            score -= 0.3
        elif claims_found and evidence_found:
            score += 0.2  # Good: claims backed by evidence
        
        # Check for specific numbers/metrics
        numbers_pattern = r'\b\d+(?:\.\d+)?(?:ms|%|GB|MB|KB|seconds?|minutes?)\b'
        if re.search(numbers_pattern, response_text):
            score += 0.2
            evidence_found.append("specific_metrics")
        
        # Normalize score
        score = max(0.0, min(1.0, score))
        
        # Determine compliance (threshold: 0.6)
        compliant = score >= 0.6 and len(issues) == 0
        
        return VerificationResult(
            compliant=compliant,
            score=score,
            issues=issues,
            suggestions=suggestions,
            evidence_markers=evidence_found
        )

    def format_feedback(self, result: VerificationResult) -> str:
        """Format verification feedback for agent response"""
        
        if result.compliant:
            return f"✅ Sunday Verification: COMPLIANT (score: {result.score:.2f})"
        
        feedback = [f"⚠️ Sunday Verification: NEEDS IMPROVEMENT (score: {result.score:.2f})"]
        
        if result.issues:
            feedback.append("\nIssues:")
            for issue in result.issues:
                feedback.append(f"  • {issue}")
        
        if result.suggestions:
            feedback.append("\nSuggestions:")
            for suggestion in result.suggestions:
                feedback.append(f"  • {suggestion}")
        
        if result.evidence_markers:
            feedback.append(f"\nEvidence found: {', '.join(result.evidence_markers)}")
        
        feedback.append("\nRemember: Show your work. Trust but verify. 🔍")
        
        return "\n".join(feedback)

# Global instance
sunday_verifier = SundayVerificationEngine()

def validate_sunday_principle(response_text: str) -> Dict[str, Any]:
    """
    Validate a response against the Sunday Verification Principle.
    
    Args:
        response_text: The agent response to validate
        
    Returns:
        Dictionary with validation results
    """
    try:
        result = sunday_verifier.analyze_response(response_text)
        
        return {
            "sunday_compliant": result.compliant,
            "sunday_score": result.score,
            "sunday_feedback": sunday_verifier.format_feedback(result),
            "evidence_markers": result.evidence_markers,
            "improvement_needed": len(result.issues) > 0
        }
    
    except Exception as e:
        logger.error(f"Sunday verification failed: {e}")
        return {
            "sunday_compliant": False,
            "sunday_score": 0.0,
            "sunday_feedback": f"Verification error: {e}",
            "evidence_markers": [],
            "improvement_needed": True
        }

def enforce_sunday_principle(response_text: str) -> str:
    """
    Enforce Sunday Verification Principle on response.
    Returns enhanced response with verification feedback if needed.
    """
    validation = validate_sunday_principle(response_text)
    
    if validation["sunday_compliant"]:
        # Already compliant, just log success
        logger.info(f"Sunday verification passed: score {validation['sunday_score']:.2f}")
        return response_text
    
    # Not compliant, append feedback
    enhanced_response = response_text + "\n\n" + validation["sunday_feedback"]
    
    logger.warning(f"Sunday verification failed: score {validation['sunday_score']:.2f}")
    return enhanced_response

# FastAPI middleware integration
async def sunday_verification_middleware(request, call_next):
    """FastAPI middleware to enforce Sunday Verification Principle"""
    
    response = await call_next(request)
    
    # Only check agent responses (not system endpoints)
    if hasattr(response, 'body') and request.url.path.startswith('/'):
        try:
            # For agent responses, validate Sunday compliance
            # This would be integrated with the actual response processing
            pass
        except Exception as e:
            logger.error(f"Sunday verification middleware error: {e}")
    
    return response 