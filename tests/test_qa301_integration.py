#!/usr/bin/env python3
"""
QA-301 Integration Tests - Meta Hash Audit
==========================================

Comprehensive test suite for meta hash audit functionality including:
- Hash determinism verification 
- Hash comparison logic
- Quorum decision making
- PatchCtl integration
- meta.yaml flag updates

Run with: python -m pytest tests/test_qa301_integration.py -v
"""

import pytest
import asyncio
import tempfile
import os
import json
import yaml
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
from aiohttp import web

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.explain_meta import PhiMiniExplainer
from tools.meta_hash_audit import MetaHashAuditor, HashComparison, QuorumDecision

class TestPhiMiniExplainer:
    """Test the Phi-3-mini explainer functionality"""
    
    @pytest.fixture
    def explainer(self):
        return PhiMiniExplainer()
        
    @pytest.fixture
    def sample_diff(self):
        return """--- a/services/api.py
+++ b/services/api.py
@@ -10,6 +10,8 @@ class APIService:
     def __init__(self):
         self.app = FastAPI()
+        self.health_check_enabled = True
+        
     def start(self):
         uvicorn.run(self.app, port=8000)"""
        
    def test_hash_determinism(self, explainer, sample_diff):
        """Test that identical inputs produce identical hashes"""
        async def run_test():
            # Generate explanations for identical inputs
            result1 = await explainer.explain_changes(
                diff_content=sample_diff,
                intent="Add health check flag",
                affected_files=["api.py"]
            )
            
            result2 = await explainer.explain_changes(
                diff_content=sample_diff,
                intent="Add health check flag", 
                affected_files=["api.py"]
            )
            
            # Hashes should be identical for identical inputs
            assert result1["meta_hash"] == result2["meta_hash"]
            assert result1["summary"] == result2["summary"]
            assert result1["logic_change_type"] == result2["logic_change_type"]
            
        asyncio.run(run_test())
        
    def test_hash_generation_format(self, explainer):
        """Test that generated hashes follow expected format"""
        async def run_test():
            result = await explainer.explain_changes(
                diff_content="test diff",
                intent="test intent"
            )
            
            # Hash should be 8 characters (as per QA-301 spec)
            assert len(result["meta_hash"]) == 8
            assert result["meta_hash"].isalnum()
            
            # Required fields should be present
            assert "summary" in result
            assert "logic_change_type" in result
            assert "affected_modules" in result
            assert "deterministic" in result
            assert result["deterministic"] is True
            
        asyncio.run(run_test())
        
    def test_fallback_explanation(self, explainer):
        """Test fallback behavior when Phi-3-mini fails"""
        
        # Mock Phi-3-mini failure
        with patch.object(explainer, '_query_phi_mini', side_effect=Exception("API Error")):
            async def run_test():
                result = await explainer.explain_changes(
                    diff_content="test diff",
                    intent="test intent",
                    affected_files=["test.py"]
                )
                
                # Should still generate valid response
                assert "meta_hash" in result
                assert "summary" in result
                assert result["model"] == "fallback_heuristic"
                
            asyncio.run(run_test())

class TestMetaHashAuditor:
    """Test the meta hash auditor functionality"""
    
    @pytest.fixture
    def auditor(self):
        return MetaHashAuditor()
        
    @pytest.fixture
    def temp_files(self):
        """Create temporary files for testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Meta file with Phi-3 hash
        meta_file = os.path.join(temp_dir, "meta.yaml")
        with open(meta_file, 'w') as f:
            yaml.dump({
                "meta_hash": "abc12345",
                "summary": "Test PR changes",
                "logic_change_type": "feature",
                "affected_modules": ["api.py"]
            }, f)
            
        # Audit log with matching hash
        audit_log_match = os.path.join(temp_dir, "audit_match.yaml")
        with open(audit_log_match, 'w') as f:
            yaml.dump({
                "hash": "abc12345",
                "summary": "Test PR changes",
                "audit_result": "pass"
            }, f)
            
        # Audit log with mismatching hash
        audit_log_mismatch = os.path.join(temp_dir, "audit_mismatch.yaml")
        with open(audit_log_mismatch, 'w') as f:
            yaml.dump({
                "hash": "xyz98765",
                "summary": "Different explanation",
                "audit_result": "pass"
            }, f)
            
        return {
            "temp_dir": temp_dir,
            "meta_file": meta_file,
            "audit_log_match": audit_log_match,
            "audit_log_mismatch": audit_log_mismatch
        }
        
    def test_exact_hash_match(self, auditor, temp_files):
        """Test exact hash matching behavior"""
        async def run_test():
            decision = await auditor.audit_pr_hash(
                pr_id="QA-301-test",
                meta_file=temp_files["meta_file"],
                audit_log=temp_files["audit_log_match"]
            )
            
            assert decision.passed is True
            assert decision.reason == "hash_match"
            assert decision.phi3_hash == "abc12345"
            assert decision.audit_hash == "abc12345"
            assert decision.confidence == 1.0
            
        asyncio.run(run_test())
        
    def test_hash_mismatch(self, auditor, temp_files):
        """Test hash mismatch behavior"""
        async def run_test():
            decision = await auditor.audit_pr_hash(
                pr_id="QA-301-test",
                meta_file=temp_files["meta_file"],
                audit_log=temp_files["audit_log_mismatch"]
            )
            
            assert decision.passed is False
            assert decision.reason == "hash_mismatch"
            assert decision.phi3_hash == "abc12345"
            assert decision.audit_hash == "xyz98765"
            assert decision.confidence == 0.0
            
        asyncio.run(run_test())
        
    def test_semantic_similarity_matching(self, auditor):
        """Test semantic similarity matching when hashes differ"""
        
        phi3_data = {
            "meta_hash": "abc12345",
            "summary": "Add health check endpoint to API service"
        }
        
        audit_data = {
            "hash": "xyz98765", 
            "summary": "Add health check endpoint to API service"  # Same summary
        }
        
        async def run_test():
            comparison = await auditor._compare_hashes(
                "abc12345", "xyz98765", phi3_data, audit_data
            )
            
            # Should match due to identical summaries
            assert comparison.match is True
            assert comparison.confidence >= auditor.similarity_threshold
            assert "semantic similarity" in comparison.explanation.lower()
            
        asyncio.run(run_test())
        
    def test_text_similarity_calculation(self, auditor):
        """Test text similarity calculation"""
        
        # Identical text
        similarity = auditor._calculate_text_similarity(
            "Add health check endpoint",
            "Add health check endpoint"
        )
        assert similarity == 1.0
        
        # Similar text
        similarity = auditor._calculate_text_similarity(
            "Add health check endpoint to API",
            "Add health check endpoint to service"
        )
        assert 0.5 <= similarity <= 1.0
        
        # Different text
        similarity = auditor._calculate_text_similarity(
            "Add health check endpoint",
            "Remove database connection"
        )
        assert similarity < 0.5
        
    def test_meta_yaml_update(self, auditor, temp_files):
        """Test meta.yaml update functionality"""
        async def run_test():
            decision = QuorumDecision(
                pr_id="QA-301-test",
                passed=True,
                reason="hash_match",
                phi3_hash="abc12345",
                audit_hash="abc12345",
                confidence=1.0,
                timestamp=1234567890.0,
                actions_taken=[]
            )
            
            await auditor._update_meta_yaml(
                "QA-301-test", 
                decision, 
                temp_files["meta_file"]
            )
            
            # Verify meta.yaml was updated
            with open(temp_files["meta_file"]) as f:
                updated_meta = yaml.safe_load(f)
                
            assert updated_meta["quorum_passed"] is True
            assert updated_meta["quorum_reason"] == "hash_match"
            assert updated_meta["phi3_hash"] == "abc12345"
            assert updated_meta["audit_hash"] == "abc12345"
            assert updated_meta["hash_confidence"] == 1.0
            
        asyncio.run(run_test())

class TestPatchCtlIntegration:
    """Test PatchCtl integration functionality"""
    
    @pytest.fixture
    async def mock_patchctl_server(self):
        """Mock PatchCtl server for testing"""
        app = web.Application()
        
        # Mock audit endpoint
        audit_responses = {}
        
        async def get_audit(request):
            pr_id = request.match_info['pr_id']
            if pr_id in audit_responses:
                return web.json_response(audit_responses[pr_id])
            else:
                return web.json_response(
                    {"audit_hash": "default123", "status": "pending"},
                    status=200
                )
                
        async def update_quorum(request):
            data = await request.json()
            return web.json_response({"status": "updated", "data": data})
            
        app.router.add_get('/audit/{pr_id}', get_audit)
        app.router.add_patch('/quorum/{pr_id}', update_quorum)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8090)
        await site.start()
        
        # Store reference for setting test responses
        app['audit_responses'] = audit_responses
        
        yield app
        
        await runner.cleanup()
        
    @pytest.mark.asyncio
    async def test_patchctl_audit_retrieval(self, mock_patchctl_server):
        """Test retrieval of audit data from PatchCtl"""
        # Set up mock response
        mock_patchctl_server['audit_responses']['QA-301-test'] = {
            "audit_hash": "test12345",
            "summary": "Test audit summary",
            "status": "completed"
        }
        
        auditor = MetaHashAuditor("http://localhost:8090")
        
        audit_hash, audit_data = await auditor._get_audit_hash("QA-301-test")
        
        assert audit_hash == "test12345"
        assert audit_data["summary"] == "Test audit summary"
        assert audit_data["status"] == "completed"
        
    @pytest.mark.asyncio
    async def test_patchctl_quorum_update(self, mock_patchctl_server):
        """Test updating PatchCtl with quorum decision"""
        auditor = MetaHashAuditor("http://localhost:8090")
        
        decision = QuorumDecision(
            pr_id="QA-301-test",
            passed=True,
            reason="hash_match",
            phi3_hash="abc12345",
            audit_hash="abc12345",
            confidence=1.0,
            timestamp=1234567890.0,
            actions_taken=[]
        )
        
        await auditor._update_patchctl_quorum(decision)
        
        assert "patchctl_updated" in decision.actions_taken

class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    def test_full_workflow_hash_match(self, temp_files):
        """Test complete workflow with matching hashes"""
        async def run_test():
            auditor = MetaHashAuditor()
            
            # Mock successful audit
            with patch.object(auditor, '_get_audit_hash') as mock_audit:
                mock_audit.return_value = ("abc12345", {"hash": "abc12345"})
                
                with patch.object(auditor, '_update_patchctl_quorum') as mock_patchctl:
                    decision = await auditor.audit_pr_hash(
                        pr_id="QA-301-test",
                        meta_file=temp_files["meta_file"]
                    )
                    
                    assert decision.passed is True
                    assert decision.reason == "hash_match"
                    mock_patchctl.assert_called_once()
                    
        asyncio.run(run_test())
        
    def test_full_workflow_hash_mismatch(self, temp_files):
        """Test complete workflow with mismatching hashes"""
        async def run_test():
            auditor = MetaHashAuditor()
            
            # Mock failing audit
            with patch.object(auditor, '_get_audit_hash') as mock_audit:
                mock_audit.return_value = ("xyz98765", {"hash": "xyz98765"})
                
                with patch.object(auditor, '_update_patchctl_quorum') as mock_patchctl:
                    decision = await auditor.audit_pr_hash(
                        pr_id="QA-301-test",
                        meta_file=temp_files["meta_file"]
                    )
                    
                    assert decision.passed is False
                    assert decision.reason == "hash_mismatch"
                    mock_patchctl.assert_called_once()
                    
        asyncio.run(run_test())
        
    def test_cli_integration(self, temp_files):
        """Test CLI integration"""
        from tools.meta_hash_audit import MetaHashAuditCLI
        
        async def run_test():
            cli = MetaHashAuditCLI()
            
            # Mock PatchCtl to avoid external dependency
            with patch.object(cli.auditor, '_update_patchctl_quorum'):
                decision = await cli.run_audit(
                    pr_id="QA-301-test",
                    meta_file=temp_files["meta_file"],
                    audit_log=temp_files["audit_log_match"]
                )
                
                assert decision.pr_id == "QA-301-test"
                assert decision.passed is True
                
        asyncio.run(run_test())

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_missing_files(self):
        """Test behavior with missing files"""
        async def run_test():
            auditor = MetaHashAuditor()
            
            decision = await auditor.audit_pr_hash(
                pr_id="QA-301-test",
                meta_file="/nonexistent/meta.yaml",
                audit_log="/nonexistent/audit.log"
            )
            
            # Should still produce a decision with fallback hashes
            assert decision.pr_id == "QA-301-test"
            assert len(decision.phi3_hash) == 8
            assert len(decision.audit_hash) == 8
            
        asyncio.run(run_test())
        
    def test_invalid_yaml_files(self, temp_files):
        """Test behavior with invalid YAML files"""
        
        # Create invalid YAML file
        invalid_yaml = os.path.join(temp_files["temp_dir"], "invalid.yaml")
        with open(invalid_yaml, 'w') as f:
            f.write("invalid: yaml: content: [")
            
        async def run_test():
            auditor = MetaHashAuditor()
            
            # Should handle gracefully and generate fallback
            audit_data = await auditor._parse_audit_log(invalid_yaml)
            assert "error" in audit_data
            
        asyncio.run(run_test())
        
    def test_network_failures(self):
        """Test behavior with network failures"""
        async def run_test():
            auditor = MetaHashAuditor("http://nonexistent:9999")
            
            # Should fall back gracefully
            audit_hash, audit_data = await auditor._get_audit_hash("QA-301-test")
            
            assert len(audit_hash) == 8
            assert audit_data["source"] == "fallback"
            
        asyncio.run(run_test())

# Test fixtures cleanup
@pytest.fixture(autouse=True)
def cleanup_temp_files(temp_files):
    """Clean up temporary files after tests"""
    yield
    
    import shutil
    if os.path.exists(temp_files["temp_dir"]):
        shutil.rmtree(temp_files["temp_dir"])

if __name__ == "__main__":
    pytest.main([__file__, "-v"])