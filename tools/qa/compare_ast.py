#!/usr/bin/env python3
"""
QA-300: Dual-Render Diff Engine
🎯 AST-level semantic comparison between Sonnet-A and Sonnet-B builders

Computes semantic distance using AST parsing, token diffing, and Levenshtein distance.
Outputs structured meta.yaml for PatchCtl integration and Gemini audit routing.
"""

import ast
import argparse
import difflib
import json
import logging
import os
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
try:
    import Levenshtein
except ImportError:
    # Fallback for environments without Levenshtein
    class Levenshtein:
        @staticmethod
        def distance(a, b):
            # Simple edit distance fallback
            if len(a) == 0: return len(b)
            if len(b) == 0: return len(a)
            
            matrix = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
            
            for i in range(len(a) + 1):
                matrix[i][0] = i
            for j in range(len(b) + 1):
                matrix[0][j] = j
            
            for i in range(1, len(a) + 1):
                for j in range(1, len(b) + 1):
                    if a[i-1] == b[j-1]:
                        cost = 0
                    else:
                        cost = 1
                    
                    matrix[i][j] = min(
                        matrix[i-1][j] + 1,      # deletion
                        matrix[i][j-1] + 1,      # insertion
                        matrix[i-1][j-1] + cost  # substitution
                    )
            
            return matrix[len(a)][len(b)]
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ASTComparison:
    """AST comparison result with semantic analysis"""
    file_a: str
    file_b: str
    ast_similarity: float
    token_similarity: float
    structure_similarity: float
    semantic_distance: float
    quorum_decision: str  # "pass" or "fail"
    route_to: str  # "none" or "gemini-audit"
    diff_details: Dict[str, Any]
    execution_time_ms: float
    timestamp: str

@dataclass
class ASTMetrics:
    """AST structure metrics for comparison"""
    node_count: int
    depth: int
    function_count: int
    class_count: int
    import_count: int
    complexity_score: float
    node_types: Dict[str, int]

class ASTAnalyzer:
    """AST analysis and comparison engine"""
    
    def __init__(self, threshold: float = 0.03):
        self.threshold = threshold
        self.pass_threshold = 1.0 - threshold  # 97% similarity for pass
        
    def parse_file(self, filepath: str) -> Optional[ast.AST]:
        """Parse Python file into AST"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            return tree
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse {filepath}: {e}")
            return None

    def extract_ast_metrics(self, tree: ast.AST) -> ASTMetrics:
        """Extract structural metrics from AST"""
        metrics = {
            'node_count': 0,
            'depth': 0,
            'function_count': 0,
            'class_count': 0,
            'import_count': 0,
            'node_types': {}
        }
        
        def visit_node(node, depth=0):
            metrics['node_count'] += 1
            metrics['depth'] = max(metrics['depth'], depth)
            
            node_type = type(node).__name__
            metrics['node_types'][node_type] = metrics['node_types'].get(node_type, 0) + 1
            
            if isinstance(node, ast.FunctionDef):
                metrics['function_count'] += 1
            elif isinstance(node, ast.ClassDef):
                metrics['class_count'] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics['import_count'] += 1
            
            for child in ast.iter_child_nodes(node):
                visit_node(child, depth + 1)
        
        visit_node(tree)
        
        # Calculate complexity score (simplified cyclomatic complexity)
        complexity = (
            metrics['function_count'] * 2 +
            metrics['class_count'] * 3 +
            metrics['node_types'].get('If', 0) +
            metrics['node_types'].get('For', 0) +
            metrics['node_types'].get('While', 0) +
            metrics['node_types'].get('Try', 0)
        )
        
        return ASTMetrics(
            node_count=metrics['node_count'],
            depth=metrics['depth'],
            function_count=metrics['function_count'],
            class_count=metrics['class_count'],
            import_count=metrics['import_count'],
            complexity_score=complexity,
            node_types=metrics['node_types']
        )

    def ast_to_tokens(self, tree: ast.AST) -> List[str]:
        """Convert AST to normalized token sequence"""
        tokens = []
        
        def visit_node(node):
            # Add node type as token
            tokens.append(type(node).__name__)
            
            # Add relevant attributes (normalized for variable names)
            if hasattr(node, 'name'):
                # Normalize function/class names to reduce variable name sensitivity
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    tokens.append(f"NAME:{node.name}")
                else:
                    tokens.append("NAME:var")  # Generic variable placeholder
            if hasattr(node, 'id'):
                # Normalize identifiers to reduce variable name sensitivity
                tokens.append("ID:identifier")
            if hasattr(node, 'attr'):
                tokens.append(f"ATTR:{node.attr}")
            
            # Visit children in consistent order
            for child in ast.iter_child_nodes(node):
                visit_node(child)
        
        visit_node(tree)
        return tokens

    def calculate_token_similarity(self, tokens_a: List[str], tokens_b: List[str]) -> float:
        """Calculate token-level similarity using sequence matching"""
        if not tokens_a and not tokens_b:
            return 1.0
        if not tokens_a or not tokens_b:
            return 0.0
        
        # Use difflib for sequence similarity
        matcher = difflib.SequenceMatcher(None, tokens_a, tokens_b)
        return matcher.ratio()

    def calculate_levenshtein_similarity(self, tokens_a: List[str], tokens_b: List[str]) -> float:
        """Calculate Levenshtein distance similarity"""
        if not tokens_a and not tokens_b:
            return 1.0
        if not tokens_a or not tokens_b:
            return 0.0
        
        # Convert token lists to strings for Levenshtein
        str_a = " ".join(tokens_a)
        str_b = " ".join(tokens_b)
        
        # Calculate normalized Levenshtein distance
        max_len = max(len(str_a), len(str_b))
        if max_len == 0:
            return 1.0
        
        distance = Levenshtein.distance(str_a, str_b)
        similarity = 1.0 - (distance / max_len)
        return max(0.0, similarity)

    def calculate_structure_similarity(self, metrics_a: ASTMetrics, metrics_b: ASTMetrics) -> float:
        """Calculate structural similarity between AST metrics"""
        # Compare key structural metrics
        structure_scores = []
        
        # Node count similarity
        if max(metrics_a.node_count, metrics_b.node_count) > 0:
            node_sim = 1.0 - abs(metrics_a.node_count - metrics_b.node_count) / max(metrics_a.node_count, metrics_b.node_count)
            structure_scores.append(node_sim)
        
        # Depth similarity
        if max(metrics_a.depth, metrics_b.depth) > 0:
            depth_sim = 1.0 - abs(metrics_a.depth - metrics_b.depth) / max(metrics_a.depth, metrics_b.depth)
            structure_scores.append(depth_sim)
        
        # Function count similarity
        if max(metrics_a.function_count, metrics_b.function_count) > 0:
            func_sim = 1.0 - abs(metrics_a.function_count - metrics_b.function_count) / max(metrics_a.function_count, metrics_b.function_count)
            structure_scores.append(func_sim)
        
        # Class count similarity
        if max(metrics_a.class_count, metrics_b.class_count) > 0:
            class_sim = 1.0 - abs(metrics_a.class_count - metrics_b.class_count) / max(metrics_a.class_count, metrics_b.class_count)
            structure_scores.append(class_sim)
        
        # Complexity similarity
        if max(metrics_a.complexity_score, metrics_b.complexity_score) > 0:
            complexity_sim = 1.0 - abs(metrics_a.complexity_score - metrics_b.complexity_score) / max(metrics_a.complexity_score, metrics_b.complexity_score)
            structure_scores.append(complexity_sim)
        
        # Node type distribution similarity
        all_node_types = set(metrics_a.node_types.keys()) | set(metrics_b.node_types.keys())
        if all_node_types:
            node_type_sim = 0.0
            for node_type in all_node_types:
                count_a = metrics_a.node_types.get(node_type, 0)
                count_b = metrics_b.node_types.get(node_type, 0)
                max_count = max(count_a, count_b)
                if max_count > 0:
                    type_sim = 1.0 - abs(count_a - count_b) / max_count
                    node_type_sim += type_sim
            node_type_sim /= len(all_node_types)
            structure_scores.append(node_type_sim)
        
        # Return average of all structure scores
        return sum(structure_scores) / len(structure_scores) if structure_scores else 0.0

    def compare_files(self, file_a: str, file_b: str) -> ASTComparison:
        """Compare two Python files using AST analysis"""
        start_time = time.time()
        
        logger.info(f"Comparing {file_a} vs {file_b}")
        
        # Parse both files
        tree_a = self.parse_file(file_a)
        tree_b = self.parse_file(file_b)
        
        if tree_a is None or tree_b is None:
            return ASTComparison(
                file_a=file_a,
                file_b=file_b,
                ast_similarity=0.0,
                token_similarity=0.0,
                structure_similarity=0.0,
                semantic_distance=1.0,
                quorum_decision="fail",
                route_to="gemini-audit",
                diff_details={"error": "Failed to parse one or both files"},
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat()
            )
        
        # Extract metrics
        metrics_a = self.extract_ast_metrics(tree_a)
        metrics_b = self.extract_ast_metrics(tree_b)
        
        # Convert to tokens
        tokens_a = self.ast_to_tokens(tree_a)
        tokens_b = self.ast_to_tokens(tree_b)
        
        # Calculate similarities
        token_similarity = self.calculate_token_similarity(tokens_a, tokens_b)
        levenshtein_similarity = self.calculate_levenshtein_similarity(tokens_a, tokens_b)
        structure_similarity = self.calculate_structure_similarity(metrics_a, metrics_b)
        
        # Combined AST similarity (weighted average)
        # Prioritize structure over exact token matching for better tolerance
        ast_similarity = (
            token_similarity * 0.3 +
            levenshtein_similarity * 0.2 +
            structure_similarity * 0.5
        )
        
        # Semantic distance (inverse of similarity)
        semantic_distance = 1.0 - ast_similarity
        
        # Quorum decision
        quorum_decision = "pass" if ast_similarity >= self.pass_threshold else "fail"
        route_to = "none" if quorum_decision == "pass" else "gemini-audit"
        
        # Detailed diff analysis
        diff_details = {
            "metrics_a": asdict(metrics_a),
            "metrics_b": asdict(metrics_b),
            "token_count_a": len(tokens_a),
            "token_count_b": len(tokens_b),
            "common_tokens": len(set(tokens_a) & set(tokens_b)),
            "unique_tokens_a": len(set(tokens_a) - set(tokens_b)),
            "unique_tokens_b": len(set(tokens_b) - set(tokens_a)),
            "threshold_used": self.threshold,
            "pass_threshold": self.pass_threshold
        }
        
        execution_time = (time.time() - start_time) * 1000
        
        result = ASTComparison(
            file_a=file_a,
            file_b=file_b,
            ast_similarity=ast_similarity,
            token_similarity=token_similarity,
            structure_similarity=structure_similarity,
            semantic_distance=semantic_distance,
            quorum_decision=quorum_decision,
            route_to=route_to,
            diff_details=diff_details,
            execution_time_ms=execution_time,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"AST comparison completed: {ast_similarity:.1%} similarity, {quorum_decision}")
        
        return result

    def generate_meta_yaml(self, comparison: ASTComparison, output_path: str = "meta.yaml") -> str:
        """Generate meta.yaml output for PatchCtl integration"""
        meta_data = {
            'qa_300_dual_render': {
                'ast_similarity': f"{comparison.ast_similarity:.1%}",
                'quorum_decision': comparison.quorum_decision,
                'route_to': comparison.route_to,
                'semantic_distance': round(comparison.semantic_distance, 4),
                'threshold': self.threshold,
                'files_compared': {
                    'sonnet_a': comparison.file_a,
                    'sonnet_b': comparison.file_b
                },
                'metrics': {
                    'token_similarity': round(comparison.token_similarity, 4),
                    'structure_similarity': round(comparison.structure_similarity, 4),
                    'execution_time_ms': round(comparison.execution_time_ms, 2)
                },
                'timestamp': comparison.timestamp,
                'rollback': 'qa-revert'
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(meta_data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Meta YAML written to {output_path}")
        return output_path

    def generate_prometheus_metric(self, comparison: ASTComparison) -> str:
        """Generate Prometheus metric for monitoring"""
        diff_percent = comparison.semantic_distance * 100
        builder_pair = "sonnet-a:sonnet-b"
        
        metric = f'quorum_ast_diff_percent{{builder_pair="{builder_pair}"}} = {diff_percent:.2f}'
        return metric

def main():
    """CLI interface for AST comparison"""
    parser = argparse.ArgumentParser(description="QA-300 Dual-Render Diff Engine")
    parser.add_argument('--file-a', required=True, help='First Python file (Sonnet-A output)')
    parser.add_argument('--file-b', required=True, help='Second Python file (Sonnet-B output)')
    parser.add_argument('--threshold', type=float, default=0.03, help='Diff threshold (default: 0.03)')
    parser.add_argument('--output', default='meta.yaml', help='Output meta.yaml path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--metric-file', help='Write Prometheus metric to file')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input files
    if not os.path.exists(args.file_a):
        logger.error(f"File not found: {args.file_a}")
        sys.exit(1)
    
    if not os.path.exists(args.file_b):
        logger.error(f"File not found: {args.file_b}")
        sys.exit(1)
    
    # Create analyzer
    analyzer = ASTAnalyzer(threshold=args.threshold)
    
    # Perform comparison
    try:
        comparison = analyzer.compare_files(args.file_a, args.file_b)
        
        # Generate outputs
        meta_path = analyzer.generate_meta_yaml(comparison, args.output)
        metric = analyzer.generate_prometheus_metric(comparison)
        
        # Write metric file if requested
        if args.metric_file:
            with open(args.metric_file, 'w') as f:
                f.write(metric + '\n')
            logger.info(f"Metric written to {args.metric_file}")
        
        # Output results
        if args.json:
            print(json.dumps(asdict(comparison), indent=2))
        else:
            print(f"🎯 QA-300 Dual-Render Diff Engine Results")
            print(f"=" * 50)
            print(f"Files: {args.file_a} vs {args.file_b}")
            print(f"AST Similarity: {comparison.ast_similarity:.1%}")
            print(f"Semantic Distance: {comparison.semantic_distance:.1%}")
            print(f"Quorum Decision: {comparison.quorum_decision.upper()}")
            print(f"Route To: {comparison.route_to}")
            print(f"Execution Time: {comparison.execution_time_ms:.1f}ms")
            print(f"Meta YAML: {meta_path}")
            print(f"Prometheus Metric: {metric}")
        
        # Exit with appropriate code
        sys.exit(0 if comparison.quorum_decision == "pass" else 1)
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main() 