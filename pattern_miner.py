#!/usr/bin/env python3
"""
Pattern Miner - Autonomous Learning Loop
========================================

Ingest successful completions, cluster with MiniLM & HDBSCAN, 
derive route rules, and create synthetic specialists.

Goal: Cut another 20-30% of cloud usage by learning patterns.
"""

import os
import sys
import json
import time
import logging
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re
import hdbscan
import redis
from sentence_transformers import SentenceTransformer

# ML libraries for clustering
try:
    from sentence_transformers import SentenceTransformer
    import hdbscan
    from sklearn.feature_extraction.text import TfidfVectorizer
    ML_AVAILABLE = True
except ImportError as e:
    SentenceTransformer = None
    hdbscan = None
    TfidfVectorizer = None
    ML_AVAILABLE = False
    print(f"⚠️ ML libraries not available: {e}")
    print("Install with: pip install sentence-transformers hdbscan scikit-learn")

logger = logging.getLogger(__name__)

# Configuration
MIN_CLUSTER_SIZE = 2      # Minimum prompts to form a cluster (reduced for testing)
MIN_CONFIDENCE = 0.7      # Minimum confidence for pattern extraction
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Lightweight sentence transformer
PATTERN_CACHE_FILE = "patterns/learned_patterns.json"
COMPLETIONS_DIR = "data/completions"
SYNTHETIC_SPECIALISTS_FILE = "patterns/synthetic_specialists.py"

# Initialize embeddings model and Redis connection
EMB = SentenceTransformer("thenlper/gte-small")
R = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

@dataclass
class CompletionRecord:
    """Record of a successful completion"""
    prompt: str
    response: str
    confidence: float
    model_used: str
    timestamp: float
    cost_usd: float = 0.0
    session_id: str = ""

@dataclass
class PatternCluster:
    """A discovered pattern cluster"""
    cluster_id: int
    prompts: List[str]
    responses: List[str]
    keywords: List[str]
    route_rule: str
    template_response: str
    confidence: float
    usage_count: int = 0

class PatternMiner:
    """
    Pattern Mining and Synthetic Specialist Generator
    """
    
    def __init__(self):
        """Initialize the pattern miner"""
        self.embedder = None
        self.clusters: List[PatternCluster] = []
        self.vectorizer = None
        self.ml_available = ML_AVAILABLE  # Store as instance variable
        
        # Initialize ML models if available
        if self.ml_available:
            try:
                self.embedder = SentenceTransformer(EMBEDDING_MODEL)
                self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
                logger.info(f"🧠 Pattern miner initialized with {EMBEDDING_MODEL}")
            except Exception as e:
                logger.warning(f"🧠 ML model loading failed: {e}")
                self.ml_available = False
        
        # Ensure directories exist
        os.makedirs("patterns", exist_ok=True)
        os.makedirs("data/completions", exist_ok=True)
        
    def ingest_completions(self, sources: List[str]) -> List[CompletionRecord]:
        """
        Ingest successful completions from various sources.
        
        Args:
            sources: List of source paths (files, directories)
            
        Returns:
            List of completion records
        """
        completions = []
        
        for source in sources:
            if os.path.isfile(source):
                completions.extend(self._ingest_file(source))
            elif os.path.isdir(source):
                completions.extend(self._ingest_directory(source))
            else:
                logger.warning(f"🧠 Source not found: {source}")
                
        logger.info(f"🧠 Ingested {len(completions)} completion records")
        return completions
    
    def _ingest_file(self, filepath: str) -> List[CompletionRecord]:
        """Ingest completions from a single file"""
        completions = []
        
        try:
            if filepath.endswith('.json'):
                completions.extend(self._parse_json_completions(filepath))
            elif filepath.endswith('.md'):
                completions.extend(self._parse_markdown_completions(filepath))
            elif filepath.endswith('.txt'):
                completions.extend(self._parse_text_completions(filepath))
            else:
                logger.debug(f"🧠 Unknown file type: {filepath}")
                
        except Exception as e:
            logger.error(f"🧠 Error ingesting {filepath}: {e}")
            
        return completions
    
    def _ingest_directory(self, dirpath: str) -> List[CompletionRecord]:
        """Ingest completions from all files in directory"""
        completions = []
        
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                if file.endswith(('.json', '.md', '.txt')):
                    filepath = os.path.join(root, file)
                    completions.extend(self._ingest_file(filepath))
                    
        return completions
    
    def _parse_json_completions(self, filepath: str) -> List[CompletionRecord]:
        """Parse JSON completion records"""
        completions = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON formats
            if isinstance(data, list):
                for item in data:
                    completion = self._parse_completion_item(item)
                    if completion:
                        completions.append(completion)
            elif isinstance(data, dict):
                completion = self._parse_completion_item(data)
                if completion:
                    completions.append(completion)
                    
        except Exception as e:
            logger.error(f"🧠 JSON parse error {filepath}: {e}")
            
        return completions
    
    def _parse_markdown_completions(self, filepath: str) -> List[CompletionRecord]:
        """Parse markdown files with Q&A patterns"""
        completions = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple regex to find Q&A patterns
            qa_pattern = r'(?:Q:|Question:|User:)\s*(.+?)\n(?:A:|Answer:|Assistant:)\s*(.+?)(?=\n(?:Q:|Question:|User:)|\Z)'
            matches = re.findall(qa_pattern, content, re.DOTALL | re.IGNORECASE)
            
            for prompt, response in matches:
                completion = CompletionRecord(
                    prompt=prompt.strip(),
                    response=response.strip(),
                    confidence=0.8,  # Default for manual Q&A
                    model_used="manual",
                    timestamp=time.time()
                )
                completions.append(completion)
                
        except Exception as e:
            logger.error(f"🧠 Markdown parse error {filepath}: {e}")
            
        return completions
    
    def _parse_text_completions(self, filepath: str) -> List[CompletionRecord]:
        """Parse plain text files with simple patterns"""
        completions = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Simple pattern: alternating prompt/response lines
            for i in range(0, len(lines) - 1, 2):
                prompt = lines[i].strip()
                response = lines[i + 1].strip() if i + 1 < len(lines) else ""
                
                if prompt and response:
                    completion = CompletionRecord(
                        prompt=prompt,
                        response=response,
                        confidence=0.7,  # Default for text files
                        model_used="text",
                        timestamp=time.time()
                    )
                    completions.append(completion)
                    
        except Exception as e:
            logger.error(f"🧠 Text parse error {filepath}: {e}")
            
        return completions
    
    def _parse_completion_item(self, item: Dict) -> Optional[CompletionRecord]:
        """Parse a single completion item from JSON"""
        try:
            # Handle different JSON schemas
            prompt = item.get('prompt') or item.get('input') or item.get('question')
            response = item.get('response') or item.get('output') or item.get('answer')
            confidence = item.get('confidence', 0.8)
            model = item.get('model', 'unknown')
            timestamp = item.get('timestamp', time.time())
            
            if prompt and response:
                return CompletionRecord(
                    prompt=str(prompt).strip(),
                    response=str(response).strip(),
                    confidence=float(confidence),
                    model_used=str(model),
                    timestamp=float(timestamp)
                )
                
        except Exception as e:
            logger.debug(f"🧠 Item parse error: {e}")
            
        return None
    
    def cluster_prompts(self, completions: List[CompletionRecord]) -> List[PatternCluster]:
        """
        Cluster prompts using MiniLM embeddings and HDBSCAN.
        
        Args:
            completions: List of completion records
            
        Returns:
            List of pattern clusters
        """
        if not self.ml_available or not self.embedder:
            logger.warning("🧠 ML not available - using simple keyword clustering")
            return self._simple_keyword_clustering(completions)
            
        logger.info(f"🧠 Clustering {len(completions)} prompts with MiniLM + HDBSCAN...")
        
        # Extract prompts and generate embeddings
        prompts = [c.prompt for c in completions]
        try:
            embeddings = self.embedder.encode(prompts)
            logger.info(f"🧠 Generated {embeddings.shape} embeddings")
        except Exception as e:
            logger.error(f"🧠 Embedding generation failed: {e}")
            return self._simple_keyword_clustering(completions)
        
        # Cluster with HDBSCAN
        try:
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=MIN_CLUSTER_SIZE,
                metric='euclidean',  # Use euclidean instead of cosine
                cluster_selection_epsilon=0.1
            )
            cluster_labels = clusterer.fit_predict(embeddings)
            
            n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
            logger.info(f"🧠 Found {n_clusters} clusters, {list(cluster_labels).count(-1)} noise points")
            
        except Exception as e:
            logger.error(f"🧠 HDBSCAN clustering failed: {e}")
            return self._simple_keyword_clustering(completions)
        
        # Build pattern clusters
        clusters = []
        cluster_dict = {}
        
        for i, label in enumerate(cluster_labels):
            if label == -1:  # Noise point
                continue
                
            if label not in cluster_dict:
                cluster_dict[label] = {
                    'prompts': [],
                    'responses': [],
                    'completions': []
                }
                
            cluster_dict[label]['prompts'].append(completions[i].prompt)
            cluster_dict[label]['responses'].append(completions[i].response)
            cluster_dict[label]['completions'].append(completions[i])
        
        # Generate cluster metadata
        for cluster_id, data in cluster_dict.items():
            pattern_cluster = self._analyze_cluster(cluster_id, data)
            if pattern_cluster:
                clusters.append(pattern_cluster)
        
        logger.info(f"🧠 Generated {len(clusters)} pattern clusters")
        return clusters
    
    def _simple_keyword_clustering(self, completions: List[CompletionRecord]) -> List[PatternCluster]:
        """Fallback clustering using simple keyword matching"""
        logger.info("🧠 Using simple keyword clustering (fallback)")
        
        keyword_groups = {
            'math': ['calculate', 'compute', '+', '-', '*', '/', 'math', 'equation'],
            'code': ['function', 'code', 'python', 'javascript', 'programming', 'def '],
            'logic': ['proof', 'logic', 'reasoning', 'because', 'therefore'],
            'knowledge': ['explain', 'what is', 'how does', 'describe', 'define']
        }
        
        clusters = []
        cluster_dict = {}
        
        for completion in completions:
            prompt_lower = completion.prompt.lower()
            cluster_id = 'other'
            
            # Find best matching keyword group
            max_matches = 0
            for group_name, keywords in keyword_groups.items():
                matches = sum(1 for kw in keywords if kw in prompt_lower)
                if matches > max_matches:
                    max_matches = matches
                    cluster_id = group_name
            
            if cluster_id not in cluster_dict:
                cluster_dict[cluster_id] = {
                    'prompts': [],
                    'responses': [],
                    'completions': []
                }
                
            cluster_dict[cluster_id]['prompts'].append(completion.prompt)
            cluster_dict[cluster_id]['responses'].append(completion.response)
            cluster_dict[cluster_id]['completions'].append(completion)
        
        # Convert to pattern clusters
        for i, (cluster_name, data) in enumerate(cluster_dict.items()):
            logger.debug(f"🧠 Cluster '{cluster_name}': {len(data['prompts'])} prompts")
            if len(data['prompts']) >= MIN_CLUSTER_SIZE:
                pattern_cluster = self._analyze_cluster(i, data, cluster_name)
                if pattern_cluster:
                    clusters.append(pattern_cluster)
                    logger.debug(f"🧠 Created pattern cluster {i} for '{cluster_name}'")
        
        return clusters
    
    def _analyze_cluster(self, cluster_id: int, data: Dict, cluster_name: str = None) -> Optional[PatternCluster]:
        """Analyze a cluster to extract patterns and create synthetic specialist"""
        prompts = data['prompts']
        responses = data['responses']
        
        if len(prompts) < MIN_CLUSTER_SIZE:
            return None
            
        # Extract keywords (simple TF-IDF approach)
        try:
            if self.vectorizer:
                tfidf_matrix = self.vectorizer.fit_transform(prompts)
                feature_names = self.vectorizer.get_feature_names_out()
                scores = tfidf_matrix.sum(axis=0).A1
                top_indices = scores.argsort()[-10:][::-1]
                keywords = [feature_names[i] for i in top_indices]
            else:
                # Simple word frequency fallback
                word_freq = {}
                for prompt in prompts:
                    for word in prompt.lower().split():
                        word = re.sub(r'[^a-z]', '', word)
                        if len(word) > 3:
                            word_freq[word] = word_freq.get(word, 0) + 1
                keywords = sorted(word_freq.keys(), key=word_freq.get, reverse=True)[:10]
        except Exception as e:
            logger.debug(f"🧠 Keyword extraction failed: {e}")
            keywords = []
        
        # Generate route rule (regex pattern)
        route_rule = self._generate_route_rule(keywords, prompts)
        
        # Create template response (median good answer)
        template_response = self._create_template_response(responses)
        
        # Calculate cluster confidence
        confidence = min(0.9, 0.6 + len(prompts) * 0.05)  # More prompts = higher confidence
        
        return PatternCluster(
            cluster_id=cluster_id,
            prompts=prompts,
            responses=responses,
            keywords=keywords,
            route_rule=route_rule,
            template_response=template_response,
            confidence=confidence
        )
    
    def _generate_route_rule(self, keywords: List[str], prompts: List[str]) -> str:
        """Generate a regex route rule for this pattern"""
        if not keywords:
            return r".*"
            
        # Create a regex that matches any of the top keywords
        escaped_keywords = [re.escape(kw) for kw in keywords[:5]]
        rule = r'\b(' + '|'.join(escaped_keywords) + r')\b'
        
        return rule
    
    def _create_template_response(self, responses: List[str]) -> str:
        """Create a template response from the cluster responses"""
        if not responses:
            return "I can help with that."
            
        # Simple approach: find the median-length response
        responses_by_length = sorted(responses, key=len)
        median_idx = len(responses_by_length) // 2
        template = responses_by_length[median_idx]
        
        # Clean up the template
        template = template.strip()
        if len(template) > 200:
            template = template[:200] + "..."
            
        return template
    
    def generate_synthetic_specialists(self, clusters: List[PatternCluster]) -> str:
        """
        Generate Python code for synthetic specialists.
        
        Args:
            clusters: List of pattern clusters
            
        Returns:
            Python code string for synthetic specialists
        """
        code_lines = [
            "#!/usr/bin/env python3",
            '"""',
            'Synthetic Specialists - Auto-generated from Pattern Mining',
            'These specialists handle common patterns learned from user interactions.',
            'Generated at: ' + time.strftime('%Y-%m-%d %H:%M:%S'),
            '"""',
            '',
            'import re',
            'import time',
            'from typing import Optional, Dict, Any',
            '',
            'class PatternSpecialist:',
            '    """Base class for pattern-based specialists"""',
            '    ',
            '    def __init__(self, cluster_id: int, route_rule: str, template: str, confidence: float):',
            '        self.cluster_id = cluster_id',
            '        self.route_rule = re.compile(route_rule, re.IGNORECASE)',
            '        self.template = template',
            '        self.confidence = confidence',
            '        self.usage_count = 0',
            '    ',
            '    def match(self, prompt: str) -> bool:',
            '        """Check if this specialist can handle the prompt"""',
            '        return bool(self.route_rule.search(prompt))',
            '    ',
            '    def respond(self, prompt: str) -> Dict[str, Any]:',
            '        """Generate response for matching prompt"""',
            '        if not self.match(prompt):',
            '            return {"text": "UNSURE", "confidence": 0.0}',
            '        ',
            '        self.usage_count += 1',
            '        return {',
            '            "text": self.template,',
            '            "confidence": self.confidence,',
            '            "model": f"pattern_specialist_{self.cluster_id}",',
            '            "pattern_match": True,',
            '            "usage_count": self.usage_count',
            '        }',
            '',
            '# Generated pattern specialists',
        ]
        
        # Add specialist instances
        specialist_instances = []
        for cluster in clusters:
            if cluster.confidence >= MIN_CONFIDENCE:
                instance_name = f"pattern_{cluster.cluster_id}"
                specialist_instances.append(instance_name)
                
                code_lines.extend([
                    f'{instance_name} = PatternSpecialist(',
                    f'    cluster_id={cluster.cluster_id},',
                    f'    route_rule=r"{cluster.route_rule}",',
                    f'    template="""{cluster.template_response}""",',
                    f'    confidence={cluster.confidence:.2f}',
                    ')',
                    ''
                ])
        
        # Add pattern matching function
        code_lines.extend([
            'def pattern_specialist(prompt: str) -> Dict[str, Any]:',
            '    """',
            '    Main pattern specialist function for router integration.',
            '    Returns response if pattern matches, "UNSURE" otherwise.',
            '    """',
            '    specialists = [' + ', '.join(specialist_instances) + ']',
            '    ',
            '    for specialist in specialists:',
            '        if specialist.match(prompt):',
            '            return specialist.respond(prompt)',
            '    ',
            '    return {"text": "UNSURE", "confidence": 0.0}',
            '',
            '# Statistics',
            f'PATTERN_COUNT = {len(specialist_instances)}',
            f'GENERATED_AT = "{time.strftime("%Y-%m-%d %H:%M:%S")}"',
        ])
        
        return '\n'.join(code_lines)
    
    def save_patterns(self, clusters: List[PatternCluster]) -> None:
        """Save learned patterns to JSON file"""
        pattern_data = {
            'generated_at': time.time(),
            'pattern_count': len(clusters),
            'clusters': []
        }
        
        for cluster in clusters:
            cluster_data = {
                'cluster_id': cluster.cluster_id,
                'keywords': cluster.keywords,
                'route_rule': cluster.route_rule,
                'template_response': cluster.template_response,
                'confidence': cluster.confidence,
                'prompt_count': len(cluster.prompts),
                'usage_count': cluster.usage_count
            }
            pattern_data['clusters'].append(cluster_data)
        
        try:
            with open(PATTERN_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(pattern_data, f, indent=2, ensure_ascii=False)
            logger.info(f"🧠 Saved {len(clusters)} patterns to {PATTERN_CACHE_FILE}")
        except Exception as e:
            logger.error(f"🧠 Failed to save patterns: {e}")
    
    def run_pattern_mining(self, sources: List[str]) -> None:
        """
        Run the complete pattern mining pipeline.
        
        Args:
            sources: List of completion data sources
        """
        logger.info("🧠 Starting pattern mining pipeline...")
        
        # 1. Ingest completions
        completions = self.ingest_completions(sources)
        if not completions:
            logger.warning("🧠 No completions found to analyze")
            return
        
        # 2. Cluster prompts
        clusters = self.cluster_prompts(completions)
        if not clusters:
            logger.warning("🧠 No patterns found")
            return
        
        # 3. Generate synthetic specialists
        specialist_code = self.generate_synthetic_specialists(clusters)
        
        try:
            with open(SYNTHETIC_SPECIALISTS_FILE, 'w', encoding='utf-8') as f:
                f.write(specialist_code)
            logger.info(f"🧠 Generated synthetic specialists: {SYNTHETIC_SPECIALISTS_FILE}")
        except Exception as e:
            logger.error(f"🧠 Failed to save specialists: {e}")
        
        # 4. Save patterns
        self.save_patterns(clusters)
        
        # 5. Summary
        total_prompts = sum(len(c.prompts) for c in clusters)
        logger.info(f"🧠 Pattern mining complete:")
        logger.info(f"   📥 Ingested: {len(completions)} completions")
        logger.info(f"   🔍 Found: {len(clusters)} patterns")
        logger.info(f"   📊 Covered: {total_prompts} prompts")
        logger.info(f"   🚀 Expected savings: 20-30% of cloud calls")

def mine_batch(batch):
    """Process a batch of logs through HDBSCAN clustering"""
    docs = [b["text"] for b in batch]
    vecs = EMB.encode(docs, convert_to_numpy=True)
    cids = hdbscan.HDBSCAN(min_cluster_size=15, metric="cosine").fit_predict(vecs)
    
    for rec, cid in zip(batch, cids):
        sha = hashlib.sha1(rec["text"].encode()).hexdigest()[:12]
        key = f"pattern:{sha}"
        R.hset(key, mapping={"cid": int(cid), "ts": int(time.time())})
        R.incr("pattern_clusters_total")

def run():
    """Main pattern mining loop"""
    while True:
        # fetch up to 200 unclustered logs
        raw = R.lrange("logs:recent", 0, 199)
        if not raw:
            time.sleep(30)
            continue
        
        batch = [json.loads(r) for r in raw]
        mine_batch(batch)
        R.ltrim("logs:recent", len(raw), -1)

def main():
    """CLI entry point for pattern mining"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pattern Miner - Learn from completions")
    parser.add_argument("sources", nargs="+", help="Completion data sources (files/directories)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run pattern mining
    miner = PatternMiner()
    miner.run_pattern_mining(args.sources)

if __name__ == "__main__":
    # Check if we should run as daemon or CLI
    if len(sys.argv) == 1:
        # No arguments - run as daemon
        run()
    else:
        # Arguments provided - run CLI
        main() 