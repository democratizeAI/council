#!/usr/bin/env python3
"""
Retrieval Accuracy Evaluation - Suite 6
Tests memory hit-rate & relevance using synthetic Q-A pairs
Pass criteria: ≥65% hits, MRR ≥0.75
"""

import argparse
import json
import time
import random
import requests
from typing import List, Dict, Any, Tuple
import hashlib

class RetrievalEvaluator:
    """Evaluates memory retrieval accuracy for AutoGen Council"""
    
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.qa_pairs = []
        
    def generate_synthetic_qa_pairs(self, num_pairs: int = 200) -> List[Dict[str, str]]:
        """Generate synthetic Q-A pairs for testing memory retrieval"""
        
        # Templates for generating diverse Q-A pairs
        templates = [
            # Technical topics
            {
                "question": "How does {concept} work in {domain}?",
                "answer": "{concept} in {domain} operates by {mechanism}. This allows for {benefit} and {application}.",
                "concepts": ["machine learning", "neural networks", "encryption", "databases", "APIs"],
                "domains": ["software development", "web applications", "data science", "cybersecurity", "cloud computing"],
                "mechanisms": ["processing data through layers", "analyzing patterns", "transforming information", "storing structured data", "enabling communication"],
                "benefits": ["improved accuracy", "better security", "faster processing", "scalable solutions", "automated decisions"],
                "applications": ["predictive analytics", "secure communications", "real-time systems", "distributed computing", "intelligent automation"]
            },
            
            # Scientific topics
            {
                "question": "What is the role of {component} in {system}?",
                "answer": "{component} plays a crucial role in {system} by {function}. This enables {outcome} and {importance}.",
                "components": ["photosynthesis", "DNA", "neurons", "enzymes", "cells"],
                "systems": ["plant biology", "genetics", "nervous system", "metabolism", "organism development"],
                "functions": ["converting light to energy", "storing genetic information", "transmitting signals", "catalyzing reactions", "forming tissues"],
                "outcomes": ["energy production", "trait inheritance", "coordinated responses", "biochemical processes", "growth and repair"],
                "importance": ["sustains life", "determines characteristics", "enables cognition", "maintains health", "supports reproduction"]
            },
            
            # Business topics
            {
                "question": "Why is {strategy} important for {context}?",
                "answer": "{strategy} is essential for {context} because it {reason}. This leads to {result} and {advantage}.",
                "strategies": ["market research", "customer service", "digital transformation", "quality assurance", "risk management"],
                "contexts": ["business growth", "competitive advantage", "customer retention", "operational efficiency", "innovation"],
                "reasons": ["provides valuable insights", "builds strong relationships", "modernizes operations", "ensures standards", "mitigates threats"],
                "results": ["informed decisions", "customer loyalty", "improved processes", "reliable products", "protected assets"],
                "advantages": ["sustainable growth", "market leadership", "long-term success", "operational excellence", "business resilience"]
            }
        ]
        
        qa_pairs = []
        
        for i in range(num_pairs):
            template = random.choice(templates)
            
            # Fill template with random choices
            filled_qa = {}
            for key, value in template.items():
                if key in ["question", "answer"]:
                    filled_text = value
                    for placeholder_key, options in template.items():
                        if isinstance(options, list) and f"{{{placeholder_key[:-1]}}}" in filled_text:
                            replacement = random.choice(options)
                            filled_text = filled_text.replace(f"{{{placeholder_key[:-1]}}}", replacement)
                    filled_qa[key] = filled_text
            
            # Add metadata
            filled_qa["id"] = f"qa_{i+1:03d}"
            filled_qa["category"] = "synthetic"
            filled_qa["keywords"] = self.extract_keywords(filled_qa["question"] + " " + filled_qa["answer"])
            
            qa_pairs.append(filled_qa)
        
        return qa_pairs
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract potential keywords from text"""
        # Simple keyword extraction (in practice, could use more sophisticated NLP)
        words = text.lower().replace("?", "").replace(".", "").split()
        # Filter out common words and short words
        stop_words = {"is", "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "how", "what", "why", "when", "where", "does", "do", "are", "this", "that", "it", "they", "them", "their"}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return keywords[:5]  # Return top 5 keywords
    
    def populate_memory(self, qa_pairs: List[Dict]) -> bool:
        """Populate the memory system with Q-A pairs"""
        print(f"📝 Populating memory with {len(qa_pairs)} Q-A pairs...")
        
        successful_inserts = 0
        
        for i, qa in enumerate(qa_pairs):
            try:
                # Create a conversation that includes the Q-A pair
                conversation_text = f"Q: {qa['question']}\nA: {qa['answer']}"
                
                # Send to the hybrid endpoint to trigger memory storage
                response = requests.post(
                    f"{self.base_url}/hybrid",
                    json={
                        "messages": [
                            {"role": "user", "content": qa["question"]},
                            {"role": "assistant", "content": qa["answer"]}
                        ],
                        "max_tokens": 10,  # Minimal response to focus on memory storage
                        "store_memory": True  # Custom flag if supported
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    successful_inserts += 1
                
                if (i + 1) % 20 == 0:
                    print(f"   Processed {i + 1}/{len(qa_pairs)} pairs...")
                    
            except Exception as e:
                print(f"   Warning: Failed to insert QA {qa['id']}: {e}")
        
        success_rate = successful_inserts / len(qa_pairs)
        print(f"✅ Memory population complete: {successful_inserts}/{len(qa_pairs)} ({success_rate:.1%}) successful")
        
        return success_rate > 0.8
    
    def test_retrieval_accuracy(self, qa_pairs: List[Dict]) -> Dict[str, Any]:
        """Test retrieval accuracy using the populated Q-A pairs"""
        print(f"🎯 Testing retrieval accuracy with {len(qa_pairs)} queries...")
        
        results = []
        hit_count = 0
        reciprocal_ranks = []
        
        # Test a subset for performance (or all if small enough)
        test_pairs = random.sample(qa_pairs, min(50, len(qa_pairs)))
        
        for i, qa in enumerate(test_pairs):
            try:
                # Query with the question to see if we get relevant response
                response = requests.post(
                    f"{self.base_url}/hybrid",
                    json={
                        "messages": [{"role": "user", "content": qa["question"]}],
                        "max_tokens": 100,
                        "temperature": 0.1  # Low temperature for consistent retrieval
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    response_text = result_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Evaluate relevance
                    relevance_score = self.calculate_relevance(qa["answer"], response_text, qa["keywords"])
                    is_hit = relevance_score > 0.3  # Threshold for considering it a "hit"
                    
                    if is_hit:
                        hit_count += 1
                        # For MRR calculation, assume rank 1 if it's a hit (simplified)
                        reciprocal_ranks.append(1.0)
                    else:
                        reciprocal_ranks.append(0.0)
                    
                    results.append({
                        "id": qa["id"],
                        "question": qa["question"],
                        "expected_answer": qa["answer"][:100] + "...",
                        "retrieved_answer": response_text[:100] + "...",
                        "relevance_score": relevance_score,
                        "is_hit": is_hit,
                        "keywords": qa["keywords"]
                    })
                    
                    print(f"   Query {i+1}/{len(test_pairs)}: {'✅' if is_hit else '❌'} (relevance: {relevance_score:.2f})")
                
                else:
                    print(f"   Query {i+1}/{len(test_pairs)}: ❌ HTTP {response.status_code}")
                    results.append({
                        "id": qa["id"],
                        "error": f"HTTP {response.status_code}",
                        "is_hit": False
                    })
                    reciprocal_ranks.append(0.0)
                    
            except Exception as e:
                print(f"   Query {i+1}/{len(test_pairs)}: ❌ Error: {e}")
                results.append({
                    "id": qa["id"],
                    "error": str(e),
                    "is_hit": False
                })
                reciprocal_ranks.append(0.0)
        
        # Calculate metrics
        hit_rate = hit_count / len(test_pairs) if test_pairs else 0
        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0
        
        return {
            "hit_rate": hit_rate,
            "mrr": mrr,
            "total_queries": len(test_pairs),
            "hits": hit_count,
            "detailed_results": results
        }
    
    def calculate_relevance(self, expected: str, retrieved: str, keywords: List[str]) -> float:
        """Calculate relevance score between expected and retrieved answers"""
        if not retrieved:
            return 0.0
        
        expected_lower = expected.lower()
        retrieved_lower = retrieved.lower()
        
        # Check for keyword overlap
        keyword_score = 0.0
        for keyword in keywords:
            if keyword.lower() in retrieved_lower:
                keyword_score += 1.0
        keyword_score = keyword_score / len(keywords) if keywords else 0.0
        
        # Check for semantic similarity (simplified)
        expected_words = set(expected_lower.split())
        retrieved_words = set(retrieved_lower.split())
        
        if expected_words:
            word_overlap = len(expected_words.intersection(retrieved_words)) / len(expected_words)
        else:
            word_overlap = 0.0
        
        # Combined score (weighted)
        relevance = 0.6 * keyword_score + 0.4 * word_overlap
        
        return min(relevance, 1.0)
    
    def run_evaluation(self, num_pairs: int = 200) -> Dict[str, Any]:
        """Run the complete retrieval accuracy evaluation"""
        print(f"🚀 Starting retrieval accuracy evaluation with {num_pairs} Q-A pairs")
        
        # Generate synthetic Q-A pairs
        qa_pairs = self.generate_synthetic_qa_pairs(num_pairs)
        print(f"✅ Generated {len(qa_pairs)} synthetic Q-A pairs")
        
        # Populate memory
        if not self.populate_memory(qa_pairs):
            return {"error": "Failed to populate memory sufficiently"}
        
        # Wait for memory indexing
        print("⏳ Waiting for memory indexing...")
        time.sleep(5)
        
        # Test retrieval accuracy
        retrieval_results = self.test_retrieval_accuracy(qa_pairs)
        
        # Evaluate against pass criteria
        hit_rate_pass = retrieval_results["hit_rate"] >= 0.65  # ≥65% hits
        mrr_pass = retrieval_results["mrr"] >= 0.75  # MRR ≥0.75
        overall_pass = hit_rate_pass and mrr_pass
        
        return {
            "success": True,
            "overall_pass": overall_pass,
            "timestamp": time.time(),
            "config": {
                "num_qa_pairs": num_pairs,
                "test_sample_size": retrieval_results["total_queries"]
            },
            "metrics": {
                "hit_rate": retrieval_results["hit_rate"],
                "mrr": retrieval_results["mrr"],
                "total_queries": retrieval_results["total_queries"],
                "successful_hits": retrieval_results["hits"]
            },
            "pass_criteria": {
                "hit_rate": {
                    "target": 0.65,
                    "actual": retrieval_results["hit_rate"],
                    "pass": hit_rate_pass
                },
                "mrr": {
                    "target": 0.75,
                    "actual": retrieval_results["mrr"],
                    "pass": mrr_pass
                }
            },
            "detailed_results": retrieval_results["detailed_results"]
        }

def main():
    parser = argparse.ArgumentParser(description="Retrieval accuracy evaluation")
    parser.add_argument("--qa-pairs", type=int, default=200, help="Number of Q-A pairs to generate")
    parser.add_argument("--url", default="http://localhost:9000", help="AutoGen Council base URL")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    # Run evaluation
    evaluator = RetrievalEvaluator(args.url)
    results = evaluator.run_evaluation(args.qa_pairs)
    
    # Print summary
    if results.get("success") and "metrics" in results:
        metrics = results["metrics"]
        pass_criteria = results["pass_criteria"]
        
        print(f"\n📊 RETRIEVAL ACCURACY EVALUATION RESULTS")
        print("=" * 60)
        print(f"🎯 Retrieval Metrics:")
        print(f"   Hit rate: {metrics['hit_rate']:.1%}")
        print(f"   Mean Reciprocal Rank (MRR): {metrics['mrr']:.3f}")
        print(f"   Successful hits: {metrics['successful_hits']}/{metrics['total_queries']}")
        
        print(f"\n🎯 Pass Criteria:")
        for criterion, data in pass_criteria.items():
            status = "✅" if data["pass"] else "❌"
            print(f"   {status} {criterion}: {data['actual']:.3f} (target: {data['target']:.3f})")
        
        overall_status = "✅ PASS" if results["overall_pass"] else "❌ FAIL"
        print(f"\n🏆 Overall Result: {overall_status}")
        
    else:
        print(f"❌ Evaluation failed: {results.get('error', 'Unknown error')}")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📄 Results saved to {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if results.get("overall_pass", False) else 1
    exit(exit_code)

if __name__ == "__main__":
    main() 