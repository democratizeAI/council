import pytest
import pathlib
import re
from typing import List

# Patterns to detect stub/placeholder text
BAD_PATTERNS = [
    re.compile(r"hello! i'm your autogen council assistant", re.I),
    re.compile(r"\[your role here\]", re.I),
    re.compile(r"\[placeholder\]", re.I),
    re.compile(r"lorem ipsum", re.I),
    re.compile(r"todo:", re.I),
    re.compile(r"fixme:", re.I),
    re.compile(r"xxx:", re.I),
    re.compile(r"placeholder text", re.I),
    re.compile(r"sample response", re.I),
    re.compile(r"example output", re.I),
    re.compile(r"<fill this in>", re.I),
    re.compile(r"<replace with>", re.I),
    re.compile(r"\{\{.*\}\}", re.I),  # Template variables like {{name}}
    re.compile(r"autogen.*assistant", re.I),  # Any autogen assistant references
    re.compile(r"microsoft.*research", re.I),  # Default Microsoft Research attribution
    re.compile(r"this is a template", re.I),
    re.compile(r"modify this prompt", re.I),
]

# Acceptable patterns that might look like stubs but are actually valid
ACCEPTABLE_PATTERNS = [
    re.compile(r"user:", re.I),  # Chat format
    re.compile(r"assistant:", re.I),  # Chat format  
    re.compile(r"system:", re.I),  # Chat format
    re.compile(r"role.*specialist", re.I),  # Specialist role descriptions
    re.compile(r"council.*voice", re.I),  # Council voice descriptions
]

def find_prompt_files() -> List[pathlib.Path]:
    """Find all prompt files in the repository"""
    prompt_dirs = [
        pathlib.Path("prompts"),
        pathlib.Path("config"),
        pathlib.Path("router"),
        pathlib.Path("app"),
    ]
    
    prompt_files = []
    
    for prompt_dir in prompt_dirs:
        if prompt_dir.exists():
            # Look for markdown, txt, and yaml files
            for pattern in ["*.md", "*.txt", "*.yaml", "*.yml"]:
                prompt_files.extend(prompt_dir.rglob(pattern))
    
    return prompt_files

def is_acceptable_match(text: str, match_obj: re.Match) -> bool:
    """Check if a match is acceptable (not actually a stub)"""
    matched_text = match_obj.group(0)
    
    for acceptable_pattern in ACCEPTABLE_PATTERNS:
        if acceptable_pattern.search(matched_text):
            return True
    
    return False

def test_no_stub_left():
    """Test that no stub/placeholder text remains in prompt files"""
    prompt_files = find_prompt_files()
    
    if not prompt_files:
        pytest.skip("No prompt files found")
    
    violations = []
    
    for prompt_file in prompt_files:
        try:
            content = prompt_file.read_text(encoding='utf-8')
            
            for pattern in BAD_PATTERNS:
                matches = list(pattern.finditer(content))
                for match in matches:
                    if not is_acceptable_match(content, match):
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append({
                            'file': str(prompt_file),
                            'line': line_num,
                            'match': match.group(0),
                            'pattern': pattern.pattern
                        })
        
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                content = prompt_file.read_text(encoding='cp1252')
                # ... repeat the check with this content
            except Exception as e:
                violations.append({
                    'file': str(prompt_file),
                    'line': 0,
                    'match': f"Encoding error: {e}",
                    'pattern': 'encoding'
                })
        except Exception as e:
            violations.append({
                'file': str(prompt_file),
                'line': 0,
                'match': f"Read error: {e}",
                'pattern': 'file_access'
            })
    
    if violations:
        error_msg = "Found stub/placeholder text in prompt files:\n"
        for violation in violations:
            error_msg += f"  {violation['file']}:{violation['line']} - '{violation['match']}' (pattern: {violation['pattern']})\n"
        
        pytest.fail(error_msg)

def test_prompt_files_exist():
    """Test that we have some prompt files to check"""
    prompt_files = find_prompt_files()
    assert len(prompt_files) > 0, "No prompt files found to test"

def test_council_voice_prompts():
    """Test that council voice prompts are properly defined"""
    prompt_files = find_prompt_files()
    
    # Look for council-related prompts
    council_files = [f for f in prompt_files if 'council' in str(f).lower() or 'voice' in str(f).lower()]
    
    if not council_files:
        pytest.skip("No council prompt files found")
    
    voice_types = ["reason", "knowledge", "logic", "creativity", "critique"]
    found_voices = set()
    
    for prompt_file in council_files:
        try:
            content = prompt_file.read_text(encoding='utf-8').lower()
            
            for voice_type in voice_types:
                if voice_type in content:
                    found_voices.add(voice_type)
        
        except Exception:
            continue  # Skip files we can't read
    
    # Should have at least some voice types defined
    assert len(found_voices) >= 2, f"Expected at least 2 voice types, found: {found_voices}"

def test_specific_prompt_quality():
    """Test specific prompt files for quality indicators"""
    prompt_files = find_prompt_files()
    
    quality_indicators = [
        "context",
        "role",
        "task",
        "format",
        "output",
        "example",
        "instruction"
    ]
    
    substantial_prompts = []
    
    for prompt_file in prompt_files:
        try:
            content = prompt_file.read_text(encoding='utf-8')
            
            # Skip very short files (< 100 chars)
            if len(content) < 100:
                continue
            
            content_lower = content.lower()
            
            # Count quality indicators
            indicator_count = sum(1 for indicator in quality_indicators if indicator in content_lower)
            
            if indicator_count >= 2:  # At least 2 quality indicators
                substantial_prompts.append({
                    'file': str(prompt_file),
                    'length': len(content),
                    'indicators': indicator_count
                })
        
        except Exception:
            continue
    
    # Should have at least some substantial prompts
    assert len(substantial_prompts) >= 1, "No substantial prompt files found with quality indicators"

def test_no_hardcoded_api_keys():
    """Test that no API keys are hardcoded in prompt files"""
    prompt_files = find_prompt_files()
    
    api_key_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{48}", re.I),  # OpenAI API key pattern
        re.compile(r"[a-zA-Z0-9]{32}", re.I),     # Generic 32-char key (loose)
        re.compile(r"api[_-]?key\s*[=:]\s*['\"][^'\"]{10,}['\"]", re.I),
        re.compile(r"secret\s*[=:]\s*['\"][^'\"]{10,}['\"]", re.I),
        re.compile(r"token\s*[=:]\s*['\"][^'\"]{10,}['\"]", re.I),
    ]
    
    violations = []
    
    for prompt_file in prompt_files:
        try:
            content = prompt_file.read_text(encoding='utf-8')
            
            for pattern in api_key_patterns:
                matches = list(pattern.finditer(content))
                for match in matches:
                    # Skip obvious test/demo keys
                    matched_text = match.group(0).lower()
                    if any(word in matched_text for word in ['demo', 'test', 'example', 'placeholder', 'your-key']):
                        continue
                    
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(prompt_file),
                        'line': line_num,
                        'match': match.group(0)[:20] + "...",  # Truncate for security
                    })
        
        except Exception:
            continue
    
    if violations:
        error_msg = "Found potential hardcoded API keys:\n"
        for violation in violations:
            error_msg += f"  {violation['file']}:{violation['line']} - {violation['match']}\n"
        
        pytest.fail(error_msg)

def test_prompt_formatting():
    """Test that prompt files have consistent formatting"""
    prompt_files = find_prompt_files()
    
    if not prompt_files:
        pytest.skip("No prompt files found")
    
    formatting_issues = []
    
    for prompt_file in prompt_files:
        try:
            content = prompt_file.read_text(encoding='utf-8')
            
            # Check for common formatting issues
            issues = []
            
            # Multiple consecutive blank lines
            if '\n\n\n\n' in content:
                issues.append("Multiple consecutive blank lines")
            
            # Trailing whitespace (but only flag if significant)
            lines = content.split('\n')
            trailing_whitespace_lines = [i for i, line in enumerate(lines) if line.endswith(' ') or line.endswith('\t')]
            if len(trailing_whitespace_lines) > len(lines) * 0.1:  # More than 10% of lines
                issues.append("Excessive trailing whitespace")
            
            # Very long lines (>200 chars)
            long_lines = [i for i, line in enumerate(lines) if len(line) > 200]
            if len(long_lines) > 5:
                issues.append("Many very long lines")
            
            if issues:
                formatting_issues.append({
                    'file': str(prompt_file),
                    'issues': issues
                })
        
        except Exception:
            continue
    
    # Only fail if more than 50% of files have issues
    if len(formatting_issues) > len(prompt_files) * 0.5:
        error_msg = "Formatting issues found in many prompt files:\n"
        for issue in formatting_issues[:5]:  # Show first 5
            error_msg += f"  {issue['file']}: {', '.join(issue['issues'])}\n"
        
        pytest.fail(error_msg)

def test_markdown_headers():
    """Test that markdown files have proper header structure"""
    prompt_files = [f for f in find_prompt_files() if f.suffix.lower() == '.md']
    
    if not prompt_files:
        pytest.skip("No markdown prompt files found")
    
    header_issues = []
    
    for prompt_file in prompt_files:
        try:
            content = prompt_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Check for headers
            headers = [line for line in lines if line.strip().startswith('#')]
            
            if len(content) > 500 and not headers:  # Substantial file without headers
                header_issues.append(f"{prompt_file}: No headers in substantial markdown file")
            
            # Check for title (should have at least one # header)
            if headers and not any(line.strip().startswith('# ') for line in headers):
                header_issues.append(f"{prompt_file}: No top-level header found")
        
        except Exception:
            continue
    
    if header_issues:
        # Only fail if many files have issues
        if len(header_issues) > 2:
            pytest.fail("Markdown header issues:\n" + "\n".join(header_issues[:5])) 