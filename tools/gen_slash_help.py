#!/usr/bin/env python3
"""
tools/gen_slash_help.py

Scan the Slack router's slash-command registry and emit a Markdown table
suitable for posting as the `/help` response.

🚦 FREEZE-SAFE: Reads code, writes stdout/files only. No runtime impact.
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, Callable, Any
import traceback

def safe_print(message: str):
    """Print message with Windows encoding fallback."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace emoji and special characters for Windows
        safe_message = (message
                       .replace('🔍', '[SEARCH]')
                       .replace('📋', '[LIST]') 
                       .replace('📝', '[WRITE]')
                       .replace('✅', '[OK]')
                       .replace('⚠️', '[WARN]')
                       .replace('❌', '[ERROR]')
                       .replace('🎯', '[TARGET]'))
        print(safe_message)

def load_registry() -> Dict[str, Callable]:
    """
    Load the Slack command registry from the router module.
    
    Returns:
        Dict mapping command names to handler functions
    """
    try:
        # Try to load from slack_router.commands module
        mod = importlib.import_module("slack_router.commands")
        registry = getattr(mod, "COMMAND_REGISTRY", {})
        if registry:
            return registry
    except ImportError:
        pass
    
    try:
        # Fallback: try app.slack.commands
        mod = importlib.import_module("app.slack.commands")
        registry = getattr(mod, "COMMAND_REGISTRY", {})
        if registry:
            return registry
    except ImportError:
        pass
    
    try:
        # Fallback: try app.routers.slack
        mod = importlib.import_module("app.routers.slack")
        registry = getattr(mod, "COMMANDS", {})
        if registry:
            return registry
    except ImportError:
        pass
    
    # If no registry found, create a mock one for demonstration
    safe_print("⚠️  No slash command registry found, using mock data")
    return {
        "help": lambda: "Show available commands",
        "status": lambda: "Show system status", 
        "audit": lambda: "Trigger audit process",
        "deploy": lambda: "Deploy latest changes",
        "rollback": lambda: "Rollback to previous version",
        "logs": lambda: "Fetch recent logs",
        "health": lambda: "Check service health",
        "config": lambda: "Show configuration",
        "restart": lambda: "Restart services",
        "scale": lambda: "Scale services up/down"
    }

def extract_description(func: Callable) -> str:
    """
    Extract a description from a function's docstring or name.
    
    Args:
        func: The handler function
        
    Returns:
        Human-readable description
    """
    if func is None:
        return "—"
    
    # Try to get docstring
    doc = inspect.getdoc(func)
    if doc:
        # Use first line of docstring
        return doc.splitlines()[0].strip()
    
    # Fallback to function name processing
    name = getattr(func, '__name__', str(func))
    if name == '<lambda>':
        # For lambda functions, try to get a description from the code
        try:
            source = inspect.getsource(func).strip()
            if ':' in source and 'return' in source:
                # Extract return value if it's a simple string
                parts = source.split('return')[-1].strip().strip('"\'')
                if len(parts) < 100:  # Reasonable description length
                    return parts
        except:
            pass
        return "Lambda function"
    
    # Convert function name to readable description
    readable = name.replace('_', ' ').replace('handle', '').strip()
    return readable.capitalize() if readable else "—"

def generate_help_markdown(registry: Dict[str, Callable]) -> str:
    """
    Generate markdown table from command registry.
    
    Args:
        registry: Dict mapping command names to handlers
        
    Returns:
        Markdown table as string
    """
    if not registry:
        return "# Slash Commands\n\nNo commands registered.\n"
    
    # Header
    rows = [
        "# Slash Commands",
        "",
        "Available commands for the AutoGen Council Slack integration:",
        "",
        "| Command | Description |",
        "|---------|-------------|"
    ]
    
    # Sort commands alphabetically
    for name in sorted(registry.keys()):
        func = registry[name]
        description = extract_description(func)
        
        # Escape any markdown characters in description
        description = description.replace('|', '\\|').replace('\n', ' ')
        
        # Limit description length for table readability
        if len(description) > 80:
            description = description[:77] + "..."
        
        rows.append(f"| `/{name}` | {description} |")
    
    # Footer
    rows.extend([
        "",
        "---",
        "",
        "*Generated automatically by `tools/gen_slash_help.py`*",
        f"*Last updated: {Path(__file__).stat().st_mtime}*",
        ""
    ])
    
    return "\n".join(rows)

def main():
    """Main entry point for the help generator."""
    safe_print("🔍 Scanning Slack command registry...")
    
    try:
        # Load command registry
        registry = load_registry()
        safe_print(f"📋 Found {len(registry)} registered commands")
        
        # Generate markdown
        markdown = generate_help_markdown(registry)
        
        # Write to stdout
        safe_print("📝 Generated markdown:")
        safe_print("=" * 50)
        safe_print(markdown)
        safe_print("=" * 50)
        
        # Write to file
        output_path = Path("SLASH_HELP.md")
        output_path.write_text(markdown, encoding='utf-8')
        safe_print(f"✅ Wrote {output_path.absolute()}")
        
        # Also generate a JSON version for programmatic access
        import json
        json_data = {
            "commands": {
                name: extract_description(func) 
                for name, func in registry.items()
            },
            "generated_at": str(Path(__file__).stat().st_mtime),
            "total_commands": len(registry)
        }
        
        json_path = Path("SLASH_HELP.json")
        json_path.write_text(json.dumps(json_data, indent=2), encoding='utf-8')
        safe_print(f"✅ Wrote {json_path.absolute()}")
        
        safe_print(f"🎯 Help generation complete! Found {len(registry)} commands.")
        
    except Exception as e:
        safe_print(f"❌ Error generating help: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 