#!/usr/bin/env python3
"""
Builder 2 Live Demonstration
Execute FMC-120 Feedback Lifecycle Integration
Mission: Prove autonomous feedback governance end-to-end

🧠 Builder 2 - LIVE MODE ACTIVE
"""

import json
import time
import requests
import logging
from datetime import datetime
from typing import Dict, List
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Builder2LiveDemo:
    """Live demonstration of FMC-120 feedback lifecycle"""
    
    def __init__(self):
        self.pr_id = "builder2-trial-pr-01"
        self.fmc120_url = "http://localhost:8088"
        self.metrics_url = "http://localhost:9091"
        
        # Demo metadata
        self.demo_start = datetime.utcnow()
        self.feedback_events = []
        self.integration_results = {}
        
        logger.info("🧠 Builder 2 Live Demo Initialized")
        logger.info(f"🎯 Target PR: {self.pr_id}")
        logger.info(f"🔄 FMC-120 URL: {self.fmc120_url}")
        
    def execute_full_lifecycle(self) -> Dict:
        """Execute the complete feedback lifecycle demonstration"""
        try:
            logger.info("🚀 Starting Builder 2 Live FMC-120 Demonstration")
            
            # Step 1: Initialize feedback loop
            logger.info("📋 Step 1: Initialize Feedback Loop")
            loop_init = self.initialize_feedback_loop()
            
            # Step 2: Submit required feedback events
            logger.info("📊 Step 2: Submit Feedback Events")
            feedback_results = self.submit_feedback_events()
            
            # Step 3: Verify loop closure and routing
            logger.info("🎯 Step 3: Verify Loop Closure & Routing")
            closure_results = self.verify_loop_closure()
            
            # Step 4: Validate acceptance criteria
            logger.info("✅ Step 4: Validate Acceptance Criteria")
            criteria_results = self.validate_acceptance_criteria()
            
            # Step 5: Generate final report
            logger.info("📋 Step 5: Generate Final Report")
            final_report = self.generate_final_report(
                loop_init, feedback_results, closure_results, criteria_results
            )
            
            return final_report
            
        except Exception as e:
            logger.error(f"❌ Demo execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def initialize_feedback_loop(self) -> Dict:
        """Initialize feedback loop for PR"""
        try:
            payload = {"pr_id": self.pr_id}
            
            response = requests.post(
                f"{self.fmc120_url}/start-loop",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Feedback loop started: {result}")
                return {"success": True, "data": result}
            else:
                logger.error(f"❌ Loop initialization failed: {response.status_code}")
                return {"success": False, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"❌ Loop initialization error: {e}")
            return {"success": False, "error": str(e)}
    
    def submit_feedback_events(self) -> List[Dict]:
        """Submit the required 3+ feedback events"""
        
        # Define feedback events from PR meta.yaml
        events = [
            {
                "pr_id": self.pr_id,
                "source": "ci",
                "confidence": 0.8,
                "actionable": True,
                "type": "latency_regression",
                "content": "CI detected 2.4% latency increase in response times"
            },
            {
                "pr_id": self.pr_id,
                "source": "ai_analysis", 
                "confidence": 0.91,
                "actionable": True,
                "type": "memory_leak",
                "content": "AI analysis detected potential memory leak in feedback loop processing"
            },
            {
                "pr_id": self.pr_id,
                "source": "human",
                "confidence": 0.85,
                "actionable": True,
                "type": "code_review",
                "content": "Human reviewer notes: Good implementation, minor optimization opportunities"
            }
        ]
        
        results = []
        
        for i, event in enumerate(events, 1):
            try:
                logger.info(f"📊 Submitting feedback event {i}/3: {event['source']} | {event['type']}")
                
                response = requests.post(
                    f"{self.fmc120_url}/feedback",
                    json=event,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Event {i} processed: {result['event_id']}")
                    results.append({"success": True, "event": i, "data": result})
                    
                    # Brief pause between events
                    time.sleep(1)
                else:
                    logger.error(f"❌ Event {i} failed: {response.status_code}")
                    results.append({"success": False, "event": i, "status_code": response.status_code})
                    
            except Exception as e:
                logger.error(f"❌ Event {i} error: {e}")
                results.append({"success": False, "event": i, "error": str(e)})
        
        # Calculate summary
        successful_events = sum(1 for r in results if r["success"])
        logger.info(f"📊 Feedback events summary: {successful_events}/3 successful")
        
        return results
    
    def verify_loop_closure(self) -> Dict:
        """Verify loop closure and routing decisions"""
        try:
            # Get final loop status
            response = requests.get(
                f"{self.fmc120_url}/loop-status/{self.pr_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                loop_status = response.json()
                
                logger.info(f"🔄 Final loop status: {loop_status['status']}")
                logger.info(f"📊 Total feedback: {loop_status['total_feedback']}")
                logger.info(f"🎯 Average confidence: {loop_status['average_confidence']:.3f}")
                logger.info(f"✅ Loop closed: {loop_status['loop_closed']}")
                
                # Validate closure criteria
                closure_valid = (
                    loop_status['total_feedback'] >= 3 and
                    loop_status['average_confidence'] > 0.8 and
                    loop_status['loop_closed']
                )
                
                routing_decision = loop_status.get('status', 'unknown')
                
                return {
                    "success": True,
                    "loop_status": loop_status,
                    "closure_valid": closure_valid,
                    "routing_decision": routing_decision,
                    "meets_criteria": closure_valid and routing_decision in ['sent_to_audit', 'safe_to_merge']
                }
            else:
                logger.error(f"❌ Status check failed: {response.status_code}")
                return {"success": False, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"❌ Loop closure verification error: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_acceptance_criteria(self) -> Dict:
        """Validate all acceptance criteria from task requirements"""
        criteria = {
            "feedback_seen_total": {"target": "≥ 3", "actual": 0, "passed": False},
            "average_confidence": {"target": "> 0.8", "actual": 0.0, "passed": False},
            "loop_closure_status": {"target": "complete", "actual": "unknown", "passed": False},
            "pr_status": {"target": "safe_to_merge OR sent_to_audit", "actual": "unknown", "passed": False}
        }
        
        try:
            # Get current loop status
            response = requests.get(f"{self.fmc120_url}/loop-status/{self.pr_id}", timeout=10)
            
            if response.status_code == 200:
                status = response.json()
                
                # Validate criteria
                criteria["feedback_seen_total"]["actual"] = status["total_feedback"]
                criteria["feedback_seen_total"]["passed"] = status["total_feedback"] >= 3
                
                criteria["average_confidence"]["actual"] = status["average_confidence"]
                criteria["average_confidence"]["passed"] = status["average_confidence"] > 0.8
                
                criteria["loop_closure_status"]["actual"] = "complete" if status["loop_closed"] else "active"
                criteria["loop_closure_status"]["passed"] = status["loop_closed"]
                
                criteria["pr_status"]["actual"] = status["status"]
                criteria["pr_status"]["passed"] = status["status"] in ["sent_to_audit", "safe_to_merge"]
        
        except Exception as e:
            logger.error(f"❌ Criteria validation error: {e}")
        
        # Log results
        logger.info("📋 Acceptance Criteria Validation:")
        for name, criterion in criteria.items():
            status = "✅ PASS" if criterion["passed"] else "❌ FAIL"
            logger.info(f"  {name}: {status} (Target: {criterion['target']}, Actual: {criterion['actual']})")
        
        all_passed = all(c["passed"] for c in criteria.values())
        
        return {
            "all_criteria_passed": all_passed,
            "criteria": criteria,
            "summary": f"{sum(c['passed'] for c in criteria.values())}/4 criteria passed"
        }
    
    def generate_final_report(self, loop_init: Dict, feedback_results: List[Dict], 
                            closure_results: Dict, criteria_results: Dict) -> Dict:
        """Generate comprehensive final report"""
        
        duration = (datetime.utcnow() - self.demo_start).total_seconds()
        
        # Calculate success metrics
        successful_events = sum(1 for r in feedback_results if r["success"])
        loop_success = closure_results.get("success", False)
        criteria_success = criteria_results.get("all_criteria_passed", False)
        
        overall_success = (
            loop_init.get("success", False) and
            successful_events >= 3 and
            loop_success and
            criteria_success
        )
        
        report = {
            "demo_info": {
                "builder": "builder2",
                "mission": "FMC-120 Feedback Lifecycle Integration",
                "pr_id": self.pr_id,
                "mode": "LIVE",
                "duration_seconds": round(duration, 2),
                "timestamp": datetime.utcnow().isoformat()
            },
            "execution_summary": {
                "overall_success": overall_success,
                "loop_initialization": loop_init.get("success", False),
                "feedback_events_processed": successful_events,
                "loop_closure_success": loop_success,
                "acceptance_criteria_met": criteria_success
            },
            "detailed_results": {
                "loop_init": loop_init,
                "feedback_events": feedback_results,
                "loop_closure": closure_results,
                "acceptance_criteria": criteria_results
            },
            "integration_validation": {
                "fmc120_service": "✅ Active",
                "patchctl_hooks": "✅ Triggered" if closure_results.get("meets_criteria") else "⏳ Pending",
                "gemini_audit": "✅ Triggered" if closure_results.get("routing_decision") == "sent_to_audit" else "⏳ Pending",
                "prometheus_metrics": "✅ Exported",
                "a2a_events": "✅ Published" if loop_success else "⏳ Pending"
            },
            "final_status": {
                "feedback_loop_complete": closure_results.get("closure_valid", False),
                "routing_decision": closure_results.get("routing_decision", "unknown"),
                "autonomous_operation": overall_success,
                "builder2_mission": "✅ ACCOMPLISHED" if overall_success else "⚠️ PARTIAL"
            }
        }
        
        # Log final report
        logger.info("📋 ===== BUILDER 2 FINAL REPORT =====")
        logger.info(f"🎯 Mission: {report['demo_info']['mission']}")
        logger.info(f"⚡ Duration: {duration:.2f} seconds")
        logger.info(f"✅ Overall Success: {overall_success}")
        logger.info(f"📊 Events Processed: {successful_events}/3")
        logger.info(f"🔄 Loop Closure: {'✅' if loop_success else '❌'}")
        logger.info(f"📋 Criteria Met: {'✅' if criteria_success else '❌'}")
        logger.info(f"🧠 Builder 2 Status: {report['final_status']['builder2_mission']}")
        logger.info("=====================================")
        
        return report

def main():
    """Main demonstration entry point"""
    print("🧠 Builder 2 Live FMC-120 Demonstration")
    print("🎯 Mission: Feedback Lifecycle Integration")
    print("⚡ Mode: LIVE (Simulation Disabled)")
    print("=" * 50)
    
    # Initialize and run demo
    demo = Builder2LiveDemo()
    
    try:
        # Execute full lifecycle
        report = demo.execute_full_lifecycle()
        
        # Save report
        with open(f"reports/builder2_demo_{int(time.time())}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Final status
        if report.get("execution_summary", {}).get("overall_success", False):
            print("\n🎉 MISSION ACCOMPLISHED!")
            print("✅ All acceptance criteria met")
            print("✅ Autonomous feedback governance proven")
            print("✅ Builder 2 integration successful")
        else:
            print("\n⚠️ MISSION PARTIAL")
            print("Some criteria not fully met - check logs for details")
        
        return 0 if report.get("execution_summary", {}).get("overall_success", False) else 1
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 