#!/usr/bin/env python3
"""
FMC-120: Loop Agent Service
Feedback ↔ prompt refinement loop management
Ensures feedback_seen_total ≥ 3 per PR for continuous improvement
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import redis
import requests

# Prometheus metrics
feedback_seen_total = Counter('feedback_seen_total', 'Total feedback events processed', ['pr_id', 'feedback_type'])
loop_iterations_total = Counter('loop_iterations_total', 'Total loop iterations', ['pr_id', 'stage'])
feedback_quality_score = Gauge('feedback_quality_score', 'Quality score of feedback', ['pr_id'])
loop_convergence_time = Histogram('loop_convergence_time_seconds', 'Time for loop to converge')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FeedbackEvent:
    """Individual feedback event"""
    id: str
    pr_id: str
    feedback_type: str  # code_review, test_results, user_feedback, ai_analysis
    content: str
    confidence: float
    timestamp: datetime
    source: str  # github, ci, user, ai_agent
    actionable: bool

@dataclass
class LoopIteration:
    """Single iteration in the feedback loop"""
    iteration_id: str
    pr_id: str
    stage: str  # analysis, refinement, validation, integration
    inputs: List[FeedbackEvent]
    outputs: Dict
    duration_seconds: float
    improvement_score: float
    timestamp: datetime

@dataclass
class LoopState:
    """Current state of feedback loop for a PR"""
    pr_id: str
    current_stage: str
    iterations: List[LoopIteration]
    total_feedback_events: int
    converged: bool
    quality_threshold_met: bool
    started_at: datetime
    last_activity: datetime

class LoopAgent:
    """Manages feedback loops for continuous prompt/PR refinement"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.active_loops: Dict[str, LoopState] = {}
        
        # Loop configuration
        self.min_feedback_events = 3
        self.quality_threshold = 0.8
        self.max_iterations_per_stage = 5
        self.convergence_timeout = timedelta(hours=2)
        
        # Feedback processors by type
        self.feedback_processors = {
            'code_review': self._process_code_review,
            'test_results': self._process_test_results,
            'user_feedback': self._process_user_feedback,
            'ai_analysis': self._process_ai_analysis
        }
        
        # Loop stages and their objectives
        self.loop_stages = {
            'analysis': 'Analyze incoming feedback and identify improvement areas',
            'refinement': 'Generate refined prompts/code based on feedback',
            'validation': 'Validate improvements against success criteria',
            'integration': 'Integrate improvements into PR'
        }
        
    def start_feedback_loop(self, pr_id: str) -> LoopState:
        """Initialize feedback loop for a PR"""
        loop_state = LoopState(
            pr_id=pr_id,
            current_stage='analysis',
            iterations=[],
            total_feedback_events=0,
            converged=False,
            quality_threshold_met=False,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        self.active_loops[pr_id] = loop_state
        
        # Store in Redis for persistence
        self._persist_loop_state(loop_state)
        
        logger.info(f"Started feedback loop for PR {pr_id}")
        return loop_state
    
    def process_feedback(self, pr_id: str, feedback_event: FeedbackEvent) -> Dict:
        """Process incoming feedback and advance the loop"""
        try:
            # Get or create loop state
            if pr_id not in self.active_loops:
                self.start_feedback_loop(pr_id)
            
            loop_state = self.active_loops[pr_id]
            
            # Update metrics
            feedback_seen_total.labels(pr_id=pr_id, feedback_type=feedback_event.feedback_type).inc()
            
            # Process the feedback based on type
            processor = self.feedback_processors.get(
                feedback_event.feedback_type, 
                self._process_generic_feedback
            )
            
            processing_result = processor(feedback_event, loop_state)
            
            # Update loop state
            loop_state.total_feedback_events += 1
            loop_state.last_activity = datetime.utcnow()
            
            # Check if we should advance to next iteration
            should_iterate = self._should_iterate(loop_state, feedback_event)
            
            if should_iterate:
                iteration_result = self._execute_loop_iteration(loop_state, feedback_event)
                loop_state.iterations.append(iteration_result)
                
                # Update metrics
                loop_iterations_total.labels(pr_id=pr_id, stage=loop_state.current_stage).inc()
            
            # Check convergence
            if self._check_convergence(loop_state):
                self._finalize_loop(loop_state)
            
            # Persist updated state
            self._persist_loop_state(loop_state)
            
            return {
                "feedback_processed": True,
                "feedback_id": feedback_event.id,
                "pr_id": pr_id,
                "current_stage": loop_state.current_stage,
                "total_feedback": loop_state.total_feedback_events,
                "iterations": len(loop_state.iterations),
                "converged": loop_state.converged,
                "processing_result": processing_result
            }
            
        except Exception as e:
            logger.error(f"Error processing feedback for PR {pr_id}: {e}")
            raise
    
    def _process_code_review(self, feedback: FeedbackEvent, loop_state: LoopState) -> Dict:
        """Process code review feedback"""
        # Extract actionable items from code review
        actionable_items = []
        
        # Simple pattern matching for common review feedback
        patterns = {
            'style': r'\b(style|format|lint|pep8|prettier)\b',
            'logic': r'\b(logic|algorithm|approach|method)\b',
            'performance': r'\b(performance|optimize|slow|fast|efficient)\b',
            'security': r'\b(security|vulnerable|safe|auth|permission)\b',
            'testing': r'\b(test|coverage|mock|assert|spec)\b'
        }
        
        import re
        for category, pattern in patterns.items():
            if re.search(pattern, feedback.content, re.IGNORECASE):
                actionable_items.append({
                    'category': category,
                    'priority': 'high' if category in ['security', 'logic'] else 'medium'
                })
        
        return {
            'actionable_items': actionable_items,
            'improvement_areas': len(actionable_items),
            'requires_code_changes': len(actionable_items) > 0
        }
    
    def _process_test_results(self, feedback: FeedbackEvent, loop_state: LoopState) -> Dict:
        """Process CI/test feedback"""
        # Parse test results
        test_data = {
            'passed': 0,
            'failed': 0,
            'coverage': 0.0,
            'performance_regression': False
        }
        
        try:
            # Try to parse JSON test results
            if feedback.content.startswith('{'):
                parsed = json.loads(feedback.content)
                test_data.update(parsed)
        except json.JSONDecodeError:
            # Simple text parsing
            import re
            
            # Extract test counts
            passed_match = re.search(r'(\d+)\s*passed', feedback.content, re.IGNORECASE)
            if passed_match:
                test_data['passed'] = int(passed_match.group(1))
            
            failed_match = re.search(r'(\d+)\s*failed', feedback.content, re.IGNORECASE)
            if failed_match:
                test_data['failed'] = int(failed_match.group(1))
            
            # Extract coverage
            coverage_match = re.search(r'coverage[:\s]*(\d+)%', feedback.content, re.IGNORECASE)
            if coverage_match:
                test_data['coverage'] = float(coverage_match.group(1)) / 100
        
        return {
            'test_results': test_data,
            'needs_fixes': test_data['failed'] > 0,
            'coverage_acceptable': test_data['coverage'] >= 0.8
        }
    
    def _process_user_feedback(self, feedback: FeedbackEvent, loop_state: LoopState) -> Dict:
        """Process human user feedback"""
        # Sentiment and intent analysis
        sentiment = self._analyze_sentiment(feedback.content)
        intent = self._extract_user_intent(feedback.content)
        
        return {
            'sentiment': sentiment,
            'intent': intent,
            'user_satisfaction': sentiment['score'],
            'action_required': sentiment['score'] < 0.6
        }
    
    def _process_ai_analysis(self, feedback: FeedbackEvent, loop_state: LoopState) -> Dict:
        """Process AI-generated analysis feedback"""
        # AI feedback is typically more structured
        return {
            'ai_confidence': feedback.confidence,
            'recommendations': self._extract_ai_recommendations(feedback.content),
            'quality_assessment': feedback.confidence
        }
    
    def _process_generic_feedback(self, feedback: FeedbackEvent, loop_state: LoopState) -> Dict:
        """Generic feedback processor"""
        return {
            'type': 'generic',
            'processed': True,
            'confidence': feedback.confidence
        }
    
    def _should_iterate(self, loop_state: LoopState, feedback: FeedbackEvent) -> bool:
        """Determine if we should execute a loop iteration"""
        # Iterate if:
        # 1. We have new actionable feedback
        # 2. Current stage has room for more iterations
        # 3. Loop hasn't converged
        
        if loop_state.converged:
            return False
        
        current_stage_iterations = len([
            i for i in loop_state.iterations 
            if i.stage == loop_state.current_stage
        ])
        
        if current_stage_iterations >= self.max_iterations_per_stage:
            # Advance to next stage
            self._advance_stage(loop_state)
            return True
        
        # Check if feedback is actionable enough
        return feedback.actionable or feedback.confidence > 0.7
    
    def _execute_loop_iteration(self, loop_state: LoopState, trigger_feedback: FeedbackEvent) -> LoopIteration:
        """Execute a single loop iteration"""
        start_time = time.time()
        iteration_id = f"{loop_state.pr_id}-{loop_state.current_stage}-{len(loop_state.iterations)}"
        
        # Gather all relevant feedback for this iteration
        relevant_feedback = [trigger_feedback]
        
        # Execute stage-specific logic
        stage_output = self._execute_stage_logic(loop_state.current_stage, relevant_feedback, loop_state)
        
        # Calculate improvement score
        improvement_score = self._calculate_improvement_score(stage_output, loop_state)
        
        duration = time.time() - start_time
        
        iteration = LoopIteration(
            iteration_id=iteration_id,
            pr_id=loop_state.pr_id,
            stage=loop_state.current_stage,
            inputs=relevant_feedback,
            outputs=stage_output,
            duration_seconds=duration,
            improvement_score=improvement_score,
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Completed iteration {iteration_id} (improvement: {improvement_score:.3f})")
        
        return iteration
    
    def _execute_stage_logic(self, stage: str, feedback_list: List[FeedbackEvent], 
                           loop_state: LoopState) -> Dict:
        """Execute logic specific to the current stage"""
        
        if stage == 'analysis':
            return self._analyze_feedback(feedback_list, loop_state)
        elif stage == 'refinement':
            return self._generate_refinements(feedback_list, loop_state)
        elif stage == 'validation':
            return self._validate_changes(feedback_list, loop_state)
        elif stage == 'integration':
            return self._integrate_changes(feedback_list, loop_state)
        else:
            return {'stage': stage, 'completed': True}
    
    def _analyze_feedback(self, feedback_list: List[FeedbackEvent], loop_state: LoopState) -> Dict:
        """Analyze feedback to identify improvement opportunities"""
        analysis = {
            'feedback_count': len(feedback_list),
            'feedback_types': list(set(f.feedback_type for f in feedback_list)),
            'avg_confidence': sum(f.confidence for f in feedback_list) / len(feedback_list),
            'improvement_areas': [],
            'priority_actions': []
        }
        
        # Categorize feedback by improvement areas
        for feedback in feedback_list:
            if feedback.feedback_type == 'code_review':
                analysis['improvement_areas'].append('code_quality')
            elif feedback.feedback_type == 'test_results':
                analysis['improvement_areas'].append('testing')
            elif feedback.feedback_type == 'user_feedback':
                analysis['improvement_areas'].append('user_experience')
        
        return analysis
    
    def _generate_refinements(self, feedback_list: List[FeedbackEvent], loop_state: LoopState) -> Dict:
        """Generate refined prompts/code based on feedback"""
        refinements = {
            'refined_prompts': [],
            'code_suggestions': [],
            'test_improvements': [],
            'documentation_updates': []
        }
        
        # Generate refinements based on feedback analysis
        for feedback in feedback_list:
            if 'code' in feedback.content.lower():
                refinements['code_suggestions'].append({
                    'suggestion': f"Improve code based on: {feedback.content[:100]}...",
                    'priority': 'high' if feedback.confidence > 0.8 else 'medium'
                })
            
            if 'test' in feedback.content.lower():
                refinements['test_improvements'].append({
                    'suggestion': f"Enhance tests based on: {feedback.content[:100]}...",
                    'priority': 'high' if feedback.confidence > 0.8 else 'medium'
                })
        
        return refinements
    
    def _validate_changes(self, feedback_list: List[FeedbackEvent], loop_state: LoopState) -> Dict:
        """Validate proposed changes against success criteria"""
        validation = {
            'criteria_met': 0,
            'total_criteria': 0,
            'validation_score': 0.0,
            'blocking_issues': [],
            'warnings': []
        }
        
        # Mock validation - in real implementation, this would
        # run actual validation tests
        total_criteria = 5  # Example: code quality, tests, performance, security, docs
        criteria_met = min(len(feedback_list), total_criteria)
        
        validation.update({
            'criteria_met': criteria_met,
            'total_criteria': total_criteria,
            'validation_score': criteria_met / total_criteria
        })
        
        return validation
    
    def _integrate_changes(self, feedback_list: List[FeedbackEvent], loop_state: LoopState) -> Dict:
        """Integrate approved changes into the PR"""
        integration = {
            'changes_applied': 0,
            'integration_success': True,
            'pr_updated': False,
            'next_actions': []
        }
        
        # In real implementation, this would:
        # 1. Apply code changes
        # 2. Update PR
        # 3. Trigger new CI run
        # 4. Notify stakeholders
        
        integration['changes_applied'] = len(feedback_list)
        integration['pr_updated'] = True
        
        return integration
    
    def _calculate_improvement_score(self, stage_output: Dict, loop_state: LoopState) -> float:
        """Calculate how much this iteration improved the PR"""
        # Simple scoring based on stage and outputs
        base_score = 0.5
        
        if 'validation_score' in stage_output:
            base_score = stage_output['validation_score']
        elif 'integration_success' in stage_output:
            base_score = 0.9 if stage_output['integration_success'] else 0.3
        elif 'improvement_areas' in stage_output:
            base_score = min(0.9, 0.5 + len(stage_output['improvement_areas']) * 0.1)
        
        return base_score
    
    def _check_convergence(self, loop_state: LoopState) -> bool:
        """Check if the feedback loop has converged"""
        # Convergence criteria:
        # 1. Minimum feedback events reached
        # 2. Quality threshold met
        # 3. Recent iterations show diminishing returns
        # 4. All stages completed at least once
        
        if loop_state.total_feedback_events < self.min_feedback_events:
            return False
        
        if len(loop_state.iterations) == 0:
            return False
        
        # Check quality threshold
        recent_iterations = loop_state.iterations[-3:]
        avg_improvement = sum(i.improvement_score for i in recent_iterations) / len(recent_iterations)
        
        quality_threshold_met = avg_improvement >= self.quality_threshold
        
        # Check if all stages have been attempted
        attempted_stages = set(i.stage for i in loop_state.iterations)
        all_stages_attempted = len(attempted_stages) >= 3  # At least 3 different stages
        
        # Check for diminishing returns
        if len(recent_iterations) >= 2:
            improvement_trend = recent_iterations[-1].improvement_score - recent_iterations[-2].improvement_score
            diminishing_returns = improvement_trend < 0.05
        else:
            diminishing_returns = False
        
        converged = (quality_threshold_met and all_stages_attempted) or diminishing_returns
        
        if converged:
            loop_state.converged = True
            loop_state.quality_threshold_met = quality_threshold_met
            
            # Update quality metric
            feedback_quality_score.labels(pr_id=loop_state.pr_id).set(avg_improvement)
        
        return converged
    
    def _finalize_loop(self, loop_state: LoopState):
        """Finalize the feedback loop"""
        total_duration = (datetime.utcnow() - loop_state.started_at).total_seconds()
        loop_convergence_time.observe(total_duration)
        
        logger.info(f"Feedback loop converged for PR {loop_state.pr_id} "
                   f"after {loop_state.total_feedback_events} feedback events "
                   f"and {len(loop_state.iterations)} iterations")
        
        # Store final state
        self._persist_loop_state(loop_state)
        
        # Notify completion
        self._notify_loop_completion(loop_state)
    
    def _advance_stage(self, loop_state: LoopState):
        """Advance to the next stage in the loop"""
        stages = list(self.loop_stages.keys())
        current_index = stages.index(loop_state.current_stage)
        
        if current_index < len(stages) - 1:
            loop_state.current_stage = stages[current_index + 1]
        else:
            # Cycle back to analysis for continuous improvement
            loop_state.current_stage = 'analysis'
        
        logger.info(f"Advanced PR {loop_state.pr_id} to stage: {loop_state.current_stage}")
    
    def _persist_loop_state(self, loop_state: LoopState):
        """Persist loop state to Redis"""
        try:
            state_json = json.dumps(asdict(loop_state), default=str)
            self.redis_client.setex(f"loop_state:{loop_state.pr_id}", 86400, state_json)
        except Exception as e:
            logger.error(f"Failed to persist loop state: {e}")
    
    def _notify_loop_completion(self, loop_state: LoopState):
        """Notify stakeholders of loop completion"""
        # In real implementation, this would send notifications
        # to GitHub, Slack, etc.
        logger.info(f"Loop completion notification sent for PR {loop_state.pr_id}")
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """Simple sentiment analysis"""
        positive_words = ['good', 'great', 'excellent', 'approve', 'perfect', 'nice']
        negative_words = ['bad', 'poor', 'terrible', 'reject', 'awful', 'wrong']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return {'sentiment': 'positive', 'score': 0.8}
        elif negative_count > positive_count:
            return {'sentiment': 'negative', 'score': 0.3}
        else:
            return {'sentiment': 'neutral', 'score': 0.5}
    
    def _extract_user_intent(self, text: str) -> str:
        """Extract user intent from feedback"""
        if any(word in text.lower() for word in ['approve', 'lgtm', 'ship']):
            return 'approve'
        elif any(word in text.lower() for word in ['reject', 'block', 'no']):
            return 'reject'
        elif any(word in text.lower() for word in ['change', 'fix', 'improve']):
            return 'request_changes'
        else:
            return 'comment'
    
    def _extract_ai_recommendations(self, content: str) -> List[str]:
        """Extract recommendations from AI feedback"""
        # Simple pattern matching for recommendations
        import re
        recommendations = []
        
        # Look for recommendation patterns
        patterns = [
            r'recommend[s]?\s+(.+?)(?:\.|$)',
            r'suggest[s]?\s+(.+?)(?:\.|$)',
            r'should\s+(.+?)(?:\.|$)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            recommendations.extend(matches)
        
        return recommendations[:5]  # Limit to top 5

# Initialize loop agent
loop_agent = LoopAgent()

@app.route('/start-loop', methods=['POST'])
def start_loop():
    """Start a new feedback loop for a PR"""
    try:
        data = request.get_json()
        pr_id = data.get('pr_id')
        
        if not pr_id:
            return jsonify({"error": "Missing pr_id"}), 400
        
        loop_state = loop_agent.start_feedback_loop(pr_id)
        
        return jsonify({
            "loop_started": True,
            "pr_id": pr_id,
            "current_stage": loop_state.current_stage,
            "started_at": loop_state.started_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to start loop: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/process-feedback', methods=['POST'])
def process_feedback():
    """Process feedback for a PR"""
    try:
        data = request.get_json()
        
        # Create feedback event
        feedback_event = FeedbackEvent(
            id=data.get('feedback_id', f"fb-{int(time.time())}"),
            pr_id=data.get('pr_id'),
            feedback_type=data.get('feedback_type', 'generic'),
            content=data.get('content', ''),
            confidence=data.get('confidence', 0.5),
            timestamp=datetime.utcnow(),
            source=data.get('source', 'api'),
            actionable=data.get('actionable', True)
        )
        
        if not feedback_event.pr_id:
            return jsonify({"error": "Missing pr_id"}), 400
        
        result = loop_agent.process_feedback(feedback_event.pr_id, feedback_event)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to process feedback: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/loop-status/<pr_id>', methods=['GET'])
def get_loop_status(pr_id: str):
    """Get current status of feedback loop"""
    try:
        if pr_id in loop_agent.active_loops:
            loop_state = loop_agent.active_loops[pr_id]
            
            return jsonify({
                "pr_id": pr_id,
                "current_stage": loop_state.current_stage,
                "total_feedback": loop_state.total_feedback_events,
                "iterations": len(loop_state.iterations),
                "converged": loop_state.converged,
                "quality_threshold_met": loop_state.quality_threshold_met,
                "started_at": loop_state.started_at.isoformat(),
                "last_activity": loop_state.last_activity.isoformat()
            })
        else:
            return jsonify({"error": "Loop not found"}), 404
            
    except Exception as e:
        logger.error(f"Failed to get loop status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "fmc-120-loop-agent",
        "version": "v1.0.0",
        "kpi_target": "feedback_seen_total ≥ 3 per PR",
        "active_loops": len(loop_agent.active_loops),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("Starting FMC-120 Loop Agent Service")
    logger.info("Purpose: Manage feedback ↔ prompt refinement loops")
    logger.info("KPI Target: feedback_seen_total ≥ 3 per PR")
    
    app.run(host='0.0.0.0', port=8088, debug=False) 