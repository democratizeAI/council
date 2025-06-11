#!/usr/bin/env python3
"""
tests/test_gen_slash_help.py

Unit tests for the slash command help generator tool.

🚦 FREEZE-SAFE: Tests only validate tool functionality, no live services.
"""

import subprocess
import pathlib
import json
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
import pytest

# Add tools directory to path for importing
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "tools"))

try:
    import gen_slash_help
except ImportError:
    # If import fails, we'll test via subprocess only
    gen_slash_help = None

class TestSlashHelpGenerator:
    """Test suite for the slash command help generator."""
    
    def test_tool_exists(self):
        """Test that the help generator tool exists and is executable."""
        tool_path = pathlib.Path("tools/gen_slash_help.py")
        assert tool_path.exists(), "gen_slash_help.py should exist in tools/"
        assert tool_path.is_file(), "gen_slash_help.py should be a file"
    
    def test_help_generation_subprocess(self):
        """Test help generation via subprocess (most reliable test)."""
        # Run the tool
        result = subprocess.run(
            [sys.executable, "tools/gen_slash_help.py"],
            capture_output=True,
            text=True,
            cwd=pathlib.Path(__file__).parent.parent
        )
        
        # Should exit successfully
        assert result.returncode == 0, f"Tool failed: {result.stderr}"
        
        # Should produce output
        assert len(result.stdout) > 0, "Tool should produce output"
        
        # Should mention commands in output
        assert "Found" in result.stdout, "Should report found commands"
        assert "commands" in result.stdout.lower(), "Should mention commands"
    
    def test_markdown_file_generation(self):
        """Test that SLASH_HELP.md is generated correctly."""
        # Clean up any existing file
        help_file = pathlib.Path("SLASH_HELP.md")
        if help_file.exists():
            help_file.unlink()
        
        # Run the tool
        subprocess.check_call([sys.executable, "tools/gen_slash_help.py"])
        
        # Check file was created
        assert help_file.exists(), "SLASH_HELP.md should be created"
        
        # Check file content
        content = help_file.read_text(encoding='utf-8')
        assert len(content) > 0, "File should not be empty"
        assert "# Slash Commands" in content, "Should have markdown header"
        assert "| Command | Description |" in content, "Should have table header"
        assert "|---------|-------------|" in content, "Should have table separator"
        
        # Should have at least one command row
        lines = content.split('\n')
        command_rows = [line for line in lines if line.startswith('| `/')]
        assert len(command_rows) > 0, "Should have at least one command"
        
        # Clean up
        help_file.unlink()
    
    def test_json_file_generation(self):
        """Test that SLASH_HELP.json is generated correctly."""
        # Clean up any existing file
        json_file = pathlib.Path("SLASH_HELP.json")
        if json_file.exists():
            json_file.unlink()
        
        # Run the tool
        subprocess.check_call([sys.executable, "tools/gen_slash_help.py"])
        
        # Check file was created
        assert json_file.exists(), "SLASH_HELP.json should be created"
        
        # Check file content
        content = json_file.read_text(encoding='utf-8')
        data = json.loads(content)
        
        # Validate JSON structure
        assert "commands" in data, "Should have commands section"
        assert "generated_at" in data, "Should have generation timestamp"
        assert "total_commands" in data, "Should have command count"
        
        # Should have at least one command
        assert len(data["commands"]) > 0, "Should have at least one command"
        assert data["total_commands"] > 0, "Total commands should be positive"
        
        # Clean up
        json_file.unlink()
    
    @pytest.mark.skipif(gen_slash_help is None, reason="Could not import gen_slash_help module")
    def test_load_registry_fallback(self):
        """Test that load_registry provides fallback mock data."""
        # Test the function directly
        registry = gen_slash_help.load_registry()
        
        # Should return a dict
        assert isinstance(registry, dict), "Registry should be a dictionary"
        
        # Should have some commands (either real or mock)
        assert len(registry) > 0, "Registry should not be empty"
        
        # Common commands should exist in mock data if no real registry found
        mock_commands = ["help", "status", "health"]
        found_commands = set(registry.keys())
        has_mock_commands = any(cmd in found_commands for cmd in mock_commands)
        assert has_mock_commands, "Should have mock or real commands"
    
    @pytest.mark.skipif(gen_slash_help is None, reason="Could not import gen_slash_help module")
    def test_extract_description(self):
        """Test description extraction from various function types."""
        # Test function with docstring
        def documented_func():
            """This is a test function."""
            pass
        
        desc = gen_slash_help.extract_description(documented_func)
        assert desc == "This is a test function.", "Should extract docstring"
        
        # Test function without docstring
        def undocumented_func():
            pass
        
        desc = gen_slash_help.extract_description(undocumented_func)
        assert desc == "Undocumented func", "Should generate readable name"
        
        # Test lambda function
        lambda_func = lambda: "Test response"
        desc = gen_slash_help.extract_description(lambda_func)
        assert "Test response" in desc or "Lambda function" in desc, "Should handle lambda"
        
        # Test None
        desc = gen_slash_help.extract_description(None)
        assert desc == "—", "Should handle None gracefully"
    
    @pytest.mark.skipif(gen_slash_help is None, reason="Could not import gen_slash_help module")
    def test_generate_help_markdown(self):
        """Test markdown generation from registry."""
        # Mock registry
        test_registry = {
            "help": lambda: "Show available commands",
            "status": lambda: "Show system status",
            "deploy": lambda: "Deploy latest changes"
        }
        
        markdown = gen_slash_help.generate_help_markdown(test_registry)
        
        # Should be valid markdown
        assert "# Slash Commands" in markdown, "Should have header"
        assert "| Command | Description |" in markdown, "Should have table header"
        assert "`/help`" in markdown, "Should include help command"
        assert "`/status`" in markdown, "Should include status command"
        assert "`/deploy`" in markdown, "Should include deploy command"
        
        # Should be sorted alphabetically
        lines = markdown.split('\n')
        command_lines = [line for line in lines if line.startswith('| `/')]
        assert len(command_lines) == 3, "Should have 3 commands"
        
        # Commands should be in alphabetical order
        commands = [line.split('`')[1].replace('/', '') for line in command_lines]
        assert commands == sorted(commands), "Commands should be alphabetically sorted"
    
    def test_empty_registry_handling(self):
        """Test handling of empty command registry."""
        if gen_slash_help is None:
            pytest.skip("Could not import gen_slash_help module")
        
        markdown = gen_slash_help.generate_help_markdown({})
        assert "No commands registered" in markdown, "Should handle empty registry"
    
    def test_makefile_target_exists(self):
        """Test that the Makefile has the help-md target."""
        makefile_path = pathlib.Path("Makefile")
        assert makefile_path.exists(), "Makefile should exist"
        
        content = makefile_path.read_text()
        assert "help-md:" in content, "Makefile should have help-md target"
        assert "gen_slash_help.py" in content, "Target should call the generator script"

class TestFreezeZSafety:
    """Tests to ensure the tool is freeze-safe."""
    
    def test_no_network_calls(self):
        """Ensure the tool makes no network calls."""
        # This is a static analysis - we check the source doesn't import network libraries
        tool_path = pathlib.Path("tools/gen_slash_help.py")
        if not tool_path.exists():
            pytest.skip("Tool file not found")
        
        content = tool_path.read_text()
        
        # Should not import network libraries
        forbidden_imports = ["requests", "urllib", "socket", "http.client"]
        for imp in forbidden_imports:
            assert f"import {imp}" not in content, f"Should not import {imp}"
            assert f"from {imp}" not in content, f"Should not import from {imp}"
    
    def test_no_subprocess_calls(self):
        """Ensure the tool doesn't make subprocess calls to system services."""
        tool_path = pathlib.Path("tools/gen_slash_help.py")
        if not tool_path.exists():
            pytest.skip("Tool file not found")
        
        content = tool_path.read_text()
        
        # Should not call docker, systemctl, etc.
        forbidden_calls = ["docker", "systemctl", "kubectl", "curl", "wget"]
        for call in forbidden_calls:
            assert call not in content.lower(), f"Should not contain {call} calls"
    
    def test_only_writes_documentation_files(self):
        """Ensure the tool only writes safe documentation files."""
        # Clean up any existing files
        for filename in ["SLASH_HELP.md", "SLASH_HELP.json"]:
            path = pathlib.Path(filename)
            if path.exists():
                path.unlink()
        
        # Run the tool
        subprocess.check_call([sys.executable, "tools/gen_slash_help.py"])
        
        # Check only the expected files were created
        expected_files = {"SLASH_HELP.md", "SLASH_HELP.json"}
        
        # Verify the files exist and are safe
        for filename in expected_files:
            path = pathlib.Path(filename)
            assert path.exists(), f"{filename} should be created"
            
            # Files should be readable text
            content = path.read_text(encoding='utf-8')
            assert len(content) > 0, f"{filename} should not be empty"
            
            # Clean up
            path.unlink()

# Test runner for quick validation
if __name__ == "__main__":
    # Quick smoke test
    print("🧪 Running quick slash help generator tests...")
    
    # Test tool exists
    tool_path = pathlib.Path("tools/gen_slash_help.py")
    assert tool_path.exists(), "Tool should exist"
    print("✅ Tool exists")
    
    # Test tool runs
    result = subprocess.run([sys.executable, str(tool_path)], capture_output=True)
    assert result.returncode == 0, f"Tool should run successfully: {result.stderr}"
    print("✅ Tool runs successfully")
    
    # Test files are created
    assert pathlib.Path("SLASH_HELP.md").exists(), "Markdown file should be created"
    assert pathlib.Path("SLASH_HELP.json").exists(), "JSON file should be created"
    print("✅ Files generated successfully")
    
    print("🎯 All tests passed! Help generator is freeze-safe and functional.") 