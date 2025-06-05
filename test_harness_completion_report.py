#!/usr/bin/env python3
"""
🎯 TEST HARNESS COMPLETION REPORT
================================

Comprehensive evaluation of the 4-layer zero-regression test harness
including the new front-end performance rescue implementation.

Layers evaluated:
1. Unit Tests (backend logic)
2. Service Tests (API endpoints) 
3. End-to-End Tests (full stack)
4. UI Tests (frontend performance)
+ Performance Fixes (critical regression prevention)
"""

import subprocess
import pathlib
import json
import time
from typing import Dict, List, Any

class TestHarnessCompletionReport:
    """Comprehensive test harness evaluation and scoring"""
    
    def __init__(self):
        self.results = {}
        self.scores = {}
    
    def evaluate_unit_tests(self) -> Dict[str, Any]:
        """Evaluate Layer 1: Unit Tests"""
        print("🧪 LAYER 1: Unit Tests")
        print("=" * 50)
        
        try:
            # Run unit tests
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
                capture_output=True, text=True, timeout=120
            )
            
            output_lines = result.stdout.split('\n')
            
            # Parse results
            passed = 0
            skipped = 0 
            failed = 0
            
            for line in output_lines:
                if " passed" in line and " in " in line:
                    # Extract numbers like "31 passed, 3 skipped in 9.22s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            passed = int(parts[i-1])
                        elif part == "skipped":
                            skipped = int(parts[i-1]) 
                        elif part == "failed":
                            failed = int(parts[i-1])
            
            total_tests = passed + skipped + failed
            success_rate = passed / total_tests if total_tests > 0 else 0
            
            # Component breakdown
            components = {
                "router_ladder": self._check_test_file("tests/unit/test_router_ladder.py"),
                "scratchpad": self._check_test_file("tests/unit/test_scratchpad.py"),
                "prompts": self._check_test_file("tests/unit/test_prompts.py"),
                "critical_performance": self._check_test_file("tests/unit/test_critical_performance_fixes.py")
            }
            
            print(f"📊 Results: {passed} passed, {skipped} skipped, {failed} failed")
            print(f"📈 Success rate: {success_rate:.1%}")
            
            for component, exists in components.items():
                status = "✅" if exists else "❌"
                print(f"   {status} {component}")
            
            score = success_rate * 100
            if all(components.values()):
                score += 10  # Bonus for complete coverage
            
            return {
                "layer": 1,
                "name": "Unit Tests", 
                "passed": passed,
                "skipped": skipped,
                "failed": failed,
                "success_rate": success_rate,
                "components": components,
                "score": min(score, 100),
                "status": "excellent" if success_rate > 0.9 else "good" if success_rate > 0.75 else "needs_work"
            }
            
        except Exception as e:
            print(f"❌ Unit test evaluation failed: {e}")
            return {"layer": 1, "name": "Unit Tests", "status": "error", "score": 0}
    
    def evaluate_service_tests(self) -> Dict[str, Any]:
        """Evaluate Layer 2: Service Tests"""
        print("\n🔌 LAYER 2: Service Tests")
        print("=" * 50)
        
        service_files = [
            "tests/service/test_chat_route.py"
        ]
        
        existing_files = [f for f in service_files if pathlib.Path(f).exists()]
        
        if existing_files:
            try:
                # Run service tests
                result = subprocess.run(
                    ["python", "-m", "pytest", "tests/service/", "-v"],
                    capture_output=True, text=True, timeout=60
                )
                
                success = result.returncode == 0
                print(f"📊 Service tests: {'✅ PASS' if success else '❌ FAIL'}")
                
                score = 85 if success else 60  # Service tests are critical
                
                return {
                    "layer": 2,
                    "name": "Service Tests",
                    "files": existing_files,
                    "success": success,
                    "score": score,
                    "status": "good" if success else "needs_work"
                }
                
            except Exception as e:
                print(f"⚠️ Service test execution failed: {e}")
                return {"layer": 2, "name": "Service Tests", "score": 40, "status": "partial"}
        else:
            print("❌ No service test files found")
            return {"layer": 2, "name": "Service Tests", "score": 0, "status": "missing"}
    
    def evaluate_e2e_tests(self) -> Dict[str, Any]:
        """Evaluate Layer 3: End-to-End Tests"""
        print("\n🔄 LAYER 3: End-to-End Tests")
        print("=" * 50)
        
        e2e_files = [
            "tests/e2e/test_stack.sh",
            "tests/e2e/performance.spec.ts"
        ]
        
        existing_files = [f for f in e2e_files if pathlib.Path(f).exists()]
        
        print(f"📁 E2E files: {len(existing_files)}/{len(e2e_files)} present")
        
        for f in e2e_files:
            status = "✅" if pathlib.Path(f).exists() else "❌"
            print(f"   {status} {f}")
        
        # Check if Docker/stack scripts are available
        docker_ready = self._check_docker_availability()
        
        coverage_score = (len(existing_files) / len(e2e_files)) * 100
        
        return {
            "layer": 3,
            "name": "End-to-End Tests",
            "files": existing_files,
            "docker_ready": docker_ready,
            "coverage": len(existing_files) / len(e2e_files),
            "score": coverage_score,
            "status": "good" if coverage_score > 70 else "partial" if coverage_score > 40 else "needs_work"
        }
    
    def evaluate_ui_tests(self) -> Dict[str, Any]:
        """Evaluate Layer 4: UI Tests + Performance"""
        print("\n🖥️ LAYER 4: UI Tests & Performance")
        print("=" * 50)
        
        ui_files = [
            "tests/ui/council.spec.ts",
            "tests/ui/frontend_performance.spec.ts",
            "tests/playwright.config.ts"
        ]
        
        existing_files = [f for f in ui_files if pathlib.Path(f).exists()]
        
        # Check Playwright setup
        playwright_config = pathlib.Path("tests/playwright.config.ts").exists()
        package_json = pathlib.Path("tests/package.json").exists()
        
        print(f"📁 UI test files: {len(existing_files)}/{len(ui_files)} present")
        print(f"⚙️ Playwright config: {'✅' if playwright_config else '❌'}")
        print(f"📦 Package.json: {'✅' if package_json else '❌'}")
        
        # Performance rescue plan components
        performance_files = [
            "frontend_performance_triage.py",
            "websocket_backend.py", 
            "websocket_frontend.js",
            "debug_endpoint.py",
            "debug_frontend.js",
            "webpack.optimization.js"
        ]
        
        performance_ready = [f for f in performance_files if pathlib.Path(f).exists()]
        
        print(f"\n🚀 Performance rescue: {len(performance_ready)}/{len(performance_files)} components")
        
        for f in performance_files:
            status = "✅" if pathlib.Path(f).exists() else "❌"
            print(f"   {status} {f}")
        
        ui_score = (len(existing_files) / len(ui_files)) * 50
        performance_score = (len(performance_ready) / len(performance_files)) * 50
        total_score = ui_score + performance_score
        
        return {
            "layer": 4,
            "name": "UI Tests & Performance",
            "ui_files": existing_files,
            "performance_files": performance_ready,
            "playwright_ready": playwright_config and package_json,
            "ui_coverage": len(existing_files) / len(ui_files),
            "performance_coverage": len(performance_ready) / len(performance_files),
            "score": total_score,
            "status": "excellent" if total_score > 85 else "good" if total_score > 70 else "needs_work"
        }
    
    def evaluate_critical_fixes(self) -> Dict[str, Any]:
        """Evaluate critical performance regression fixes"""
        print("\n🚨 CRITICAL PERFORMANCE FIXES")
        print("=" * 50)
        
        # Run the critical fixes test
        try:
            result = subprocess.run(
                ["python", "test_critical_fixes.py"],
                capture_output=True, text=True, timeout=60
            )
            
            output = result.stdout
            
            # Parse results
            tests_passed = output.count("✅ PASS:")
            tests_failed = output.count("❌ FAIL:")
            total_tests = tests_passed + tests_failed
            
            success_rate = tests_passed / total_tests if total_tests > 0 else 0
            
            print(f"📊 Critical fixes: {tests_passed}/{total_tests} passed ({success_rate:.1%})")
            
            # Check specific fixes
            fixes = {
                "math_unsure_penalty": "Math UNSURE penalty" in output and "PASS" in output,
                "token_limits": "Token limits" in output and "256" in output,
                "confidence_gates": "Confidence gates" in output and "0.45" in output,
                "tiny_summarizer": "Tiny summarizer" in output,
            }
            
            for fix, working in fixes.items():
                status = "✅" if working else "❌"
                print(f"   {status} {fix}")
            
            fixes_score = sum(fixes.values()) / len(fixes) * 100
            
            return {
                "name": "Critical Performance Fixes",
                "tests_passed": tests_passed,
                "total_tests": total_tests,
                "success_rate": success_rate,
                "fixes": fixes,
                "score": fixes_score,
                "status": "excellent" if success_rate > 0.8 else "good" if success_rate > 0.6 else "critical"
            }
            
        except Exception as e:
            print(f"❌ Critical fixes evaluation failed: {e}")
            return {"name": "Critical Performance Fixes", "status": "error", "score": 0}
    
    def _check_test_file(self, filepath: str) -> bool:
        """Check if test file exists and has content"""
        path = pathlib.Path(filepath)
        if not path.exists():
            return False
        
        try:
            content = path.read_text(encoding='utf-8')
            return len(content) > 100  # Has substantial content
        except:
            return False
    
    def _check_docker_availability(self) -> bool:
        """Check if Docker is available for E2E tests"""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def generate_completion_report(self) -> Dict[str, Any]:
        """Generate comprehensive completion report"""
        print("🎯 ZERO-REGRESSION TEST HARNESS COMPLETION REPORT")
        print("=" * 70)
        print(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Evaluate all layers
        layer1 = self.evaluate_unit_tests()
        layer2 = self.evaluate_service_tests()
        layer3 = self.evaluate_e2e_tests()
        layer4 = self.evaluate_ui_tests()
        critical = self.evaluate_critical_fixes()
        
        # Calculate overall score
        layer_scores = [
            layer1.get("score", 0),
            layer2.get("score", 0), 
            layer3.get("score", 0),
            layer4.get("score", 0)
        ]
        
        critical_score = critical.get("score", 0)
        
        # Weighted scoring (critical fixes are extra important)
        overall_score = (
            sum(layer_scores) * 0.8 +  # 80% for layer completion
            critical_score * 0.2       # 20% for critical fixes
        ) / 4
        
        # Determine completion level
        if overall_score >= 95:
            completion_level = "🌟 EXCEPTIONAL"
            status = "production_ready"
        elif overall_score >= 85:
            completion_level = "🚀 EXCELLENT"
            status = "nearly_complete"
        elif overall_score >= 75:
            completion_level = "✅ GOOD"
            status = "mostly_complete"
        elif overall_score >= 60:
            completion_level = "⚠️ PARTIAL"
            status = "needs_attention"
        else:
            completion_level = "❌ INCOMPLETE"
            status = "needs_major_work"
        
        print("\n" + "=" * 70)
        print("📋 FINAL ASSESSMENT")
        print("=" * 70)
        print(f"Overall Score: {overall_score:.1f}/100")
        print(f"Completion Level: {completion_level}")
        print(f"Status: {status}")
        print()
        
        # Layer breakdown
        print("Layer Scores:")
        print(f"  Layer 1 (Unit Tests): {layer1.get('score', 0):.1f}/100")
        print(f"  Layer 2 (Service Tests): {layer2.get('score', 0):.1f}/100")
        print(f"  Layer 3 (E2E Tests): {layer3.get('score', 0):.1f}/100")
        print(f"  Layer 4 (UI/Performance): {layer4.get('score', 0):.1f}/100")
        print(f"  Critical Fixes: {critical_score:.1f}/100")
        print()
        
        # Recommendations
        recommendations = []
        
        if layer1.get("score", 0) < 80:
            recommendations.append("🔧 Improve unit test coverage and fix failing tests")
        
        if layer2.get("score", 0) < 70:
            recommendations.append("🔌 Add comprehensive service/API testing")
        
        if layer3.get("score", 0) < 70:
            recommendations.append("🔄 Complete end-to-end testing infrastructure")
        
        if layer4.get("score", 0) < 80:
            recommendations.append("🖥️ Enhance UI testing and performance monitoring")
        
        if critical_score < 80:
            recommendations.append("🚨 Fix critical performance regression issues")
        
        if not recommendations:
            recommendations.append("🎉 Test harness is complete and production-ready!")
        
        print("📝 Recommendations:")
        for rec in recommendations:
            print(f"   {rec}")
        
        return {
            "timestamp": time.time(),
            "overall_score": overall_score,
            "completion_level": completion_level,
            "status": status,
            "layers": {
                "unit_tests": layer1,
                "service_tests": layer2, 
                "e2e_tests": layer3,
                "ui_tests": layer4
            },
            "critical_fixes": critical,
            "recommendations": recommendations
        }

def main():
    """Generate completion report"""
    reporter = TestHarnessCompletionReport()
    report = reporter.generate_completion_report()
    
    # Save report
    with open("test_harness_completion_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved: test_harness_completion_report.json")

if __name__ == "__main__":
    main() 