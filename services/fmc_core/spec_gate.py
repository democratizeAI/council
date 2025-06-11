#!/usr/bin/env python3
"""
FMC-110: Spec Gate Service  
Only allows /ledger rows with valid CI tests and prevents hallucinated specs from entering the system
KPI: invalid_spec_total = 0
"""

import re
import json
import yaml
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Prometheus metrics
invalid_spec_total = Counter('invalid_spec_total', 'Invalid specs blocked by gate', ['reason'])
spec_gate_validations = Counter('spec_gate_validations_total', 'Total spec validations', ['result'])
spec_gate_latency = Gauge('spec_gate_latency_ms', 'Spec validation latency in ms')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of spec validation"""
    valid: bool
    spec_id: str
    errors: List[str]
    warnings: List[str]
    ci_tests_valid: bool
    success_criteria_valid: bool
    confidence_score: float

class SpecGate:
    """Validates specs before they enter the ledger system"""
    
    def __init__(self):
        self.required_spec_fields = [
            'id', 'title', 'description', 'success_criteria', 'ci_tests', 
            'rollback_plan', 'estimated_effort', 'owner'
        ]
        
        self.valid_ci_test_patterns = [
            r'assert\s+.*',  # Assert statements
            r'expect\s*\(.*\)\.to.*',  # Expect patterns
            r'curl\s+.*\|\s*(grep|jq)',  # API tests
            r'pytest\s+.*',  # PyTest commands
            r'npm\s+test.*',  # NPM tests
            r'docker\s+.*\s+test',  # Docker tests
            r'make\s+test.*',  # Makefile tests
            r'.*\.status_code\s*==\s*200',  # HTTP status checks
            r'.*response\.json\(\).*',  # JSON response checks
            r'.*\.should\.contain.*',  # Chai-style assertions
        ]
        
        self.hallucination_indicators = [
            r'TODO:?\s*implement',  # Placeholder implementations
            r'FIXME:?\s*.*',  # Fixme comments
            r'XXX:?\s*.*',  # XXX comments
            r'placeholder.*test',  # Placeholder tests
            r'example.*test',  # Example tests
            r'dummy.*test',  # Dummy tests
            r'mock.*response',  # Mock-only tests without validation
            r'return\s+true\s*;?\s*$',  # Always-true returns
            r'pass\s*$',  # Python pass statements as tests
            r'console\.log\s*\(',  # Console.log as tests
        ]
        
        self.success_criteria_patterns = [
            r'.*\s*[<>=]+\s*\d+',  # Numeric thresholds
            r'.*\s*(pass|fail|error|success)',  # Binary outcomes
            r'.*\s*HTTP\s*[0-9]{3}',  # HTTP status codes
            r'.*\s*response\s*time.*ms',  # Performance criteria
            r'.*\s*accuracy.*%',  # Accuracy metrics
            r'.*\s*coverage.*%',  # Coverage metrics
        ]
        
    def validate_spec(self, spec_data: Dict) -> ValidationResult:
        """Comprehensive spec validation with hallucination detection"""
        start_time = time.time()
        
        try:
            spec_id = spec_data.get('id', 'unknown')
            errors = []
            warnings = []
            
            # 1. Required fields validation
            missing_fields = self._validate_required_fields(spec_data)
            errors.extend(missing_fields)
            
            # 2. CI tests validation
            ci_tests_valid, ci_errors = self._validate_ci_tests(spec_data.get('ci_tests', []))
            errors.extend(ci_errors)
            
            # 3. Success criteria validation
            success_criteria_valid, success_errors = self._validate_success_criteria(
                spec_data.get('success_criteria', [])
            )
            errors.extend(success_errors)
            
            # 4. Hallucination detection
            hallucination_warnings = self._detect_hallucinations(spec_data)
            warnings.extend(hallucination_warnings)
            
            # 5. Rollback plan validation
            rollback_errors = self._validate_rollback_plan(spec_data.get('rollback_plan', ''))
            errors.extend(rollback_errors)
            
            # 6. Effort estimation validation
            effort_warnings = self._validate_effort_estimation(spec_data.get('estimated_effort', ''))
            warnings.extend(effort_warnings)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                len(errors), len(warnings), ci_tests_valid, success_criteria_valid
            )
            
            # Determine if spec is valid
            is_valid = len(errors) == 0 and ci_tests_valid and success_criteria_valid
            
            # Update metrics
            latency_ms = (time.time() - start_time) * 1000
            spec_gate_latency.set(latency_ms)
            
            result = 'valid' if is_valid else 'invalid'
            spec_gate_validations.labels(result=result).inc()
            
            if not is_valid:
                # Track reasons for invalidity
                if not ci_tests_valid:
                    invalid_spec_total.labels(reason='invalid_ci_tests').inc()
                if not success_criteria_valid:
                    invalid_spec_total.labels(reason='invalid_success_criteria').inc()
                if missing_fields:
                    invalid_spec_total.labels(reason='missing_fields').inc()
            
            result = ValidationResult(
                valid=is_valid,
                spec_id=spec_id,
                errors=errors,
                warnings=warnings,
                ci_tests_valid=ci_tests_valid,
                success_criteria_valid=success_criteria_valid,
                confidence_score=confidence_score
            )
            
            logger.info(f"Spec validation: {spec_id} - {'VALID' if is_valid else 'INVALID'} "
                       f"(confidence: {confidence_score:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Spec validation failed: {e}")
            raise
    
    def _validate_required_fields(self, spec_data: Dict) -> List[str]:
        """Validate required fields are present"""
        errors = []
        for field in self.required_spec_fields:
            if field not in spec_data or not spec_data[field]:
                errors.append(f"Missing required field: {field}")
        return errors
    
    def _validate_ci_tests(self, ci_tests: List) -> Tuple[bool, List[str]]:
        """Validate CI tests are real and executable"""
        errors = []
        
        if not ci_tests:
            errors.append("No CI tests defined")
            return False, errors
        
        valid_tests = 0
        
        for i, test in enumerate(ci_tests):
            test_str = str(test)
            
            # Check for hallucination indicators
            for pattern in self.hallucination_indicators:
                if re.search(pattern, test_str, re.IGNORECASE):
                    errors.append(f"Test {i+1} appears to be placeholder/hallucinated: {test_str[:50]}...")
                    continue
            
            # Check for valid test patterns
            is_valid_test = False
            for pattern in self.valid_ci_test_patterns:
                if re.search(pattern, test_str, re.IGNORECASE):
                    is_valid_test = True
                    break
            
            if is_valid_test:
                valid_tests += 1
            else:
                errors.append(f"Test {i+1} does not match valid CI test patterns: {test_str[:50]}...")
        
        # Require at least one valid test
        tests_valid = valid_tests > 0 and len(errors) == 0
        
        if valid_tests == 0:
            errors.append("No valid CI tests found")
        
        return tests_valid, errors
    
    def _validate_success_criteria(self, success_criteria: List) -> Tuple[bool, List[str]]:
        """Validate success criteria are measurable"""
        errors = []
        
        if not success_criteria:
            errors.append("No success criteria defined")
            return False, errors
        
        valid_criteria = 0
        
        for i, criterion in enumerate(success_criteria):
            criterion_str = str(criterion)
            
            # Check for measurable patterns
            is_measurable = False
            for pattern in self.success_criteria_patterns:
                if re.search(pattern, criterion_str, re.IGNORECASE):
                    is_measurable = True
                    break
            
            if is_measurable:
                valid_criteria += 1
            else:
                # Check for vague/unmeasurable criteria
                vague_patterns = [
                    r'works well', r'looks good', r'seems fine',
                    r'user friendly', r'optimized', r'improved'
                ]
                
                is_vague = any(re.search(p, criterion_str, re.IGNORECASE) for p in vague_patterns)
                
                if is_vague:
                    errors.append(f"Success criterion {i+1} is too vague: {criterion_str}")
                else:
                    errors.append(f"Success criterion {i+1} is not measurable: {criterion_str}")
        
        criteria_valid = valid_criteria > 0 and len(errors) == 0
        
        if valid_criteria == 0:
            errors.append("No measurable success criteria found")
        
        return criteria_valid, errors
    
    def _detect_hallucinations(self, spec_data: Dict) -> List[str]:
        """Detect potential hallucinated content in spec"""
        warnings = []
        
        # Check all text fields for hallucination patterns
        text_fields = ['description', 'title', 'rollback_plan']
        
        for field in text_fields:
            if field in spec_data:
                content = str(spec_data[field])
                
                for pattern in self.hallucination_indicators:
                    if re.search(pattern, content, re.IGNORECASE):
                        warnings.append(f"Potential placeholder content in {field}: {pattern}")
        
        # Check for generic/template content
        generic_phrases = [
            r'lorem ipsum', r'sample.*data', r'example.*content',
            r'template.*text', r'placeholder.*content'
        ]
        
        full_content = json.dumps(spec_data).lower()
        for phrase in generic_phrases:
            if re.search(phrase, full_content):
                warnings.append(f"Generic template content detected: {phrase}")
        
        return warnings
    
    def _validate_rollback_plan(self, rollback_plan: str) -> List[str]:
        """Validate rollback plan is actionable"""
        errors = []
        
        if not rollback_plan or len(rollback_plan.strip()) < 10:
            errors.append("Rollback plan is too short or missing")
            return errors
        
        # Check for actionable verbs
        actionable_patterns = [
            r'\b(revert|rollback|restore|reset|disable|stop)\b',
            r'\b(git\s+revert|docker\s+stop|kubectl\s+rollout\s+undo)\b',
            r'\b(systemctl\s+stop|service\s+stop)\b'
        ]
        
        has_actionable_steps = any(
            re.search(pattern, rollback_plan, re.IGNORECASE) 
            for pattern in actionable_patterns
        )
        
        if not has_actionable_steps:
            errors.append("Rollback plan lacks actionable steps")
        
        return errors
    
    def _validate_effort_estimation(self, estimated_effort: str) -> List[str]:
        """Validate effort estimation is reasonable"""
        warnings = []
        
        effort_str = str(estimated_effort).lower()
        
        # Check for time indicators
        time_patterns = [
            r'\d+\s*(hour|day|week|month)s?',
            r'\d+\s*h\b', r'\d+\s*d\b', r'\d+\s*w\b'
        ]
        
        has_time_estimate = any(
            re.search(pattern, effort_str) for pattern in time_patterns
        )
        
        if not has_time_estimate:
            warnings.append("Effort estimation lacks specific time estimate")
        
        # Check for unrealistic estimates
        if re.search(r'\b(5|10)\s*minutes?\b', effort_str):
            warnings.append("Effort estimate may be unrealistically low")
        
        if re.search(r'\b(6|12)\s*months?\b', effort_str):
            warnings.append("Effort estimate may be unrealistically high")
        
        return warnings
    
    def _calculate_confidence_score(self, error_count: int, warning_count: int, 
                                  ci_valid: bool, criteria_valid: bool) -> float:
        """Calculate confidence score for validation"""
        base_score = 1.0
        
        # Deduct for errors (critical)
        base_score -= error_count * 0.2
        
        # Deduct for warnings (minor)
        base_score -= warning_count * 0.05
        
        # Boost for valid components
        if ci_valid:
            base_score += 0.1
        if criteria_valid:
            base_score += 0.1
        
        return max(0.0, min(1.0, base_score))

# Initialize spec gate
gate = SpecGate()

@app.route('/validate-spec', methods=['POST'])
def validate_spec_endpoint():
    """FMC-110 spec validation endpoint"""
    try:
        data = request.get_json()
        
        if 'spec' not in data:
            return jsonify({"error": "Missing 'spec' field"}), 400
        
        # Validate spec
        result = gate.validate_spec(data['spec'])
        
        # Format response
        response = {
            "validation_result": {
                "valid": result.valid,
                "spec_id": result.spec_id,
                "errors": result.errors,
                "warnings": result.warnings,
                "ci_tests_valid": result.ci_tests_valid,
                "success_criteria_valid": result.success_criteria_valid,
                "confidence_score": result.confidence_score
            },
            "gate_metadata": {
                "service": "FMC-110",
                "version": "v1.0.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "kpi_target": "invalid_spec_total = 0"
            }
        }
        
        # Block invalid specs
        if not result.valid:
            logger.warning(f"Spec blocked: {result.spec_id} - {len(result.errors)} errors")
            return jsonify(response), 422  # Unprocessable Entity
        
        logger.info(f"Spec validated: {result.spec_id} - PASS")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Spec validation endpoint failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/validate-ledger-entry', methods=['POST'])
def validate_ledger_entry():
    """Validate ledger entry before insertion"""
    try:
        data = request.get_json()
        
        # Extract spec from ledger entry
        spec_data = data.get('ticket_data', {})
        
        if not spec_data:
            return jsonify({
                "error": "No spec data found in ledger entry",
                "blocked": True
            }), 422
        
        # Validate the spec
        result = gate.validate_spec(spec_data)
        
        if not result.valid:
            logger.warning(f"Ledger entry blocked: {result.spec_id}")
            return jsonify({
                "blocked": True,
                "reason": "Invalid spec",
                "errors": result.errors,
                "spec_id": result.spec_id
            }), 422
        
        # Allow entry to proceed
        return jsonify({
            "blocked": False,
            "validated": True,
            "spec_id": result.spec_id,
            "confidence": result.confidence_score
        })
        
    except Exception as e:
        logger.error(f"Ledger entry validation failed: {e}")
        return jsonify({"error": str(e), "blocked": True}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "fmc-110-spec-gate",
        "version": "v1.0.0",
        "kpi_target": "invalid_spec_total = 0",
        "purpose": "Prevent hallucinated specs from entering Builder Swarm",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("Starting FMC-110 Spec Gate Service")
    logger.info("Purpose: Block invalid specs and hallucinations")
    logger.info("KPI Target: invalid_spec_total = 0")
    
    app.run(host='0.0.0.0', port=8087, debug=False) 