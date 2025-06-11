#!/usr/bin/env python3
"""
tests/test_release_note.py

Unit tests for the release note generator script.

🚦 FREEZE-SAFE: Tests only validate tool functionality, no live services.
"""

import subprocess
import pathlib
import json
import re
import sys
from unittest.mock import patch, MagicMock
import pytest

# Add scripts directory to path for importing
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

try:
    import make_release_note
except ImportError:
    # If import fails, we'll test via subprocess only
    make_release_note = None

class TestReleaseNoteGenerator:
    """Test suite for the release note generator."""
    
    def test_script_exists(self):
        """Test that the release note generator exists and is executable."""
        script_path = pathlib.Path("scripts/make_release_note.py")
        assert script_path.exists(), "make_release_note.py should exist in scripts/"
        assert script_path.is_file(), "make_release_note.py should be a file"
    
    def test_release_note_generation_subprocess(self):
        """Test release note generation via subprocess (most reliable test)."""
        # Clean up any existing files
        for filename in ["RELEASE_NOTES.md", "RELEASE_SUMMARY.json"]:
            path = pathlib.Path(filename)
            if path.exists():
                path.unlink()
        
        # Run the script
        result = subprocess.run(
            [sys.executable, "scripts/make_release_note.py"],
            capture_output=True,
            text=True,
            cwd=pathlib.Path(__file__).parent.parent,
            timeout=30
        )
        
        # Should exit successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        
        # Should produce output
        assert len(result.stdout) > 0, "Script should produce output"
        assert "Generating release notes" in result.stdout, "Should mention release notes"
    
    def test_markdown_file_generation(self):
        """Test that RELEASE_NOTES.md is generated correctly."""
        # Clean up any existing file
        release_file = pathlib.Path("RELEASE_NOTES.md")
        if release_file.exists():
            release_file.unlink()
        
        # Run the script
        subprocess.check_call([sys.executable, "scripts/make_release_note.py"])
        
        # Check file was created
        assert release_file.exists(), "RELEASE_NOTES.md should be created"
        
        # Check file content with UTF-8 encoding
        content = release_file.read_text(encoding='utf-8')
        assert len(content) > 0, "File should not be empty"
        
        # Should have proper structure
        assert re.search(r"^# v\d+\.\d+", content), "Should have version header"
        assert "Release Notes" in content, "Should mention release notes"
        assert "Generated" in content, "Should have generation timestamp"
        assert "## " in content, "Should have markdown sections"
        
        # Should have key sections
        assert "Executive Summary" in content, "Should have executive summary"
        assert "Performance Metrics" in content, "Should have metrics section"
        assert "Installation" in content, "Should have installation instructions"
        
        # Clean up
        release_file.unlink()
    
    def test_json_summary_generation(self):
        """Test that RELEASE_SUMMARY.json is generated correctly."""
        # Clean up any existing file
        json_file = pathlib.Path("RELEASE_SUMMARY.json")
        if json_file.exists():
            json_file.unlink()
        
        # Run the script
        subprocess.check_call([sys.executable, "scripts/make_release_note.py"])
        
        # Check file was created
        assert json_file.exists(), "RELEASE_SUMMARY.json should be created"
        
        # Check file content with UTF-8 encoding
        content = json_file.read_text(encoding='utf-8')
        data = json.loads(content)
        
        # Validate JSON structure
        assert "version" in data, "Should have version field"
        assert "generated_at" in data, "Should have generation timestamp"
        assert "git_stats" in data, "Should have git statistics"
        assert "line_count" in data, "Should have line count"
        assert "file_size" in data, "Should have file size"
        
        # Should have reasonable values
        assert len(data["version"]) > 0, "Version should not be empty"
        assert data["line_count"] > 10, "Should have substantial content"
        assert data["file_size"] > 1000, "Should have reasonable file size"
        
        # Clean up
        json_file.unlink()
    
    @pytest.mark.skipif(make_release_note is None, reason="Could not import make_release_note module")
    def test_export_ledger_fallbacks(self):
        """Test that export_ledger provides fallback data."""
        # Test the function directly
        ledger_content = make_release_note.export_ledger()
        
        # Should return a string
        assert isinstance(ledger_content, str), "Ledger export should return string"
        
        # Should have some content
        assert len(ledger_content) > 0, "Ledger export should not be empty"
        
        # Should contain relevant keywords
        keywords = ["achievement", "performance", "enterprise", "audit", "governance"]
        content_lower = ledger_content.lower()
        found_keywords = [kw for kw in keywords if kw in content_lower]
        assert len(found_keywords) > 0, f"Should contain relevant keywords, found: {found_keywords}"
    
    @pytest.mark.skipif(make_release_note is None, reason="Could not import make_release_note module")
    def test_extract_version(self):
        """Test version extraction functionality."""
        version = make_release_note.extract_version()
        
        # Should return a string
        assert isinstance(version, str), "Version should be a string"
        
        # Should look like a version
        assert len(version) > 0, "Version should not be empty"
        assert "v" in version.lower() or "." in version, "Version should look like a version string"
    
    @pytest.mark.skipif(make_release_note is None, reason="Could not import make_release_note module")
    def test_get_git_stats(self):
        """Test git statistics gathering."""
        stats = make_release_note.get_git_stats()
        
        # Should return a dict
        assert isinstance(stats, dict), "Git stats should be a dictionary"
        
        # Should have expected keys
        expected_keys = ["total_commits", "latest_commit", "branch"]
        for key in expected_keys:
            assert key in stats, f"Should have {key} in git stats"
        
        # Values should be strings
        for key, value in stats.items():
            assert isinstance(value, str), f"Git stat {key} should be a string"
    
    @pytest.mark.skipif(make_release_note is None, reason="Could not import make_release_note module")
    def test_build_release_notes(self):
        """Test release notes building from ledger content."""
        # Mock ledger content
        mock_ledger = "## Test Section\n- Feature A implemented\n- Bug B fixed"
        
        release_notes = make_release_note.build_release_notes(mock_ledger)
        
        # Should return a string
        assert isinstance(release_notes, str), "Release notes should be a string"
        
        # Should contain the input ledger content
        assert mock_ledger in release_notes, "Should include original ledger content"
        
        # Should have added structure
        assert "# v" in release_notes, "Should have version header"
        assert "## " in release_notes, "Should have markdown sections"
        assert "Generated" in release_notes, "Should have generation info"
        
        # Should have multiple sections
        sections = [line for line in release_notes.split('\n') if line.startswith('## ')]
        assert len(sections) >= 5, f"Should have multiple sections, found {len(sections)}"
    
    def test_makefile_target_exists(self):
        """Test that the Makefile has the release-note target."""
        makefile_path = pathlib.Path("Makefile")
        assert makefile_path.exists(), "Makefile should exist"
        
        content = makefile_path.read_text(encoding='utf-8')
        assert "release-note:" in content, "Makefile should have release-note target"
        assert "make_release_note.py" in content, "Target should call the generator script"

class TestFreezeSafety:
    """Tests to ensure the release note generator is freeze-safe."""
    
    def test_no_network_calls(self):
        """Ensure the script makes no network calls."""
        script_path = pathlib.Path("scripts/make_release_note.py")
        if not script_path.exists():
            pytest.skip("Script file not found")
        
        content = script_path.read_text(encoding='utf-8')
        
        # Should not import network libraries
        forbidden_imports = ["requests", "urllib", "socket", "http.client"]
        for imp in forbidden_imports:
            assert f"import {imp}" not in content, f"Should not import {imp}"
            assert f"from {imp}" not in content, f"Should not import from {imp}"
    
    def test_no_dangerous_subprocess_calls(self):
        """Ensure the script doesn't make dangerous subprocess calls."""
        script_path = pathlib.Path("scripts/make_release_note.py")
        if not script_path.exists():
            pytest.skip("Script file not found")
        
        content = script_path.read_text(encoding='utf-8')
        
        # Check for actual subprocess calls, not documentation strings
        # Look for subprocess.run patterns with dangerous commands
        import re
        subprocess_calls = re.findall(r'subprocess\.(?:run|call|check_call|check_output)\s*\(\s*\[?["\']([^"\']+)', content)
        
        dangerous_commands = ["rm", "sudo", "docker", "systemctl", "service", "shutdown", "reboot"]
        for call in subprocess_calls:
            first_word = call.split()[0] if call.split() else ""
            assert first_word not in dangerous_commands, f"Dangerous subprocess call found: {call}"
    
    def test_only_writes_documentation_files(self):
        """Ensure the script only writes safe documentation files."""
        # Clean up any existing files
        for filename in ["RELEASE_NOTES.md", "RELEASE_SUMMARY.json"]:
            path = pathlib.Path(filename)
            if path.exists():
                path.unlink()
        
        # Run the script
        subprocess.check_call([sys.executable, "scripts/make_release_note.py"])
        
        # Check only the expected files were created
        expected_files = {"RELEASE_NOTES.md", "RELEASE_SUMMARY.json"}
        
        # Verify the files exist and are safe
        for filename in expected_files:
            path = pathlib.Path(filename)
            assert path.exists(), f"{filename} should be created"
            
            # Files should be readable text with UTF-8 encoding
            content = path.read_text(encoding='utf-8')
            assert len(content) > 0, f"{filename} should not be empty"
            
            # Clean up
            path.unlink()
    
    def test_git_commands_are_safe(self):
        """Ensure git commands used are read-only and safe."""
        script_path = pathlib.Path("scripts/make_release_note.py")
        if not script_path.exists():
            pytest.skip("Script file not found")
        
        content = script_path.read_text(encoding='utf-8')
        
        # Check that no dangerous git operations are used
        dangerous_git_ops = ["git push", "git commit", "git merge", "git rebase", "git reset", "git rm", "git add"]
        for dangerous_op in dangerous_git_ops:
            assert dangerous_op not in content, f"Script should not contain dangerous git operation: {dangerous_op}"
        
        # Verify script only uses safe read-only git commands in subprocess calls
        # Look for patterns like ["git", "describe", ...] in subprocess calls
        safe_git_subcommands = ["describe", "rev-list", "rev-parse", "branch", "log", "show", "status"]
        
        # This is a positive test - if git is used in subprocess, it should be for safe operations
        if "subprocess.run" in content and "[\"git\"" in content:
            # Check if any safe git subcommands are found in the subprocess context
            found_safe_op = False
            for safe_cmd in safe_git_subcommands:
                # Look for patterns like ["git", "describe"] or ['git', 'describe']
                if f'["git", "{safe_cmd}"' in content or f"['git', '{safe_cmd}']" in content:
                    found_safe_op = True
                    break
            
            assert found_safe_op, f"Script uses git in subprocess but no safe git operations found. Expected one of: {safe_git_subcommands}"

class TestReleaseNoteContent:
    """Tests for the content and structure of generated release notes."""
    
    def test_version_header_format(self):
        """Test that version header follows expected format."""
        # Run the script
        subprocess.check_call([sys.executable, "scripts/make_release_note.py"])
        
        # Check version header with UTF-8 encoding
        content = pathlib.Path("RELEASE_NOTES.md").read_text(encoding='utf-8')
        lines = content.split('\n')
        header = lines[0]
        
        # Should match version pattern
        assert re.match(r"^# v\d+\.\d+", header), f"Header should match version pattern: {header}"
        assert "Release Notes" in header, "Header should mention release notes"
        
        # Clean up
        pathlib.Path("RELEASE_NOTES.md").unlink()
        pathlib.Path("RELEASE_SUMMARY.json").unlink()
    
    def test_required_sections_present(self):
        """Test that all required sections are present."""
        # Run the script
        subprocess.check_call([sys.executable, "scripts/make_release_note.py"])
        
        content = pathlib.Path("RELEASE_NOTES.md").read_text(encoding='utf-8')
        
        # Required sections (with emoji support)
        required_sections = [
            "Executive Summary",
            "Performance Metrics", 
            "Detailed Changes",
            "Technical Achievements",
            "Installation",
            "Security Updates",
            "What's Next"
        ]
        
        for section in required_sections:
            # Check for both plain and emoji-prefixed headers
            plain_header = f"## {section}"
            emoji_header = f"## 🎯 {section}"
            metrics_header = f"## 📊 {section}"
            changes_header = f"## 📋 {section}"
            tech_header = f"## 🏆 {section}"
            install_header = f"## 🚀 {section}"
            security_header = f"## 🛡️ {section}"
            next_header = f"## 🛣️ {section}"
            
            has_section = any([
                plain_header in content,
                emoji_header in content,
                metrics_header in content,
                changes_header in content,
                tech_header in content,
                install_header in content,
                security_header in content,
                next_header in content,
                section in content  # Fallback to just the section name
            ])
            
            assert has_section, f"Should have {section} section"
        
        # Clean up
        pathlib.Path("RELEASE_NOTES.md").unlink()
        pathlib.Path("RELEASE_SUMMARY.json").unlink()

# Test runner for quick validation
if __name__ == "__main__":
    # Quick smoke test
    print("🧪 Running quick release note generator tests...")
    
    # Test script exists
    script_path = pathlib.Path("scripts/make_release_note.py")
    assert script_path.exists(), "Script should exist"
    print("✅ Script exists")
    
    # Test script runs
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True)
    assert result.returncode == 0, f"Script should run successfully: {result.stderr}"
    print("✅ Script runs successfully")
    
    # Test files are created
    assert pathlib.Path("RELEASE_NOTES.md").exists(), "Release notes should be created"
    assert pathlib.Path("RELEASE_SUMMARY.json").exists(), "Release summary should be created"
    print("✅ Files generated successfully")
    
    # Test version header format with UTF-8 encoding
    content = pathlib.Path("RELEASE_NOTES.md").read_text(encoding='utf-8')
    assert re.search(r"^# v\d+\.\d+", content), "Should have proper version header"
    print("✅ Version header format correct")
    
    print("🎯 All tests passed! Release note generator is freeze-safe and functional.") 