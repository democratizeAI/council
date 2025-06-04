# -*- coding: utf-8 -*-
"""
Voting Router with Quality Filters - Track ② Integration
========================================================

Enhanced voting system with P1 quality improvements:
- Duplicate-token detection with cloud fallback
- Confidence-weighted voting
- Quality post-processing
- Memory hooks for context-aware conversations
"""

import asyncio
import time
import random
from typing import List, Dict, Any, Optional
from loader.deterministic_loader import generate_response, get_loaded_models
from router.quality_filters import (
    check_duplicate_tokens, 
    apply_confidence_weighted_voting,
    get_optimal_decoding_params,
    post_process_response,
    calculate_quality_metrics,
    CloudRetryException
)

# Import global memory
from bootstrap import MEMORY

import logging
from router.selector import pick_specialist, load_models_config, should_use_cloud_fallback
from router_cascade import RouterCascade

logger = logging.getLogger(__name__)

class SpecialistRunner:
    """Runs individual specialists with timeout and error handling"""
    
    def __init__(self):
        self.router = RouterCascade()
    
    async def run_specialist(self, specialist: str, prompt: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Run a single specialist with timeout protection"""
        start_time = time.time()
        
        try:
            # Map specialist names to router methods
            specialist_map = {
                "math_specialist": self._run_math,
                "code_specialist": self._run_code,
                "logic_specialist": self._run_logic, 
                "knowledge_specialist": self._run_knowledge,
                "mistral_general": self._run_general
            }
            
            if specialist not in specialist_map:
                raise ValueError(f"Unknown specialist: {specialist}")
            
            # Run specialist with timeout
            result = await asyncio.wait_for(
                specialist_map[specialist](prompt),
                timeout=timeout
            )
            
            # Add metadata
            result["specialist"] = specialist
            result["latency_ms"] = (time.time() - start_time) * 1000
            result["status"] = "success"
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "specialist": specialist,
                "text": f"[TIMEOUT] {specialist} exceeded {timeout}s",
                "confidence": 0.0,
                "status": "timeout",
                "latency_ms": timeout * 1000
            }
        except Exception as e:
            return {
                "specialist": specialist,
                "text": f"[ERROR] {specialist}: {str(e)}",
                "confidence": 0.0, 
                "status": "error",
                "latency_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }
    
    async def _run_math(self, prompt: str) -> Dict[str, Any]:
        """Run math specialist (SymPy)"""
        try:
            # Force routing to math specialist
            result = await self.router.route_query(prompt, force_skill="math")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.9),
                "model": "lightning-math-sympy",
                "skill_type": "math"
            }
        except Exception as e:
            # Fallback if math specialist fails
            raise Exception(f"Math specialist failed: {e}")
    
    async def _run_code(self, prompt: str) -> Dict[str, Any]:
        """Run code specialist (DeepSeek + Sandbox)"""
        try:
            result = await self.router.route_query(prompt, force_skill="code")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.8),
                "model": "deepseek-coder-sandbox",
                "skill_type": "code"
            }
        except Exception as e:
            raise Exception(f"Code specialist failed: {e}")
    
    async def _run_logic(self, prompt: str) -> Dict[str, Any]:
        """Run logic specialist (SWI-Prolog)"""
        try:
            result = await self.router.route_query(prompt, force_skill="logic")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.7),
                "model": "swi-prolog-engine",
                "skill_type": "logic"
            }
        except Exception as e:
            raise Exception(f"Logic specialist failed: {e}")
    
    async def _run_knowledge(self, prompt: str) -> Dict[str, Any]:
        """Run knowledge specialist (FAISS RAG)"""
        try:
            result = await self.router.route_query(prompt, force_skill="knowledge")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.6),
                "model": "faiss-rag-retrieval",
                "skill_type": "knowledge"
            }
        except Exception as e:
            raise Exception(f"Knowledge specialist failed: {e}")
    
    async def _run_general(self, prompt: str) -> Dict[str, Any]:
        """Run general LLM (Mistral/OpenAI cloud fallback)"""
        try:
            result = await self.router.route_query(prompt, force_skill="agent0")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.5),
                "model": result.get("model", "cloud-fallback"),
                "skill_type": "general"
            }
        except Exception as e:
            raise Exception(f"General LLM failed: {e}")

    async def run_specialist_with_conversation(self, specialist: str, conversation_prompt: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Run a single specialist with natural conversation prompt"""
        start_time = time.time()
        
        try:
            # Map specialist names to router methods
            specialist_map = {
                "math_specialist": self._run_math_conversation,
                "code_specialist": self._run_code_conversation,
                "logic_specialist": self._run_logic_conversation, 
                "knowledge_specialist": self._run_knowledge_conversation,
                "mistral_general": self._run_general_conversation
            }
            
            if specialist not in specialist_map:
                raise ValueError(f"Unknown specialist: {specialist}")
            
            # Run specialist with conversation prompt and timeout
            result = await asyncio.wait_for(
                specialist_map[specialist](conversation_prompt),
                timeout=timeout
            )
            
            # Add metadata
            result["specialist"] = specialist
            result["latency_ms"] = (time.time() - start_time) * 1000
            result["status"] = "success"
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "specialist": specialist,
                "text": f"[TIMEOUT] {specialist} exceeded {timeout}s",
                "confidence": 0.0,
                "status": "timeout",
                "latency_ms": timeout * 1000
            }
        except Exception as e:
            return {
                "specialist": specialist,
                "text": f"[ERROR] {specialist}: {str(e)}",
                "confidence": 0.0, 
                "status": "error",
                "latency_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }
    
    async def _run_math_conversation(self, conversation_prompt: str) -> Dict[str, Any]:
        """Run math specialist with conversation style"""
        try:
            # Extract the actual user query from conversation prompt
            user_query = conversation_prompt.split("User: ")[-1].split("\nCouncil:")[0] if "User: " in conversation_prompt else conversation_prompt
            result = await self.router.route_query(user_query, force_skill="math")
            
            # Make response more conversational for math
            response_text = result["text"]
            if response_text.replace(".", "").replace("-", "").isdigit() or any(op in user_query for op in ['+', '-', '*', '/', '=', 'sqrt', 'sin', 'cos']):
                response_text = f"The answer is {response_text}! 🧮"
            
            return {
                "text": response_text,
                "confidence": result.get("confidence", 0.9),
                "model": "lightning-math-sympy",
                "skill_type": "math"
            }
        except Exception as e:
            raise Exception(f"Math specialist failed: {e}")
    
    async def _run_code_conversation(self, conversation_prompt: str) -> Dict[str, Any]:
        """Run code specialist with conversation style"""
        try:
            user_query = conversation_prompt.split("User: ")[-1].split("\nCouncil:")[0] if "User: " in conversation_prompt else conversation_prompt
            result = await self.router.route_query(user_query, force_skill="code")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.8),
                "model": "deepseek-coder-sandbox",
                "skill_type": "code"
            }
        except Exception as e:
            raise Exception(f"Code specialist failed: {e}")
    
    async def _run_logic_conversation(self, conversation_prompt: str) -> Dict[str, Any]:
        """Run logic specialist with conversation style"""
        try:
            user_query = conversation_prompt.split("User: ")[-1].split("\nCouncil:")[0] if "User: " in conversation_prompt else conversation_prompt
            result = await self.router.route_query(user_query, force_skill="logic")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.7),
                "model": "swi-prolog-engine",
                "skill_type": "logic"
            }
        except Exception as e:
            raise Exception(f"Logic specialist failed: {e}")
    
    async def _run_knowledge_conversation(self, conversation_prompt: str) -> Dict[str, Any]:
        """Run knowledge specialist with conversation style"""
        try:
            user_query = conversation_prompt.split("User: ")[-1].split("\nCouncil:")[0] if "User: " in conversation_prompt else conversation_prompt
            result = await self.router.route_query(user_query, force_skill="knowledge")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.6),
                "model": "faiss-rag-retrieval",
                "skill_type": "knowledge"
            }
        except Exception as e:
            raise Exception(f"Knowledge specialist failed: {e}")
    
    async def _run_general_conversation(self, conversation_prompt: str) -> Dict[str, Any]:
        """Run general LLM with conversation style"""
        try:
            user_query = conversation_prompt.split("User: ")[-1].split("\nCouncil:")[0] if "User: " in conversation_prompt else conversation_prompt
            result = await self.router.route_query(user_query, force_skill="agent0")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.5),
                "model": result.get("model", "cloud-fallback"),
                "skill_type": "general"
            }
        except Exception as e:
            raise Exception(f"General LLM failed: {e}")

async def vote(prompt: str, model_names: List[str] = None, top_k: int = 1, use_context: bool = True) -> Dict[str, Any]:
    """
    Run council voting with natural conversation style.
    
    Following o3plan.md: ALL messages go through 5-head Council with 
    friendly conversation prompts and memory context.
    """
    start_time = time.time()
    
    # Build natural conversation prompt (o3plan.md recipe)
    conversation_prompt = build_conversation_prompt(prompt)
    
    # Determine specialists to try
    if model_names is None:
        # Use intelligent specialist selection
        config = load_models_config()
        specialist, confidence, tried = pick_specialist(prompt, config)
        
        # Add primary specialist plus fallbacks
        specialists_to_try = [specialist]
        
        # Add other specialists if confidence is low
        if confidence < 0.8:
            other_specialists = [s for s in config["specialists_order"] if s != specialist]
            specialists_to_try.extend(other_specialists[:2])  # Try 2 more
    else:
        specialists_to_try = model_names
    
    # Run specialists in priority order with conversation-style prompts
    runner = SpecialistRunner()
    results = []
    
    for specialist in specialists_to_try:
        logger.info(f"🎯 Council member: {specialist}")
        
        try:
            # Pass the natural conversation prompt to specialists
            result = await runner.run_specialist_with_conversation(specialist, conversation_prompt)
            results.append(result)
            
            # If we got a good result from a high-priority specialist, stop here
            if (result["status"] == "success" and 
                result["confidence"] > 0.85 and  # Raised from 0.7 to 0.85
                "specialist" in specialist):
                logger.info(f"✅ {specialist} provided confident answer ({result['confidence']:.2f})")
                break
                
        except Exception as e:
            logger.warning(f"⚠️ {specialist} failed: {e}")
            
            # Check if we should try cloud fallback
            if should_use_cloud_fallback(specialist, str(e)):
                logger.info("☁️ Triggering cloud fallback")
                try:
                    cloud_result = await runner.run_specialist_with_conversation("mistral_general", conversation_prompt)
                    results.append(cloud_result)
                except Exception as cloud_error:
                    logger.error(f"☁️ Cloud fallback also failed: {cloud_error}")
    
    # If no results, emergency fallback
    if not results:
        emergency_result = {
            "specialist": "emergency_fallback",
            "text": f"I apologize, but all specialists are currently unavailable. Please try again later.",
            "confidence": 0.1,
            "status": "emergency",
            "latency_ms": (time.time() - start_time) * 1000
        }
        results.append(emergency_result)
    
    # Vote for best result
    successful_results = [r for r in results if r["status"] == "success"]
    if not successful_results:
        successful_results = results  # Use whatever we have
    
    # 🗳️ CONSENSUS FUSION: Instead of just picking winner, fuse all answers
    if len(successful_results) > 1:
        # Get top 5 candidates for fusion
        top_candidates = sorted(successful_results, key=lambda r: r.get("confidence", 0), reverse=True)[:5]
        
        # Fuse all answers into consensus
        try:
            fused_answer = await consensus_fuse(top_candidates, prompt)
            logger.info(f"🤝 Consensus fusion: {len(top_candidates)} heads → unified answer")
            
            # Create consensus winner
            winner = {
                "specialist": "council_consensus", 
                "text": fused_answer,
                "confidence": sum(r["confidence"] for r in top_candidates) / len(top_candidates),
                "status": "consensus",
                "model": "council-fusion",
                "candidates": top_candidates,  # Keep all candidates for transparency
                "fusion_method": "local_llm"
            }
        except Exception as e:
            logger.warning(f"Consensus fusion failed: {e}, falling back to top candidate")
            winner = max(successful_results, key=lambda r: r.get("confidence", 0))
            winner["candidates"] = top_candidates  # Still provide candidates
    else:
        # Single answer or emergency fallback
        winner = max(successful_results, key=lambda r: r.get("confidence", 0))
    
    # Voting statistics (enhanced for consensus)
    voting_stats = {
        "total_specialists": len(results),
        "successful_specialists": len(successful_results),
        "winner_confidence": winner["confidence"],
        "total_latency_ms": (time.time() - start_time) * 1000,
        "specialists_tried": [r["specialist"] for r in results],
        "consensus_fusion": winner.get("specialist") == "council_consensus",
        "candidates_count": len(winner.get("candidates", []))
    }
    
    logger.info(f"🏆 Council decision: {winner['specialist']} wins with {winner['confidence']:.2f} confidence")
    
    # 🧠 Log Q&A to memory with success flags (required for Phase 3 self-improvement)
    try:
        # Use singleton memory instead of creating new instance
        
        # Determine success based on confidence and status
        success_flag = (winner["confidence"] > 0.5 and 
                       winner.get("status", "success") == "success" and
                       "ERROR" not in winner["text"] and
                       "TIMEOUT" not in winner["text"])
        
        # Log the conversation pair for Agent-0 learning
        original_prompt = prompt.split("\nUser query: ")[-1] if "\nUser query: " in prompt else prompt
        MEMORY.add(original_prompt, {
            "role": "user", 
            "timestamp": time.time(),
            "session_id": f"council_{int(time.time())}"
        })
        MEMORY.add(winner["text"], {
            "role": "assistant", 
            "timestamp": time.time(),
            "success": success_flag,  # Critical for Phase 3 failure harvesting
            "confidence": winner["confidence"],
            "specialist": winner["specialist"],
            "latency_ms": voting_stats["total_latency_ms"],
            "council_decision": True
        })
        
        logger.debug(f"💾 Logged Q&A to memory: success={success_flag}, confidence={winner['confidence']:.2f}")
        
    except Exception as e:
        logger.warning(f"Memory logging failed: {e}")
    
    return {
        "text": winner["text"],
        "model": winner.get("model", winner["specialist"]),
        "winner": winner,
        "voting_stats": voting_stats,
        "specialists_tried": [r["specialist"] for r in results],
        "council_decision": True,
        "timestamp": time.time(),
        # 🗳️ Consensus transparency
        "consensus_fusion": winner.get("specialist") == "council_consensus",
        "candidates": winner.get("candidates", []),  # All head votes for transparency
        "fusion_method": winner.get("fusion_method", "single_winner")
    }

def smart_select(prompt: str, model_names: List[str]) -> str:
    """
    Smart single-model selection for simple prompts (Track ① fast path)
    
    Selects the best model for a given prompt without running inference.
    Enhanced with quality considerations.
    """
    if not model_names:
        return model_names[0] if model_names else "unknown"
    
    # Simple heuristic-based selection with quality focus
    prompt_lower = prompt.lower()
    
    # Math-related prompts → prefer math specialist
    if any(math_word in prompt_lower for math_word in ['math', 'calculate', 'add', 'subtract', '+', '-', '*', '/', 'equals']):
        for model in model_names:
            if 'math' in model.lower():
                return model
    
    # Code-related prompts → prefer code specialist  
    if any(code_word in prompt_lower for code_word in ['code', 'python', 'def ', 'function', 'import', 'class']):
        for model in model_names:
            if 'code' in model.lower():
                return model
    
    # Logic prompts → prefer logic specialist
    if any(logic_word in prompt_lower for logic_word in ['if ', 'then', 'logic', 'reasoning', 'true', 'false']):
        for model in model_names:
            if 'logic' in model.lower():
                return model
    
    # For general prompts, prefer models known for quality
    # Priority order: phi2 > tinyllama > mistral > others
    quality_priority = ['phi2', 'tinyllama', 'mistral']
    
    for priority_model in quality_priority:
        for model in model_names:
            if priority_model in model.lower():
                return model
    
    # Fallback to first available model
    return model_names[0]

def is_simple_greeting(prompt: str) -> bool:
    """Detect if this is a simple greeting that doesn't need specialist routing"""
    prompt_lower = prompt.lower().strip()
    simple_greetings = [
        'hi', 'hello', 'hey', 'hey!', 'hi!', 'hello!', 
        'good morning', 'good afternoon', 'good evening',
        'how are you', 'how are you?', 'whats up', "what's up",
        'sup', 'yo', 'greetings'
    ]
    return prompt_lower in simple_greetings or len(prompt_lower) <= 3

def handle_simple_greeting(prompt: str, start_time: float) -> Dict[str, Any]:
    """Handle simple greetings with memory-aware, contextual responses"""
    
    import time  # Add missing import
    
    # Still use memory context for greetings - check for user name, preferences, etc.
    contextual_greeting = prompt
    memory_context = ""
    
    try:
        from faiss_memory import FaissMemory
        memory = FaissMemory()
        context_results = memory.query(prompt, k=2)  # Get recent context
        
        if context_results:
            # Look for user name or preferences in memory
            names = []
            recent_topics = []
            
            for result in context_results:
                text = result.get("text", "")
                # Extract potential names (simple heuristic)
                if "my name is" in text.lower() or "i'm " in text.lower():
                    names.extend([word.strip(".,!") for word in text.split() if word[0].isupper() and len(word) > 2])
                # Extract recent topics
                if len(text) > 10:
                    recent_topics.append(text[:50] + "..." if len(text) > 50 else text)
            
            # Build personalized greeting
            if names:
                user_name = names[-1]  # Use most recent name
                contextual_greetings = [
                    f"Hello {user_name}! Great to see you again. How can I help you today?",
                    f"Hi {user_name}! I'm ready to assist with any questions you have.",
                    f"Hey {user_name}! 👋 What would you like to work on today?",
                ]
                import random
                response_text = random.choice(contextual_greetings)
            elif recent_topics:
                # Reference recent conversation
                response_text = f"Hello! Welcome back. I see we were discussing {recent_topics[0]}. What would you like to explore now?"
            else:
                # Standard but context-aware greeting
                contextual_greetings = [
                    "Hello! I'm your AutoGen Council assistant. How can I help you today?",
                    "Hi there! I'm ready to help with math, code, logic, knowledge, or general questions!",
                    "Hey! 👋 What would you like to work on? I have specialists for math, coding, reasoning, and more!",
                ]
                import random
                response_text = random.choice(contextual_greetings)
                
            memory_context = f"Found {len(context_results)} relevant memories"
        else:
            # First-time greeting
            response_text = "Hello! I'm your AutoGen Council assistant with specialized capabilities. What would you like to explore?"
            
        # Log this greeting interaction to memory (just like the full system)
        memory.add(prompt, {"role": "user", "timestamp": time.time(), "greeting": True})
        memory.add(response_text, {"role": "assistant", "timestamp": time.time(), "greeting_response": True, "success": True})
        
    except Exception as e:
        logger.warning(f"Memory lookup failed for greeting: {e}")
        # Fallback greeting
        response_text = "Hello! I'm your AutoGen Council assistant. How can I help you today?"
    
    return {
        "text": response_text,
        "model": "memory_aware_greeting_handler",
        "winner": {
            "specialist": "memory_aware_greeting_handler", 
            "text": response_text,
            "confidence": 1.0,
            "model": "contextual-greeting-handler",
            "memory_context": memory_context
        },
        "voting_stats": {
            "total_specialists": 1,
            "successful_specialists": 1,
            "winner_confidence": 1.0,
            "total_latency_ms": (time.time() - start_time) * 1000,
            "specialists_tried": ["memory_aware_greeting_handler"],
            "memory_used": True
        },
        "specialists_tried": ["memory_aware_greeting_handler"],
        "council_decision": False,  # Fast path but still memory-aware
        "memory_context_applied": True,
        "timestamp": time.time()
    }

def build_conversation_prompt(user_msg: str) -> str:
    """
    Build natural conversation prompt with memory context.
    
    Following o3plan.md recipe: 
    - Fetch 3 most relevant memories
    - Add friendly system prompt
    - Make Council sound conversational
    """
    try:
        # Use singleton memory instead of creating new instance
        ctx = MEMORY.query(user_msg, k=3)
        ctx_block = "\n".join(f"- {m['text']}" for m in ctx) if ctx else "- none"
        
        # Guard rails: truncate to 1000 chars
        if len(ctx_block) > 1000:
            ctx_block = ctx_block[:1000] + "..."
        
    except Exception as e:
        logger.warning(f"Memory context failed: {e}")
        ctx_block = "- none"
    
    # 2) Build conversation-style system prompt
    system_prompt = f"""You are the **Council**, a collective of five specialist heads.
Be concise, helpful, and keep a friendly tone.

Relevant past facts:
{ctx_block}
—
Answer the user:"""

    # 3) Return formatted conversation prompt
    return f"{system_prompt}\n\nUser: {user_msg}\nCouncil:"

async def consensus_fuse(candidates: List[Dict[str, Any]], original_prompt: str) -> str:
    """
    Consensus fusion: merge multiple specialist answers into unified response.
    
    Uses local LLM to synthesize all candidate answers into a single,
    comprehensive, non-repetitive answer.
    """
    from prometheus_client import Summary
    import time
    
    # Prometheus metric for fusion latency
    try:
        FUSE_LAT = Summary("swarm_consensus_latency_seconds", "Consensus fusion step")
        with FUSE_LAT.time():
            return await _perform_fusion(candidates, original_prompt)
    except:
        # Fallback without metrics if prometheus not available
        return await _perform_fusion(candidates, original_prompt)

async def _perform_fusion(candidates: List[Dict[str, Any]], original_prompt: str) -> str:
    """Perform the actual fusion of candidate answers"""
    
    # Build bullet list of all candidate answers
    bullet_list = []
    for i, candidate in enumerate(candidates):
        specialist = candidate.get("specialist", f"head_{i}")
        text = candidate.get("text", "").strip()
        confidence = candidate.get("confidence", 0)
        
        if text and text not in [c.get("text", "") for c in candidates[:i]]:  # Avoid duplicates
            bullet_list.append(f"- **{specialist}** ({confidence:.2f}): {text}")
    
    bullet_text = "\n".join(bullet_list)
    
    # Extract user query from conversation prompt if needed
    user_query = original_prompt
    if "User: " in original_prompt:
        user_query = original_prompt.split("User: ")[-1].split("\nCouncil:")[0]
    
    # Consensus fusion prompt
    fusion_prompt = f"""As the Council Scribe, merge these specialist answers into a single, comprehensive response.

User asked: {user_query}

Specialist answers:
{bullet_text}

Instructions:
- Combine the best insights from each specialist
- Remove redundancy and contradictions
- Keep the response concise but complete
- Maintain a helpful, friendly tone
- Don't mention the specialists or fusion process

Unified Council answer:"""

    try:
        # Use the router to get a local LLM response for fusion
        from router_cascade import RouterCascade
        router = RouterCascade()
        
        # Force use of agent0 (general) for fusion
        result = await router.route_query(fusion_prompt, force_skill="agent0")
        fused_text = result.get("text", "").strip()
        
        # Clean up the response
        if fused_text.startswith("Unified Council answer:"):
            fused_text = fused_text.replace("Unified Council answer:", "").strip()
        
        # Fallback if fusion is empty or too short
        if len(fused_text) < 20:
            # Simple rule-based fusion as fallback
            best_answer = max(candidates, key=lambda c: c.get("confidence", 0))
            return best_answer.get("text", "I apologize, but I couldn't process your request.")
        
        return fused_text
        
    except Exception as e:
        logger.warning(f"LLM fusion failed: {e}, using rule-based fusion")
        
        # Rule-based fallback fusion
        if candidates:
            best_answer = max(candidates, key=lambda c: c.get("confidence", 0))
            other_answers = [c for c in candidates if c != best_answer]
            
            if other_answers:
                # Simple merge: best answer + additional insights
                additional_insights = []
                for candidate in other_answers[:2]:  # Top 2 additional insights
                    text = candidate.get("text", "").strip()
                    if text and len(text) > 10 and text not in best_answer.get("text", ""):
                        additional_insights.append(text)
                
                if additional_insights:
                    return f"{best_answer.get('text', '')} Additionally, {' '.join(additional_insights)}"
            
            return best_answer.get("text", "I apologize, but I couldn't process your request.")
        
        return "I apologize, but I couldn't process your request." 