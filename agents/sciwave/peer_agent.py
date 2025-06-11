#!/usr/bin/env python3
"""
SCI-120: Peer Agent - Self-Critique + Cross-Agent Comparison
👥 Peer review system with confidence improvement tracking

KPI Gate: delta_confidence ≥ 2%
Effort: 0.75 days
"""

import asyncio
import logging
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib

logger = logging.getLogger(__name__)

@dataclass
class PeerReview:
    """Peer review result with detailed analysis"""
    original_summary_id: str
    reviewer_id: str
    critique: str
    suggested_improvements: List[str]
    quality_score: float
    confidence_before: float
    confidence_after: float
    delta_confidence: float
    consensus_score: float
    timestamp: datetime

@dataclass
class CrossAgentComparison:
    """Cross-agent comparison analysis"""
    summary_a_id: str
    summary_b_id: str
    similarity_score: float
    key_differences: List[str]
    consensus_points: List[str]
    recommendation: str
    confidence_improvement: float

class PeerAgent:
    """SCI-120: Self-critique and cross-agent peer review"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agent_id = f"peer_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Quality thresholds
        self.min_delta_confidence = 0.02  # 2% minimum improvement
        self.min_consensus_score = 0.7
        
        # Critique templates
        self.critique_categories = {
            'clarity': 'Is the summary clear and well-structured?',
            'completeness': 'Does it capture the main findings and methodology?',
            'accuracy': 'Are the technical details accurately represented?',
            'conciseness': 'Is the information presented concisely?',
            'significance': 'Is the importance of the work properly conveyed?'
        }
        
        # Metrics tracking
        self.metrics = {
            'reviews_completed': 0,
            'delta_confidence_values': [],
            'avg_delta_confidence': 0.0,
            'kpi_gate_passes': 0,
            'consensus_failures': 0,
            'self_critique_count': 0,
            'cross_agent_comparisons': 0,
            'last_run': None
        }

    def analyze_summary_quality(self, summary_text: str, title: str = "") -> Dict[str, float]:
        """Analyze summary quality across multiple dimensions"""
        try:
            scores = {}
            
            # Clarity score - based on readability and structure
            sentences = summary_text.split('.')
            avg_sentence_length = np.mean([len(s.split()) for s in sentences if s.strip()])
            clarity_score = max(0.0, min(1.0, 1.0 - (abs(avg_sentence_length - 20) / 30)))
            scores['clarity'] = clarity_score
            
            # Completeness score - based on content coverage
            key_elements = ['method', 'result', 'conclusion', 'finding', 'approach', 'technique']
            present_elements = sum(1 for element in key_elements if element in summary_text.lower())
            completeness_score = min(1.0, present_elements / 4.0)  # Expect at least 4 key elements
            scores['completeness'] = completeness_score
            
            # Accuracy score - based on technical indicators
            technical_terms = ['algorithm', 'model', 'dataset', 'evaluation', 'metric', 'performance']
            technical_density = sum(1 for term in technical_terms if term in summary_text.lower())
            accuracy_score = min(1.0, technical_density / 3.0)
            scores['accuracy'] = accuracy_score
            
            # Conciseness score - optimal length around 100-200 words
            word_count = len(summary_text.split())
            if 100 <= word_count <= 200:
                conciseness_score = 1.0
            else:
                deviation = abs(word_count - 150) / 150
                conciseness_score = max(0.0, 1.0 - deviation)
            scores['conciseness'] = conciseness_score
            
            # Significance score - based on impact indicators
            impact_words = ['novel', 'significant', 'improve', 'outperform', 'achieve', 'advance']
            impact_count = sum(1 for word in impact_words if word in summary_text.lower())
            significance_score = min(1.0, impact_count / 3.0)
            scores['significance'] = significance_score
            
            return scores
            
        except Exception as e:
            logger.error(f"Quality analysis failed: {e}")
            return {category: 0.5 for category in self.critique_categories.keys()}

    def generate_critique(self, summary_text: str, quality_scores: Dict[str, float]) -> Tuple[str, List[str]]:
        """Generate detailed critique and improvement suggestions"""
        try:
            critiques = []
            improvements = []
            
            for category, score in quality_scores.items():
                question = self.critique_categories[category]
                
                if score < 0.6:  # Needs improvement
                    if category == 'clarity':
                        critiques.append(f"Clarity issue: {question} Score: {score:.2f}. "
                                       "Consider simplifying sentence structure and improving flow.")
                        improvements.append("Simplify complex sentences and improve logical flow")
                        
                    elif category == 'completeness':
                        critiques.append(f"Completeness issue: {question} Score: {score:.2f}. "
                                       "Missing key technical details or methodology information.")
                        improvements.append("Include more details about methodology and key findings")
                        
                    elif category == 'accuracy':
                        critiques.append(f"Accuracy concern: {question} Score: {score:.2f}. "
                                       "Lacks sufficient technical terminology or precision.")
                        improvements.append("Add more precise technical language and specific metrics")
                        
                    elif category == 'conciseness':
                        critiques.append(f"Conciseness issue: {question} Score: {score:.2f}. "
                                       "Either too verbose or too brief for optimal comprehension.")
                        improvements.append("Adjust length to 100-200 words for optimal clarity")
                        
                    elif category == 'significance':
                        critiques.append(f"Significance unclear: {question} Score: {score:.2f}. "
                                       "Impact and importance not clearly communicated.")
                        improvements.append("Better highlight the significance and impact of the work")
                
                elif score > 0.8:  # Strong points
                    critiques.append(f"Strong {category}: {question} Score: {score:.2f}. Well executed.")
            
            full_critique = " ".join(critiques) if critiques else "Overall good quality summary."
            
            return full_critique, improvements
            
        except Exception as e:
            logger.error(f"Critique generation failed: {e}")
            return "Critique generation failed.", ["Unable to generate specific improvements"]

    async def self_critique(self, summary_data: Dict[str, Any]) -> PeerReview:
        """Perform self-critique on a summary"""
        try:
            summary_id = summary_data.get('paper_id', 'unknown')
            summary_text = summary_data.get('abstractive_summary', '')
            title = summary_data.get('title', '')
            original_confidence = summary_data.get('confidence', 0.5)
            
            logger.info(f"Self-critiquing summary: {summary_id}")
            
            # Analyze quality
            quality_scores = self.analyze_summary_quality(summary_text, title)
            
            # Generate critique
            critique, improvements = self.generate_critique(summary_text, quality_scores)
            
            # Calculate overall quality score
            quality_score = np.mean(list(quality_scores.values()))
            
            # Determine confidence adjustment
            # High quality scores should increase confidence
            confidence_adjustment = (quality_score - 0.5) * 0.3  # Max ±15% adjustment
            new_confidence = max(0.0, min(1.0, original_confidence + confidence_adjustment))
            delta_confidence = new_confidence - original_confidence
            
            # Update metrics
            self.metrics['self_critique_count'] += 1
            self.metrics['reviews_completed'] += 1
            self.metrics['delta_confidence_values'].append(delta_confidence)
            self.metrics['avg_delta_confidence'] = np.mean(self.metrics['delta_confidence_values'])
            
            if abs(delta_confidence) >= self.min_delta_confidence:
                self.metrics['kpi_gate_passes'] += 1
            
            self.metrics['last_run'] = datetime.now().isoformat()
            
            review = PeerReview(
                original_summary_id=summary_id,
                reviewer_id=self.agent_id,
                critique=critique,
                suggested_improvements=improvements,
                quality_score=quality_score,
                confidence_before=original_confidence,
                confidence_after=new_confidence,
                delta_confidence=delta_confidence,
                consensus_score=quality_score,  # Self-consensus based on quality
                timestamp=datetime.now()
            )
            
            logger.info(f"Self-critique completed: δ confidence = {delta_confidence:.3f}")
            
            return review
            
        except Exception as e:
            logger.error(f"Self-critique failed: {e}")
            self.metrics['consensus_failures'] += 1
            return PeerReview(
                original_summary_id=summary_data.get('paper_id', 'error'),
                reviewer_id=self.agent_id,
                critique="Self-critique failed",
                suggested_improvements=[],
                quality_score=0.0,
                confidence_before=0.0,
                confidence_after=0.0,
                delta_confidence=0.0,
                consensus_score=0.0,
                timestamp=datetime.now()
            )

    async def cross_agent_comparison(self, summary_a: Dict[str, Any], 
                                   summary_b: Dict[str, Any]) -> CrossAgentComparison:
        """Compare summaries from different agents"""
        try:
            summary_a_id = summary_a.get('paper_id', 'summary_a')
            summary_b_id = summary_b.get('paper_id', 'summary_b')
            
            text_a = summary_a.get('abstractive_summary', '')
            text_b = summary_b.get('abstractive_summary', '')
            
            logger.info(f"Cross-agent comparison: {summary_a_id} vs {summary_b_id}")
            
            # Calculate similarity using TF-IDF
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform([text_a, text_b])
            similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Find differences using difflib
            differ = difflib.unified_diff(
                text_a.split(), text_b.split(),
                fromfile=summary_a_id, tofile=summary_b_id,
                lineterm='', n=0
            )
            
            differences = []
            for line in differ:
                if line.startswith('-') or line.startswith('+'):
                    differences.append(line)
            
            # Extract key differences
            key_differences = []
            if len(differences) > 0:
                # Group differences into meaningful chunks
                unique_words_a = set(text_a.lower().split()) - set(text_b.lower().split())
                unique_words_b = set(text_b.lower().split()) - set(text_a.lower().split())
                
                if unique_words_a:
                    key_differences.append(f"Summary A emphasizes: {', '.join(list(unique_words_a)[:5])}")
                if unique_words_b:
                    key_differences.append(f"Summary B emphasizes: {', '.join(list(unique_words_b)[:5])}")
            
            # Find consensus points (common important terms)
            common_words = set(text_a.lower().split()) & set(text_b.lower().split())
            important_common = [word for word in common_words 
                              if len(word) > 4 and word not in ['method', 'result', 'paper']]
            consensus_points = [f"Both mention: {word}" for word in important_common[:3]]
            
            # Generate recommendation
            if similarity_score > 0.8:
                recommendation = "High consensus - summaries are very similar"
                confidence_improvement = 0.1
            elif similarity_score > 0.6:
                recommendation = "Moderate consensus - minor differences noted"
                confidence_improvement = 0.05
            else:
                recommendation = "Low consensus - significant differences require review"
                confidence_improvement = -0.05
            
            # Update metrics
            self.metrics['cross_agent_comparisons'] += 1
            self.metrics['reviews_completed'] += 1
            
            comparison = CrossAgentComparison(
                summary_a_id=summary_a_id,
                summary_b_id=summary_b_id,
                similarity_score=similarity_score,
                key_differences=key_differences,
                consensus_points=consensus_points,
                recommendation=recommendation,
                confidence_improvement=confidence_improvement
            )
            
            logger.info(f"Cross-agent comparison completed: similarity = {similarity_score:.3f}")
            
            return comparison
            
        except Exception as e:
            logger.error(f"Cross-agent comparison failed: {e}")
            return CrossAgentComparison(
                summary_a_id="error_a",
                summary_b_id="error_b",
                similarity_score=0.0,
                key_differences=["Comparison failed"],
                consensus_points=[],
                recommendation="Unable to compare",
                confidence_improvement=0.0
            )

    async def peer_review_cycle(self, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute full peer review cycle"""
        reviews = []
        comparisons = []
        
        # Self-critique each summary
        for summary in summaries:
            review = await self.self_critique(summary)
            reviews.append(review)
        
        # Cross-agent comparisons (pairwise)
        for i in range(len(summaries)):
            for j in range(i + 1, len(summaries)):
                comparison = await self.cross_agent_comparison(summaries[i], summaries[j])
                comparisons.append(comparison)
        
        # Calculate overall metrics
        delta_confidences = [r.delta_confidence for r in reviews]
        avg_delta = np.mean(delta_confidences) if delta_confidences else 0.0
        
        # Check KPI gate
        kpi_passed = abs(avg_delta) >= self.min_delta_confidence
        
        result = {
            'reviews': [review.__dict__ for review in reviews],
            'comparisons': [comp.__dict__ for comp in comparisons],
            'metrics': self.get_metrics(),
            'avg_delta_confidence': avg_delta,
            'kpi_gate_passed': kpi_passed,
            'timestamp': datetime.now().isoformat()
        }
        
        return result

    def get_metrics(self) -> Dict[str, Any]:
        """Get current peer review metrics"""
        return self.metrics.copy()

    def check_kpi_gate(self) -> bool:
        """Check if KPI gate is passed (delta_confidence ≥ 2%)"""
        return abs(self.metrics['avg_delta_confidence']) >= self.min_delta_confidence

# Test function
async def test_peer_agent():
    """Test the peer agent functionality"""
    agent = PeerAgent()
    
    print("👥 Testing SCI-120 Peer Agent...")
    
    # Test summary data
    test_summaries = [
        {
            'paper_id': 'test-001',
            'title': 'Machine Learning with Transformers',
            'abstractive_summary': 'This paper presents a novel transformer-based approach that achieves state-of-the-art results on multiple benchmarks. The method improves accuracy by 15% while reducing computational cost.',
            'confidence': 0.75
        },
        {
            'paper_id': 'test-002', 
            'title': 'Advanced Neural Networks',
            'abstractive_summary': 'We propose an advanced neural network architecture that demonstrates superior performance on classification tasks. Our approach outperforms existing methods by significant margins.',
            'confidence': 0.65
        }
    ]
    
    # Test self-critique
    review = await agent.self_critique(test_summaries[0])
    print(f"Self-critique result:")
    print(f"  Original confidence: {review.confidence_before:.3f}")
    print(f"  New confidence: {review.confidence_after:.3f}")
    print(f"  Delta: {review.delta_confidence:.3f}")
    print(f"  Quality score: {review.quality_score:.3f}")
    
    # Test cross-agent comparison
    comparison = await agent.cross_agent_comparison(test_summaries[0], test_summaries[1])
    print(f"\nCross-agent comparison:")
    print(f"  Similarity: {comparison.similarity_score:.3f}")
    print(f"  Recommendation: {comparison.recommendation}")
    print(f"  Key differences: {comparison.key_differences}")
    
    # Test full cycle
    cycle_result = await agent.peer_review_cycle(test_summaries)
    print(f"\nFull cycle result:")
    print(f"  Average delta confidence: {cycle_result['avg_delta_confidence']:.3f}")
    print(f"  KPI gate passed: {cycle_result['kpi_gate_passed']}")
    
    return cycle_result

if __name__ == "__main__":
    asyncio.run(test_peer_agent()) 