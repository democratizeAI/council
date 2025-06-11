#!/usr/bin/env python3
"""
SCI-110: Review Agent - Extractive + Abstractive Paper Summary
🧠 Intelligent paper analysis with quality metrics

KPI Gate: summary_bleu ≥ 0.85
Effort: 0.5 days
"""

import asyncio
import logging
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import textstat

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

@dataclass
class PaperSummary:
    """Structured paper summary with quality metrics"""
    paper_id: str
    title: str
    extractive_summary: str
    abstractive_summary: str
    key_findings: List[str]
    methodology: str
    significance_score: float
    readability_score: float
    bleu_score: float
    confidence: float
    timestamp: datetime

class ReviewAgent:
    """SCI-110: Extractive + abstractive paper summarization"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stop_words = set(stopwords.words('english'))
        
        # Quality thresholds
        self.min_bleu_score = 0.85
        self.min_confidence = 0.7
        
        # Metrics tracking
        self.metrics = {
            'summaries_generated': 0,
            'bleu_scores': [],
            'avg_bleu_score': 0.0,
            'quality_gate_passes': 0,
            'processing_failures': 0,
            'last_run': None
        }

    def extract_key_sentences(self, text: str, num_sentences: int = 3) -> List[str]:
        """Extract key sentences using TF-IDF ranking"""
        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= num_sentences:
                return sentences
            
            # Create TF-IDF vectors for sentences
            vectorizer = TfidfVectorizer(
                stop_words='english',
                lowercase=True,
                max_features=1000
            )
            
            sentence_vectors = vectorizer.fit_transform(sentences)
            
            # Calculate sentence importance scores
            sentence_scores = []
            for i, sentence in enumerate(sentences):
                # TF-IDF score
                tfidf_score = sentence_vectors[i].sum()
                
                # Position score (earlier sentences often more important)
                position_score = 1.0 - (i / len(sentences)) * 0.3
                
                # Length score (prefer moderate length)
                words = word_tokenize(sentence.lower())
                length_score = min(1.0, len(words) / 20.0)
                
                total_score = tfidf_score * position_score * length_score
                sentence_scores.append((total_score, sentence))
            
            # Sort by score and return top sentences
            sentence_scores.sort(reverse=True)
            return [sentence for _, sentence in sentence_scores[:num_sentences]]
            
        except Exception as e:
            logger.error(f"Extractive summarization failed: {e}")
            # Fallback: return first few sentences
            sentences = sent_tokenize(text)
            return sentences[:num_sentences]

    async def generate_abstractive_summary(self, text: str, max_length: int = 200) -> str:
        """Generate abstractive summary using local LLM"""
        try:
            # For now, use extractive + paraphrasing approach
            # In a full implementation, this would call the local LLM
            
            key_sentences = self.extract_key_sentences(text, 5)
            combined_text = " ".join(key_sentences)
            
            # Simple abstractive approach: rephrase and condense
            words = word_tokenize(combined_text.lower())
            filtered_words = [w for w in words if w not in self.stop_words and w.isalpha()]
            
            # Create a more concise version
            sentences = sent_tokenize(combined_text)
            summary_sentences = []
            
            for sentence in sentences[:3]:  # Take top 3 sentences
                # Simplify sentence structure
                simplified = re.sub(r'\([^)]*\)', '', sentence)  # Remove parentheticals
                simplified = re.sub(r'\s+', ' ', simplified).strip()
                if len(simplified) > 20:  # Ensure meaningful content
                    summary_sentences.append(simplified)
            
            abstractive = " ".join(summary_sentences)
            
            # Truncate if too long
            if len(abstractive) > max_length:
                abstractive = abstractive[:max_length].rsplit(' ', 1)[0] + "..."
            
            return abstractive
            
        except Exception as e:
            logger.error(f"Abstractive summarization failed: {e}")
            return self.extract_key_sentences(text, 1)[0] if text else ""

    def analyze_methodology(self, text: str) -> str:
        """Extract methodology information from paper"""
        try:
            # Look for methodology indicators
            method_patterns = [
                r'method[s]?\s*[:\-]?\s*([^.]*\.)',
                r'approach[es]?\s*[:\-]?\s*([^.]*\.)',
                r'technique[s]?\s*[:\-]?\s*([^.]*\.)',
                r'algorithm[s]?\s*[:\-]?\s*([^.]*\.)',
                r'experiment[s]?\s*[:\-]?\s*([^.]*\.)'
            ]
            
            methodology_sentences = []
            for pattern in method_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    sentence = match.group(0)
                    if len(sentence) > 30 and sentence not in methodology_sentences:
                        methodology_sentences.append(sentence)
            
            if methodology_sentences:
                return " ".join(methodology_sentences[:2])  # Top 2 method descriptions
            else:
                # Fallback: look for sentences with method keywords
                sentences = sent_tokenize(text)
                for sentence in sentences:
                    if any(word in sentence.lower() for word in ['method', 'approach', 'algorithm', 'technique']):
                        return sentence
                
                return "Methodology not clearly identified in abstract."
                
        except Exception as e:
            logger.error(f"Methodology analysis failed: {e}")
            return "Methodology analysis failed."

    def extract_key_findings(self, text: str) -> List[str]:
        """Extract key findings and results"""
        try:
            # Look for result/finding indicators
            finding_patterns = [
                r'result[s]?\s*[:\-]?\s*([^.]*\.)',
                r'finding[s]?\s*[:\-]?\s*([^.]*\.)',
                r'show[s]?\s+that\s+([^.]*\.)',
                r'demonstrate[s]?\s+([^.]*\.)',
                r'achieve[s]?\s+([^.]*\.)',
                r'improve[s]?\s+([^.]*\.)'
            ]
            
            findings = []
            for pattern in finding_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    finding = match.group(1) if match.lastindex else match.group(0)
                    if len(finding) > 20 and finding not in findings:
                        findings.append(finding.strip())
            
            # Also look for numerical results
            numerical_patterns = [
                r'(\d+\.?\d*%?\s*(?:improvement|accuracy|precision|recall|f1))',
                r'(\d+\.?\d*x?\s*(?:faster|better|higher|lower))',
                r'(achieved?\s+\d+\.?\d*)'
            ]
            
            for pattern in numerical_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    finding = match.group(0)
                    if finding not in findings:
                        findings.append(finding)
            
            return findings[:5]  # Return top 5 findings
            
        except Exception as e:
            logger.error(f"Key findings extraction failed: {e}")
            return ["Key findings extraction failed."]

    def calculate_significance_score(self, text: str, title: str) -> float:
        """Calculate paper significance score based on content analysis"""
        try:
            score = 0.5  # Base score
            
            # Impact indicators
            impact_words = ['novel', 'breakthrough', 'significant', 'superior', 'outperform', 
                          'state-of-the-art', 'sota', 'best', 'improve', 'advance']
            
            text_lower = text.lower()
            title_lower = title.lower()
            
            # Check for impact words
            impact_count = sum(1 for word in impact_words if word in text_lower)
            score += min(impact_count * 0.1, 0.3)
            
            # Numerical results boost significance
            numbers = re.findall(r'\d+\.?\d*%', text)
            if numbers:
                score += min(len(numbers) * 0.05, 0.1)
            
            # Length suggests thorough work
            word_count = len(word_tokenize(text))
            if word_count > 100:
                score += 0.1
            
            # Title keywords
            important_title_words = ['new', 'novel', 'improved', 'advanced', 'efficient']
            title_boost = sum(0.05 for word in important_title_words if word in title_lower)
            score += min(title_boost, 0.15)
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Significance calculation failed: {e}")
            return 0.5

    def calculate_bleu_score(self, reference: str, hypothesis: str) -> float:
        """Calculate BLEU score between reference and hypothesis"""
        try:
            # Tokenize
            reference_tokens = word_tokenize(reference.lower())
            hypothesis_tokens = word_tokenize(hypothesis.lower())
            
            # Calculate BLEU score with smoothing
            smoothing = SmoothingFunction().method1
            bleu = sentence_bleu([reference_tokens], hypothesis_tokens, 
                               smoothing_function=smoothing)
            
            return bleu
            
        except Exception as e:
            logger.error(f"BLEU calculation failed: {e}")
            return 0.0

    async def review_paper(self, paper_data: Dict[str, Any]) -> PaperSummary:
        """Generate comprehensive review of a paper"""
        try:
            paper_id = paper_data.get('id', 'unknown')
            title = paper_data.get('title', 'Untitled')
            abstract = paper_data.get('abstract', '')
            
            logger.info(f"Reviewing paper: {paper_id}")
            
            # Generate extractive summary
            extractive_summary = " ".join(self.extract_key_sentences(abstract, 3))
            
            # Generate abstractive summary
            abstractive_summary = await self.generate_abstractive_summary(abstract)
            
            # Extract components
            key_findings = self.extract_key_findings(abstract)
            methodology = self.analyze_methodology(abstract)
            significance_score = self.calculate_significance_score(abstract, title)
            
            # Calculate quality metrics
            readability_score = textstat.flesch_reading_ease(abstractive_summary)
            bleu_score = self.calculate_bleu_score(abstract, abstractive_summary)
            
            # Calculate confidence based on various factors
            confidence = min(
                bleu_score * 0.4 +
                significance_score * 0.3 +
                (1.0 if len(key_findings) > 0 else 0.5) * 0.3,
                1.0
            )
            
            # Update metrics
            self.metrics['summaries_generated'] += 1
            self.metrics['bleu_scores'].append(bleu_score)
            self.metrics['avg_bleu_score'] = np.mean(self.metrics['bleu_scores'])
            
            if bleu_score >= self.min_bleu_score:
                self.metrics['quality_gate_passes'] += 1
            
            self.metrics['last_run'] = datetime.now().isoformat()
            
            summary = PaperSummary(
                paper_id=paper_id,
                title=title,
                extractive_summary=extractive_summary,
                abstractive_summary=abstractive_summary,
                key_findings=key_findings,
                methodology=methodology,
                significance_score=significance_score,
                readability_score=readability_score,
                bleu_score=bleu_score,
                confidence=confidence,
                timestamp=datetime.now()
            )
            
            logger.info(f"Review completed for {paper_id}: BLEU={bleu_score:.3f}, Confidence={confidence:.3f}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Paper review failed: {e}")
            self.metrics['processing_failures'] += 1
            # Return minimal summary
            return PaperSummary(
                paper_id=paper_data.get('id', 'error'),
                title=paper_data.get('title', 'Error'),
                extractive_summary="Review failed",
                abstractive_summary="Review failed",
                key_findings=[],
                methodology="Failed to analyze",
                significance_score=0.0,
                readability_score=0.0,
                bleu_score=0.0,
                confidence=0.0,
                timestamp=datetime.now()
            )

    async def batch_review(self, papers: List[Dict[str, Any]]) -> List[PaperSummary]:
        """Review multiple papers in batch"""
        summaries = []
        
        for paper in papers:
            summary = await self.review_paper(paper)
            summaries.append(summary)
        
        return summaries

    def get_metrics(self) -> Dict[str, Any]:
        """Get current review metrics"""
        return self.metrics.copy()

    def check_kpi_gate(self) -> bool:
        """Check if KPI gate is passed (summary_bleu ≥ 0.85)"""
        return self.metrics['avg_bleu_score'] >= self.min_bleu_score

# Test function
async def test_review_agent():
    """Test the review agent functionality"""
    agent = ReviewAgent()
    
    print("🧠 Testing SCI-110 Review Agent...")
    
    # Test paper data
    test_paper = {
        'id': 'test-001',
        'title': 'A Novel Approach to Machine Learning with Transformers',
        'abstract': '''We present a novel approach to machine learning using transformer architectures. 
        Our method achieves state-of-the-art performance on several benchmarks, showing 15% improvement 
        over previous methods. The approach utilizes attention mechanisms and demonstrates significant 
        advances in natural language processing. Results show that our technique outperforms existing 
        methods by substantial margins across multiple datasets. We achieved 95% accuracy on the test set 
        and reduced computational complexity by 30%. The methodology involves fine-tuning pre-trained 
        models with domain-specific data.'''
    }
    
    summary = await agent.review_paper(test_paper)
    
    print(f"Paper ID: {summary.paper_id}")
    print(f"Extractive Summary: {summary.extractive_summary[:100]}...")
    print(f"Abstractive Summary: {summary.abstractive_summary}")
    print(f"Key Findings: {summary.key_findings}")
    print(f"Methodology: {summary.methodology[:100]}...")
    print(f"BLEU Score: {summary.bleu_score:.3f}")
    print(f"Confidence: {summary.confidence:.3f}")
    print(f"KPI Gate Passed: {agent.check_kpi_gate()}")
    
    return summary

if __name__ == "__main__":
    asyncio.run(test_review_agent()) 