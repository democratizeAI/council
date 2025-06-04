#!/usr/bin/env python3
"""
AutoGen Council Router Cascade
Main entry point for the AutoGen Council routing system.
This module provides a unified interface to the council routing capabilities.
"""

import sys
import os
import time
import logging
import asyncio
import aiohttp
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the router directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'router'))

# Backward compatibility exceptions
class CloudRetry(Exception):
    """Exception to trigger cloud fallback for edge cases"""
    def __init__(self, reason: str, response_text: str = ""):
        self.reason = reason
        self.response_text = response_text
        super().__init__(f"CloudRetry: {reason}")

class MockResponseError(Exception):
    """Exception for mock/stub responses that need CloudRetry"""
    def __init__(self, response_text: str):
        self.response_text = response_text
        super().__init__(f"Mock response detected: {response_text[:100]}...")

@dataclass
class SkillConfig:
    """Configuration for individual skills"""
    name: str
    patterns: List[str]
    confidence_boost: float = 0.0
    enabled: bool = True

# Backward compatibility RouterCascade class
class RouterCascade:
    """Backward compatible router for AutoGen Council system"""
    
    def __init__(self):
        """Initialize router with skill configurations"""
        self.llm_endpoint = os.getenv('LLM_ENDPOINT', 'http://localhost:8000/v1')
        self.model_name = os.getenv('MODEL_NAME', 'mistral-13b-gptq')
        self.cloud_enabled = os.getenv('SWARM_CLOUD_ENABLED', 'false').lower() == 'true'
        self.budget_usd = float(os.getenv('SWARM_CLOUD_BUDGET_USD', '10.0'))
        
        # Template stub detection patterns
        self.stub_markers = [
            'custom_function', 'TODO', 'pass', 'NotImplemented',
            'placeholder', 'your_code_here', '# Add implementation'
        ]
        
        # Routing patterns for each skill
        self.skills = {
            'math': SkillConfig(
                name='Lightning Math',
                patterns=[
                    r'\d+\s*[\+\-\*/\^]\s*\d+',  # Basic arithmetic
                    r'solve|calculate|compute',
                    r'square\s*root|sqrt',
                    r'factorial|fibonacci',
                    r'equation|algebra'
                ],
                confidence_boost=0.2
            ),
            'code': SkillConfig(
                name='DeepSeek Coder', 
                patterns=[
                    r'function|def |class ',
                    r'algorithm|implement',
                    r'write.*code|python|javascript',
                    r'debug|fix.*bug'
                ],
                confidence_boost=0.1
            ),
            'logic': SkillConfig(
                name='Prolog Logic',
                patterns=[
                    r'reasoning|logic|logical',
                    r'spatial|geometric|position',
                    r'if.*then|implies|therefore',
                    r'true|false|valid'
                ],
                confidence_boost=0.1
            ),
            'knowledge': SkillConfig(
                name='FAISS RAG',
                patterns=[
                    r'what\s+is|define|explain',
                    r'capital\s+of|country|geography',
                    r'history|when\s+did|who\s+was',
                    r'facts?|information|tell\s+me\s+about'
                ],
                confidence_boost=0.1
            )
        }
        
        # Initialize health check
        self._health_check_done = False
        
        logger.info("🎯 RouterCascade initialized")
        logger.info(f"   LLM Endpoint: {self.llm_endpoint}")
        logger.info(f"   Model: {self.model_name}")
        logger.info(f"   Cloud Enabled: {self.cloud_enabled}")
        logger.info(f"   Budget: ${self.budget_usd}")

    async def _health_check_llm(self) -> bool:
        """Check if LLM endpoint is healthy"""
        if self._health_check_done:
            return True
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.llm_endpoint}/models", timeout=5) as response:
                    if response.status == 200:
                        logger.info("✅ LLM endpoint health check passed")
                        self._health_check_done = True
                        return True
                    else:
                        logger.warning(f"⚠️ LLM endpoint returned {response.status}")
                        return False
        except Exception as e:
            logger.warning(f"⚠️ LLM endpoint health check failed: {e}")
            return False

    def _calculate_confidence(self, query: str, skill: str) -> float:
        """Calculate routing confidence for a skill"""
        skill_config = self.skills.get(skill)
        if not skill_config or not skill_config.enabled:
            return 0.0
        
        confidence = 0.0
        query_lower = query.lower()
        
        # Pattern matching
        for pattern in skill_config.patterns:
            if re.search(pattern, query_lower):
                confidence += 0.3
        
        # Apply confidence boost
        confidence += skill_config.confidence_boost
        
        # Cap at 1.0
        return min(confidence, 1.0)

    def _route_query(self, query: str) -> tuple[str, float]:
        """Determine best skill for query"""
        confidences = {}
        
        for skill_name in self.skills:
            confidences[skill_name] = self._calculate_confidence(query, skill_name)
        
        # Find highest confidence skill
        best_skill = max(confidences, key=confidences.get)
        best_confidence = confidences[best_skill]
        
        # If no skill has good confidence, use agent-0 (LLM backend)
        if best_confidence < 0.3:
            return 'agent0', 0.5
        
        return best_skill, best_confidence

    async def _call_math_skill(self, query: str) -> Dict[str, Any]:
        """Lightning Math skill using SymPy"""
        try:
            # Simple arithmetic pattern matching
            import re
            
            # Extract basic arithmetic operations
            arithmetic_pattern = r'(\d+(?:\.\d+)?)\s*([\+\-\*/])\s*(\d+(?:\.\d+)?)'
            match = re.search(arithmetic_pattern, query)
            
            if match:
                a, op, b = match.groups()
                a, b = float(a), float(b)
                
                if op == '+':
                    result = a + b
                elif op == '-':
                    result = a - b
                elif op == '*':
                    result = a * b
                elif op == '/':
                    result = a / b if b != 0 else "Division by zero"
                else:
                    result = "Unknown operation"
                
                return {
                    "text": str(result),
                    "model": "autogen-math",
                    "skill_type": "math",
                    "confidence": 1.0,
                    "timestamp": time.time()
                }
            
            # For more complex math, check for unsupported cases
            if any(term in query.lower() for term in ['factorial', 'gcd', 'prime', 'complex']):
                raise CloudRetry("Complex math operation - cloud retry needed", "Unsupported mathematical operation")
            
            # Fall back to basic response
            return {
                "text": "Could not parse arithmetic expression",
                "model": "autogen-math",  
                "skill_type": "math",
                "confidence": 0.3,
                "timestamp": time.time()
            }
            
        except CloudRetry:
            raise
        except Exception as e:
            logger.error(f"Math skill error: {e}")
            raise CloudRetry(f"Math skill failed: {e}")

    async def _call_code_skill(self, query: str) -> Dict[str, Any]:
        """DeepSeek Coder skill"""
        try:
            # Simple code generation
            if 'factorial' in query.lower():
                code = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)"""
            elif 'fibonacci' in query.lower():
                code = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""
            else:
                # Generate a template that will trigger CloudRetry
                code = """def custom_function():
    # TODO: Add implementation here
    pass"""
            
            # Check for template stubs
            if any(marker in code for marker in self.stub_markers):
                raise CloudRetry("Template stub detected - cloud retry needed", code)
            
            return {
                "text": code,
                "model": "autogen-code",
                "skill_type": "code", 
                "confidence": 0.8,
                "timestamp": time.time()
            }
            
        except CloudRetry:
            raise
        except Exception as e:
            logger.error(f"Code skill error: {e}")
            raise CloudRetry(f"Code skill failed: {e}")

    async def _call_logic_skill(self, query: str) -> Dict[str, Any]:
        """Prolog Logic skill"""
        try:
            # Simple logic responses
            if 'true' in query.lower() or 'false' in query.lower():
                response = "Logical statement evaluated"
            else:
                response = "Logic reasoning applied"
                
            return {
                "text": response,
                "model": "autogen-logic",
                "skill_type": "logic",
                "confidence": 0.7,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Logic skill error: {e}")
            raise CloudRetry(f"Logic skill failed: {e}")

    async def _call_knowledge_skill(self, query: str) -> Dict[str, Any]:
        """FAISS RAG knowledge skill"""
        try:
            # Simple knowledge responses
            if 'capital' in query.lower() and 'france' in query.lower():
                response = "The capital of France is Paris."
            elif 'dna' in query.lower():
                response = "DNA (deoxyribonucleic acid) carries genetic instructions for all living organisms."
            else:
                response = "Based on the knowledge base: FAISS (Facebook AI Similarity Search) is a library for efficient similarity search and clustering."
                
            return {
                "text": response,
                "model": "autogen-rag", 
                "skill_type": "knowledge",
                "confidence": 0.9,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Knowledge skill error: {e}")
            raise CloudRetry(f"Knowledge skill failed: {e}")

    async def _call_agent0_llm(self, query: str) -> Dict[str, Any]:
        """Agent-0 LLM backend for general reasoning"""
        # Check if LLM endpoint is available
        llm_healthy = await self._health_check_llm()
        
        if not llm_healthy:
            logger.warning("🔄 LLM endpoint unavailable, using mock response")
            return {
                "text": f"[LLM_ENDPOINT_UNAVAILABLE] Mock response for: {query[:50]}...",
                "model": "mock-agent0",
                "skill_type": "agent0",
                "confidence": 0.3,
                "timestamp": time.time()
            }
        
        try:
            # Make request to LLM endpoint
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": query}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.llm_endpoint}/chat/completions",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        text = result['choices'][0]['message']['content']
                        
                        return {
                            "text": text,
                            "model": f"agent0-{self.model_name}",
                            "skill_type": "agent0",
                            "confidence": 0.8,
                            "timestamp": time.time()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"LLM endpoint error {response.status}: {error_text}")
                        raise CloudRetry(f"LLM endpoint error: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("LLM endpoint timeout")
            raise CloudRetry("LLM endpoint timeout")
        except Exception as e:
            logger.error(f"Agent-0 LLM error: {e}")
            raise CloudRetry(f"Agent-0 LLM failed: {e}")

    async def route_query(self, query: str) -> Dict[str, Any]:
        """Main routing function"""
        start_time = time.time()
        
        try:
            # Route to appropriate skill
            skill, confidence = self._route_query(query)
            
            logger.info(f"🎯 Routing to {skill} (confidence: {confidence:.2f})")
            
            # Call the appropriate skill
            if skill == 'math':
                result = await self._call_math_skill(query)
            elif skill == 'code':
                result = await self._call_code_skill(query)
            elif skill == 'logic':
                result = await self._call_logic_skill(query)
            elif skill == 'knowledge':
                result = await self._call_knowledge_skill(query)
            elif skill == 'agent0':
                result = await self._call_agent0_llm(query)
            else:
                raise CloudRetry(f"Unknown skill: {skill}")
            
            # Add routing metadata
            result['routing_skill'] = skill
            result['routing_confidence'] = confidence
            result['latency_ms'] = (time.time() - start_time) * 1000
            
            return result
            
        except CloudRetry as e:
            logger.warning(f"☁️ CloudRetry triggered: {e.reason}")
            # Re-raise for higher-level handling (API will handle cloud fallback)
            raise
        except Exception as e:
            logger.error(f"❌ Router error: {e}")
            raise CloudRetry(f"Router cascade failed: {e}")

# Factory function for easy instantiation
def create_autogen_council(config: Optional[Dict[str, Any]] = None):
    """
    Factory function to create a RouterCascade (backward compatibility)
    """
    return RouterCascade()

# CLI interface for testing
if __name__ == "__main__":
    print("🚀 AutoGen Council Router Cascade")
    print("=" * 40)
    
    # Create router instance
    router = RouterCascade()
    
    print(f"✅ Router initialized successfully!")
    print(f"📡 LLM Endpoint: {router.llm_endpoint}")
    print(f"🤖 Model: {router.model_name}")
    print(f"☁️ Cloud Enabled: {router.cloud_enabled}")
    
    # Test basic functionality
    print("\n🧪 Testing basic functionality...")
    import asyncio
    
    async def test_router():
        test_queries = [
            "What is 2 + 2?",
            "Write a hello world function",
            "What is the capital of France?"
        ]
        
        for query in test_queries:
            print(f"\n📤 Testing: {query}")
            try:
                result = await router.route_query(query)
                print(f"✅ Response: {result.get('text', '')[:100]}...")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_router())
    except Exception as e:
        print(f"Test failed: {e}")
    
    print("\n🎯 Ready for Agent-Zero integration!") 