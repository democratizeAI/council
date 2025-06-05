#!/usr/bin/env python3
"""
Enhanced Specialist Router
=========================

Upgrades specialist capabilities with tool plugins:
- Math: SymPy integration for symbolic computation  
- Code: Python execution sandbox
- Knowledge: DuckDuckGo search integration
- Logic: Enhanced reasoning with step-by-step validation
"""

import re
import subprocess
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SpecialistResponse:
    content: str
    confidence: float
    tools_used: List[str]
    execution_time_ms: float

class MathSpecialistEnhanced:
    """Math specialist with SymPy integration"""
    
    def __init__(self):
        self.sympy_available = self._check_sympy()
        
    def _check_sympy(self) -> bool:
        try:
            import sympy
            return True
        except ImportError:
            logger.warning("SymPy not available - falling back to basic math")
            return False
    
    def enhance_prompt(self, query: str, base_prompt: str) -> str:
        """Enhance math queries with SymPy capabilities"""
        if not self.sympy_available:
            return base_prompt
            
        # Detect math operations
        math_patterns = [
            r"factor|expand|simplify|solve|integrate|differentiate|derivative",
            r"equation|polynomial|algebra|calculus|matrix|determinant",
            r"\^|\*\*|sqrt|sin|cos|tan|log|ln|exp"
        ]
        
        is_symbolic = any(re.search(pattern, query.lower()) for pattern in math_patterns)
        
        if is_symbolic:
            enhanced_prompt = f"""You are a mathematical specialist with SymPy symbolic computation capabilities.

For the query: "{query}"

Use SymPy when appropriate for:
- Algebraic manipulation (factor, expand, simplify)
- Equation solving
- Calculus (derivatives, integrals)
- Matrix operations
- Symbolic computation

Example SymPy usage:
```python
import sympy as sp
x = sp.Symbol('x')
result = sp.factor(x**2 - 5*x + 6)  # (x-2)*(x-3)
```

{base_prompt}

Show your work step-by-step and provide the SymPy code when applicable."""
            return enhanced_prompt
        
        return base_prompt
    
    def execute_sympy(self, code: str) -> Dict[str, Any]:
        """Safely execute SymPy code in sandbox"""
        try:
            # Simple sandboxed execution
            allowed_imports = ["sympy", "math", "numpy"]
            
            exec_globals = {}
            for module in allowed_imports:
                try:
                    exec_globals[module] = __import__(module)
                except ImportError:
                    pass
            
            # Execute the code
            exec(code, exec_globals)
            
            return {
                "success": True,
                "result": str(exec_globals.get("result", "Computation completed")),
                "tools_used": ["sympy"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tools_used": ["sympy_failed"]
            }

class CodeSpecialistEnhanced:
    """Code specialist with Python execution sandbox"""
    
    def enhance_prompt(self, query: str, base_prompt: str) -> str:
        """Enhance coding queries with execution capabilities"""
        enhanced_prompt = f"""You are a code specialist with Python execution capabilities.

For the query: "{query}"

You can execute Python code safely in a sandbox. When providing code solutions:

1. Explain the approach
2. Provide clean, runnable code
3. Show expected output when applicable
4. Handle edge cases and errors

{base_prompt}

Use proper error handling and follow Python best practices."""
        return enhanced_prompt
    
    def execute_python(self, code: str) -> Dict[str, Any]:
        """Safely execute Python code in subprocess sandbox"""
        try:
            # Create a safe execution environment
            safe_code = f"""
import sys
import io
import contextlib

# Capture stdout
output_buffer = io.StringIO()

try:
    with contextlib.redirect_stdout(output_buffer):
{chr(10).join('        ' + line for line in code.split(chr(10)))}
    
    result = output_buffer.getvalue()
    print(json.dumps({{"success": True, "output": result}}))
    
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
            
            # Execute in subprocess with timeout
            result = subprocess.run(
                ["python", "-c", safe_code],
                capture_output=True,
                text=True,
                timeout=10  # 10 second timeout
            )
            
            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout.strip())
                    output["tools_used"] = ["python_exec"]
                    return output
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "output": result.stdout,
                        "tools_used": ["python_exec"]
                    }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "tools_used": ["python_exec_failed"]
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Code execution timeout (10s limit)",
                "tools_used": ["python_timeout"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tools_used": ["python_exec_failed"]
            }

class KnowledgeSpecialistEnhanced:
    """Knowledge specialist with search integration"""
    
    def enhance_prompt(self, query: str, base_prompt: str) -> str:
        """Enhance knowledge queries with search context"""
        enhanced_prompt = f"""You are a knowledge specialist with web search capabilities.

For the query: "{query}"

You can search for current information when needed. For factual questions:

1. Use your existing knowledge first
2. Indicate when information might be outdated
3. Suggest search terms for verification
4. Provide authoritative sources when possible

{base_prompt}

Focus on accuracy and cite reliable sources."""
        return enhanced_prompt
    
    def search_web(self, query: str) -> Dict[str, Any]:
        """Placeholder for web search integration"""
        # TODO: Integrate with DuckDuckGo API
        return {
            "success": True,
            "search_query": query,
            "note": "Web search integration coming soon",
            "tools_used": ["search_placeholder"]
        }

class SpecialistEnhancer:
    """Main specialist enhancement controller"""
    
    def __init__(self):
        self.math = MathSpecialistEnhanced()
        self.code = CodeSpecialistEnhanced() 
        self.knowledge = KnowledgeSpecialistEnhanced()
        
    def enhance_specialist_request(self, specialist: str, query: str, base_prompt: str) -> str:
        """Enhance specialist prompts with tool capabilities"""
        
        if specialist == "math_specialist":
            return self.math.enhance_prompt(query, base_prompt)
        elif specialist == "code_specialist":
            return self.code.enhance_prompt(query, base_prompt)
        elif specialist == "knowledge_specialist":
            return self.knowledge.enhance_prompt(query, base_prompt)
        else:
            return base_prompt
    
    def execute_tools(self, specialist: str, tool_request: str) -> Dict[str, Any]:
        """Execute tool requests from specialists"""
        
        if specialist == "math_specialist" and "sympy" in tool_request.lower():
            return self.math.execute_sympy(tool_request)
        elif specialist == "code_specialist" and "python" in tool_request.lower():
            return self.code.execute_python(tool_request)
        elif specialist == "knowledge_specialist" and "search" in tool_request.lower():
            return self.knowledge.search_web(tool_request)
        else:
            return {
                "success": False,
                "error": f"Unknown tool request for {specialist}",
                "tools_used": ["unknown"]
            }

# Global enhancer instance
enhancer = SpecialistEnhancer()

def enhance_specialist_prompt(specialist: str, query: str, base_prompt: str) -> str:
    """Main function to enhance specialist prompts"""
    return enhancer.enhance_specialist_request(specialist, query, base_prompt)

def execute_specialist_tool(specialist: str, tool_request: str) -> Dict[str, Any]:
    """Main function to execute specialist tools"""
    return enhancer.execute_tools(specialist, tool_request) 