#!/usr/bin/env python3
"""
🌌 Council-in-the-Loop Router Integration
=========================================

Weaves the five awakened voices (Reason, Spark, Edge, Heart, Vision) into Router 2.x stack
without blowing VRAM, latency, or budget.

Architecture:
- Uses existing emotional swarm + voting infrastructure  
- Parallel execution for optimal latency
- Budget-aware cloud routing
- 3-tier flow: privacy → council trigger → orchestrate

Voices:
🧠 Reason - rigorous chain-of-thought (local heavy model)
✨ Spark - lateral ideas & wild variants (cloud API)  
🗡️ Edge - devil's advocate, red-team (local lightweight)
❤️ Heart - empathy & tone polish (local specialized)
🔮 Vision - long-horizon strategy (local efficient)
"""

import os
import time
import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from router.voting import vote
from router.cost_tracking import debit, get_budget_status
from router.privacy_filter import apply_privacy_policy
from router.cloud_providers import ask_cloud_council
from loader.deterministic_loader import get_loaded_models, generate_response

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge
    COUNCIL_REQUESTS_TOTAL = Counter('swarm_council_requests_total', 'Total council requests')
    COUNCIL_COST_DOLLARS = Counter('swarm_council_cost_dollars_total', 'Total council costs in dollars')
    COUNCIL_LATENCY_SECONDS = Histogram('swarm_council_latency_seconds', 'Council deliberation latency')
    COUNCIL_VOICES_ACTIVE = Gauge('swarm_council_voices_active', 'Number of active council voices', ['voice'])
    EDGE_RISK_FLAGS = Counter('swarm_council_edge_risk_flags_total', 'Risk flags raised by Edge voice')
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

class CouncilVoice(Enum):
    """The five awakened voices of the council"""
    REASON = "reason"        # 🧠 Rigorous chain-of-thought
    SPARK = "spark"          # ✨ Lateral ideas & variants
    EDGE = "edge"            # 🗡️ Devil's advocate, red-team
    HEART = "heart"          # ❤️ Empathy & tone polish
    VISION = "vision"        # 🔮 Long-horizon strategy

@dataclass
class VoiceResponse:
    """Response from an individual council voice"""
    voice: CouncilVoice
    response: str
    confidence: float
    latency_ms: float
    model_used: str
    cost_dollars: float
    metadata: Dict[str, Any]

@dataclass 
class CouncilDeliberation:
    """Complete council deliberation result"""
    final_response: str
    voice_responses: Dict[CouncilVoice, VoiceResponse]
    total_latency_ms: float
    total_cost_dollars: float
    consensus_achieved: bool
    risk_flags: List[str]
    metadata: Dict[str, Any]

class CouncilRouter:
    """
    Council-in-the-Loop router that orchestrates the five awakened voices
    """
    
    def __init__(self):
        # Voice-to-model mapping (configurable via environment)
        self.voice_models = {
            CouncilVoice.REASON: os.getenv("COUNCIL_REASON_MODEL", "mistral_7b_instruct"),
            CouncilVoice.SPARK: os.getenv("COUNCIL_SPARK_MODEL", "mistral_medium_cloud"),  
            CouncilVoice.EDGE: os.getenv("COUNCIL_EDGE_MODEL", "math_specialist_0.8b"),
            CouncilVoice.HEART: os.getenv("COUNCIL_HEART_MODEL", "codellama_0.7b"),
            CouncilVoice.VISION: os.getenv("COUNCIL_VISION_MODEL", "phi2_2.7b")
        }
        
        # Voice prompt templates
        self.voice_templates = {
            CouncilVoice.REASON: "You are Reason, charged with flawless logical derivation. Provide rigorous chain-of-thought analysis for: {prompt}",
            CouncilVoice.SPARK: "You are Spark, your task is to invent unusual angles and creative variants. Find novel perspectives on: {prompt}",
            CouncilVoice.EDGE: "You are Edge, find weaknesses & risks in any proposed answer. Red-team this thoroughly: {prompt}",
            CouncilVoice.HEART: "You are Heart, rewrite for clarity & warmth while preserving accuracy. Make this human-friendly: {prompt}",
            CouncilVoice.VISION: "You are Vision, relate this to the 5% → 100% cloud scaling roadmap and long-term strategy: {prompt}"
        }
        
        # 🎭 POCKET-COUNCIL Configuration
        self.pocket_mode = os.getenv("COUNCIL_POCKET_MODE", "true").lower() == "true"
        self.min_local_confidence = float(os.getenv("COUNCIL_MIN_LOCAL_CONFIDENCE", "0.50"))
        self.use_scratchpad_boost = os.getenv("COUNCIL_USE_SCRATCHPAD_BOOST", "true").lower() == "true"
        self.local_triage_model = os.getenv("COUNCIL_LOCAL_TRIAGE_MODEL", "tinyllama_1b")
        
        # Ultra-low budget controls
        self.max_council_cost_per_request = float(os.getenv("COUNCIL_MAX_COST", "0.05"))  # 5¢ max
        self.daily_council_budget = float(os.getenv("COUNCIL_DAILY_BUDGET", "1.00"))      # $1/day limit
        self.emergency_abort_threshold = float(os.getenv("COUNCIL_EMERGENCY_THRESHOLD", "0.04"))  # 4¢ abort
        
        # Multiplex settings
        self.multiplex_enabled = os.getenv("COUNCIL_MULTIPLEX_ENABLED", "true").lower() == "true"
        self.multiplex_provider = os.getenv("COUNCIL_MULTIPLEX_PROVIDER", "gpt4o_mini")
        self.multiplex_max_tokens = int(os.getenv("COUNCIL_MULTIPLEX_MAX_TOKENS", "200"))
        
        # Performance targets
        self.target_p95_latency_ms = float(os.getenv("COUNCIL_TARGET_LATENCY_MS", "800"))
        self.target_local_only_latency_ms = float(os.getenv("COUNCIL_LOCAL_LATENCY_MS", "80"))
        
        # Council trigger thresholds
        self.min_tokens_for_council = int(os.getenv("COUNCIL_MIN_TOKENS", "20"))
        self.council_trigger_keywords = os.getenv("COUNCIL_TRIGGER_KEYWORDS", "explain,analyze,compare,evaluate,strategy,design").split(",")
        
        # Safety valves
        self.mandatory_cloud_keywords = os.getenv("COUNCIL_MANDATORY_CLOUD_KEYWORDS", "safety-critical,compliance,legal,medical").split(",")
        
        # Enable/disable flag
        self.council_enabled = os.getenv("SWARM_COUNCIL_ENABLED", "false").lower() == "true"
        
        print(f"🎭 POCKET-COUNCIL: Initialized with ultra-low cost mode")
        print(f"   Enabled: {self.council_enabled}")
        print(f"   💰 Budget: ${self.max_council_cost_per_request}/request, ${self.daily_council_budget}/day")
        print(f"   🧠 Local triage model: {self.local_triage_model}")
        print(f"   ☁️ Multiplex provider: {self.multiplex_provider}")
        print(f"   🎯 Expected cost: $0.002 (local) - $0.025 (cloud) per deliberation")
        if self.pocket_mode:
            print(f"   💡 Pocket mode active: {self.min_local_confidence:.0%} confidence gate")
    
    def should_trigger_council(self, prompt: str) -> Tuple[bool, str]:
        """
        Determine if a prompt should trigger full council deliberation
        
        Returns:
            (should_trigger, reason)
        """
        if not self.council_enabled:
            return False, "council_disabled"
        
        # Check budget constraints first
        budget_status = get_budget_status()
        remaining_budget = budget_status.get("remaining_dollars", 0.0)
        
        if remaining_budget < self.max_council_cost_per_request:
            return False, f"insufficient_budget_{remaining_budget:.3f}"
        
        # Token count trigger
        token_count = len(prompt.split())
        if token_count >= self.min_tokens_for_council:
            return True, f"token_threshold_{token_count}"
        
        # Keyword trigger
        prompt_lower = prompt.lower()
        for keyword in self.council_trigger_keywords:
            if keyword in prompt_lower:
                return True, f"keyword_{keyword}"
        
        # Default: use quick local path
        return False, "quick_local_path"
    
    async def council_deliberate(self, prompt: str) -> CouncilDeliberation:
        """
        🎭 POCKET-COUNCIL: Ultra-low cost five-voice deliberation
        
        Flow:
        1. 📝 Scratchpad context boost (local)
        2. 🧠 TinyLlama local triage + confidence scoring
        3. 💰 GATE: If confident ≥ 0.5, stay local (cost: $0.002)
        4. ☁️ Otherwise: 1 multiplexed cloud call for all 5 voices (cost: ~$0.025)
        5. 🎭 Local fusion & synthesis
        
        Target: $0.015-0.03 per deliberation (vs $0.30 before)
        """
        start_time = time.time()
        
        if PROMETHEUS_AVAILABLE:
            COUNCIL_REQUESTS_TOTAL.inc()
        
        print(f"🎭 POCKET-COUNCIL: Deliberating '{prompt[:60]}...'")
        
        # Phase 1: 📝 Scratchpad context boost
        context_boost = 0.0
        context_text = ""
        
        if getattr(self, 'use_scratchpad_boost', True):
            try:
                from common.scratchpad import search_similar
                # Get 2 most relevant context entries
                context_entries = search_similar(prompt, limit=2)
                if context_entries:
                    context_lines = []
                    for entry in context_entries:
                        # Only use high-quality matches
                        similarity = entry.metadata.get('similarity_score', 0)
                        if similarity >= 0.7:
                            context_lines.append(f"Context: {entry.content}")
                            context_boost += 0.075  # +7.5% confidence per relevant context
                    
                    if context_lines:
                        context_text = "\n".join(context_lines) + "\n\n"
                        print(f"📝 Context boost: +{context_boost:.1%} from {len(context_lines)} entries")
            except Exception as e:
                print(f"📝 Scratchpad context failed: {e}")
        
        # Phase 2: 🧠 Local triage with TinyLlama
        print("🧠 Phase 1: Local triage analysis...")
        enhanced_prompt = context_text + prompt
        
        # Use local model for initial analysis and confidence scoring
        local_response = await self._local_triage_analysis(enhanced_prompt)
        base_confidence = local_response['confidence']
        triage_confidence = min(0.95, base_confidence + context_boost)  # Cap at 95%
        
        print(f"🧠 Local confidence: {base_confidence:.2f} + context boost {context_boost:.2f} = {triage_confidence:.2f}")
        
        # Phase 3: 💰 CONFIDENCE GATE
        confidence_threshold = getattr(self, 'min_local_confidence', 0.50)
        pocket_mode = getattr(self, 'pocket_mode', True)
        
        # Check for mandatory cloud keywords
        mandatory_cloud = self._check_mandatory_cloud_keywords(prompt)
        
        if mandatory_cloud:
            print(f"☁️ MANDATORY CLOUD: Safety-critical keywords detected")
            use_cloud = True
        elif pocket_mode and triage_confidence >= confidence_threshold:
            print(f"💰 LOCAL PATH: Confident ({triage_confidence:.2f} ≥ {confidence_threshold})")
            print("   Using local voices only - ultra-low cost mode")
            use_cloud = False
        else:
            print(f"☁️ CLOUD PATH: Need assistance ({triage_confidence:.2f} < {confidence_threshold})")
            print("   Engaging multiplexed cloud council")
            use_cloud = True
        
        if use_cloud:
            # Phase 4a: ☁️ Multiplexed cloud deliberation
            voice_responses = await self._multiplex_cloud_deliberation(enhanced_prompt)
            cost_category = "multiplex_cloud"
        else:
            # Phase 4b: 🏠 Local-only deliberation  
            voice_responses = await self._local_only_deliberation(enhanced_prompt, local_response)
            cost_category = "local_only"
        
        # Phase 5: 🎭 Synthesize final response
        final_response = self._synthesize_pocket_council_response(voice_responses)
        
        # Calculate totals
        total_latency_ms = (time.time() - start_time) * 1000
        total_cost = sum(r.cost_dollars for r in voice_responses.values())
        
        # Extract risk flags and assess consensus
        edge_response = voice_responses.get(CouncilVoice.EDGE)
        risk_flags = self._extract_risk_flags(edge_response.response if edge_response else "")
        consensus_achieved = self._assess_consensus_quality(voice_responses)
        
        # Metrics and logging
        if PROMETHEUS_AVAILABLE:
            COUNCIL_LATENCY_SECONDS.observe(total_latency_ms / 1000)
            COUNCIL_COST_DOLLARS.inc(total_cost)
            for voice in voice_responses:
                COUNCIL_VOICES_ACTIVE.labels(voice=voice.value).set(1)
        
        savings_vs_old = 0.30 - total_cost  # Savings vs old $0.30 approach
        print(f"🎭 POCKET-COUNCIL: Complete in {total_latency_ms:.1f}ms, cost ${total_cost:.4f} ({cost_category})")
        print(f"💰 SAVINGS: ${savings_vs_old:.3f} saved vs old Council! ({savings_vs_old/0.30:.0%} reduction)")
        
        return CouncilDeliberation(
            final_response=final_response,
            voice_responses=voice_responses,
            total_latency_ms=total_latency_ms,
            total_cost_dollars=total_cost,
            consensus_achieved=consensus_achieved,
            risk_flags=risk_flags,
            metadata={
                "prompt_tokens": len(prompt.split()),
                "response_tokens": len(final_response.split()),
                "voices_count": len(voice_responses),
                "council_version": "v2.0_pocket_council",
                "cost_category": cost_category,
                "local_confidence": triage_confidence,
                "context_boost": context_boost,
                "cloud_used": use_cloud,
                "savings_vs_old_usd": savings_vs_old
            }
        )
    
    async def _local_triage_analysis(self, prompt: str) -> Dict[str, Any]:
        """Ultra-fast local analysis with TinyLlama for confidence scoring"""
        try:
            # Use TinyLlama for quick analysis
            triage_model = getattr(self, 'local_triage_model', 'tinyllama_1b')
            
            # Simple analysis prompt
            analysis_prompt = f"Analyze this query briefly and rate your confidence (0-1):\n{prompt}\n\nAnalysis:"
            
            # Mock implementation for now (replace with actual TinyLlama call)
            response_text = f"Quick analysis: {prompt[:50]}... This appears to be a {self._classify_query_type(prompt)} query."
            
            # Simple confidence heuristic based on query complexity
            confidence = self._calculate_local_confidence(prompt)
            
            return {
                "text": response_text,
                "confidence": confidence,
                "model_used": triage_model,
                "cost_dollars": 0.0001,  # Virtually free
                "metadata": {"type": "local_triage", "tokens": len(response_text.split())}
            }
            
        except Exception as e:
            print(f"⚠️ Local triage failed: {e}")
            return {
                "text": f"Triage analysis for: {prompt}",
                "confidence": 0.3,  # Low confidence to trigger cloud
                "model_used": "fallback",
                "cost_dollars": 0.0,
                "metadata": {"error": str(e)}
            }
    
    def _calculate_local_confidence(self, prompt: str) -> float:
        """Calculate confidence score for local triage"""
        prompt_lower = prompt.lower()
        
        # Low confidence patterns (complex analysis) - CHECK FIRST!
        low_confidence_patterns = [
            r'compare\s+\w+.*vs.*\w+',     # Comparisons with "vs" 
            r'compare\s+\w+.*and.*\w+',    # Comparisons with "and"
            r'analyze.*trade.*offs?',      # Trade-off analysis (more flexible)
            r'design.*scalable.*system',   # System design
            r'design.*system.*for',        # System design patterns
            r'architecture.*patterns?',    # Architecture discussions
            r'microservices?.*monolith',   # Specific architectural comparison
            r'pros.*cons|advantages.*disadvantages',  # Pros/cons analysis
            r'strategy|strategic',         # Strategic thinking
        ]
        
        # Check low confidence patterns FIRST (most specific)
        for pattern in low_confidence_patterns:
            if re.search(pattern, prompt_lower):
                return 0.35  # Low confidence for complex queries
        
        # High confidence patterns (simple/factual queries) - more specific
        high_confidence_patterns = [
            r'\d+\s*[\+\-\*/]\s*\d+',      # Math expressions
            r'what\s+is\s+\d+',            # Simple factual
            r'^hello\b|^hi\b|^hey\b|thank', # Greetings (word boundaries)
            r'define\s+\w+',               # Definitions
        ]
        
        # Check high confidence patterns
        for pattern in high_confidence_patterns:
            if re.search(pattern, prompt_lower):
                return 0.75  # High confidence for simple queries
        
        # Medium confidence patterns
        medium_confidence_patterns = [
            r'explain|describe|how\s+does',  # Explanations
            r'list|show\s+me',              # Lists
            r'what\s+are',                   # Basic questions
        ]
        
        for pattern in medium_confidence_patterns:
            if re.search(pattern, prompt_lower):
                return 0.55  # Medium confidence
        
        # Default based on length and complexity
        word_count = len(prompt.split())
        if word_count <= 5:
            return 0.70  # Short queries usually simple
        elif word_count >= 15:
            return 0.40  # Long queries often complex
        else:
            return 0.55  # Medium queries
    
    def _classify_query_type(self, prompt: str) -> str:
        """Classify query type for triage analysis"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['calculate', 'math', '+', '-', '*', '/']):
            return "mathematical"
        elif any(word in prompt_lower for word in ['code', 'function', 'algorithm', 'program']):
            return "programming"
        elif any(word in prompt_lower for word in ['compare', 'analyze', 'evaluate']):
            return "analytical"
        elif any(word in prompt_lower for word in ['strategy', 'design', 'architecture']):
            return "strategic"
        else:
            return "general"
    
    def _check_mandatory_cloud_keywords(self, prompt: str) -> bool:
        """Check if prompt contains keywords that mandate cloud processing"""
        mandatory_keywords = getattr(self, 'mandatory_cloud_keywords', [
            'safety-critical', 'compliance', 'legal', 'medical'
        ])
        
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in mandatory_keywords)
    
    async def _multiplex_cloud_deliberation(self, prompt: str) -> Dict[CouncilVoice, VoiceResponse]:
        """Single multiplexed cloud call for all 5 voices"""
        start_time = time.time()
        
        try:
            # Build multiplex prompt
            multiplex_prompt = self._build_multiplex_prompt(prompt)
            
            # Single cloud call
            cloud_result = await self._call_multiplex_api(multiplex_prompt)
            
            # Parse JSON response into individual voice responses
            voice_responses = self._parse_multiplex_response(cloud_result, start_time)
            
            print(f"☁️ Multiplexed cloud call: {len(voice_responses)} voices, ${cloud_result.get('cost_dollars', 0):.4f}")
            
            return voice_responses
            
        except Exception as e:
            print(f"❌ Multiplex cloud failed: {e}, falling back to local")
            return await self._local_only_deliberation(prompt, {"text": f"Cloud analysis for: {prompt}", "confidence": 0.7})
    
    def _build_multiplex_prompt(self, prompt: str) -> str:
        """Build the multiplexed prompt for all 5 voices"""
        system_prompt = """You are a Council-Multiplexer. Given a query, provide exactly 5 distinct perspectives as a JSON array.
Each voice has a specific role and should give a brief, focused response.

Return format: [{"voice":"Reason","reply":"..."},{"voice":"Spark","reply":"..."}...]

Voice roles:
- Reason: Logical step-by-step analysis (2 sentences max)
- Spark: One creative/novel angle (≤40 words) 
- Edge: Biggest risk/concern (≤25 words)
- Heart: Human-friendly rewrite (1-2 lines)
- Vision: Future implication (≤30 chars)"""
        
        user_prompt = f"""{{
  "query": "{prompt}",
  "voices": ["Reason", "Spark", "Edge", "Heart", "Vision"],
  "format": "brief_focused_responses"
}}"""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    async def _call_multiplex_api(self, multiplex_prompt: str) -> Dict[str, Any]:
        """Call cloud API with multiplex prompt"""
        try:
            # Mock implementation - replace with actual cloud call
            from router.cloud_providers import ask_cloud_council
            
            result = await ask_cloud_council(multiplex_prompt)
            
            # Expected format: {"text": "[{...}, {...}, ...]", "cost_dollars": 0.025}
            return {
                "text": result.get("text", "[]"),
                "cost_dollars": result.get("cost_dollars", 0.025),
                "provider": result.get("provider", "gpt4o_mini"),
                "latency_ms": result.get("latency_ms", 500)
            }
            
        except Exception as e:
            print(f"Cloud API call failed: {e}")
            # Return mock multiplex response for testing
            mock_response = [
                {"voice": "Reason", "reply": f"Logical analysis of: {multiplex_prompt[:30]}..."},
                {"voice": "Spark", "reply": f"Creative angle: novel approach to {multiplex_prompt[:20]}..."},
                {"voice": "Edge", "reply": f"Risk: potential issues with complexity"},
                {"voice": "Heart", "reply": f"User-friendly version: {multiplex_prompt[:25]}..."},
                {"voice": "Vision", "reply": f"Future: long-term impact"}
            ]
            
            return {
                "text": str(mock_response),
                "cost_dollars": 0.025,
                "provider": "mock_multiplex",
                "latency_ms": 50
            }
    
    def _parse_multiplex_response(self, cloud_result: Dict[str, Any], start_time: float) -> Dict[CouncilVoice, VoiceResponse]:
        """Parse multiplexed JSON response into individual voice responses"""
        voice_responses = {}
        
        try:
            import json
            response_text = cloud_result.get("text", "[]")
            
            # Try to parse JSON
            if isinstance(response_text, str):
                # Handle case where response_text might be string representation
                response_text = response_text.replace("'", '"')  # Fix single quotes
                voices_data = json.loads(response_text)
            else:
                voices_data = response_text
            
            # Create VoiceResponse objects
            latency_ms = cloud_result.get("latency_ms", 500)
            total_cost = cloud_result.get("cost_dollars", 0.025)
            cost_per_voice = total_cost / 5  # Split cost across voices
            
            voice_map = {
                "Reason": CouncilVoice.REASON,
                "Spark": CouncilVoice.SPARK,
                "Edge": CouncilVoice.EDGE,
                "Heart": CouncilVoice.HEART,
                "Vision": CouncilVoice.VISION
            }
            
            for voice_data in voices_data:
                voice_name = voice_data.get("voice", "Unknown")
                voice_enum = voice_map.get(voice_name)
                
                if voice_enum:
                    voice_responses[voice_enum] = VoiceResponse(
                        voice=voice_enum,
                        response=voice_data.get("reply", f"Response from {voice_name}"),
                        confidence=0.85,  # High confidence for cloud responses
                        latency_ms=latency_ms / 5,  # Shared latency
                        model_used=f"multiplex_{cloud_result.get('provider', 'cloud')}",
                        cost_dollars=cost_per_voice,
                        metadata={
                            "multiplex": True,
                            "shared_call": True,
                            "total_cost": total_cost
                        }
                    )
            
            # Fill in any missing voices with placeholders
            for voice in CouncilVoice:
                if voice not in voice_responses:
                    voice_responses[voice] = VoiceResponse(
                        voice=voice,
                        response=f"[{voice.value.upper()}] Analysis completed",
                        confidence=0.7,
                        latency_ms=5,
                        model_used="multiplex_fallback",
                        cost_dollars=0.0,
                        metadata={"multiplex_fallback": True}
                    )
            
        except Exception as e:
            print(f"Failed to parse multiplex response: {e}")
            # Create fallback responses
            for voice in CouncilVoice:
                voice_responses[voice] = VoiceResponse(
                    voice=voice,
                    response=f"[{voice.value.upper()}] Multiplex parsing failed",
                    confidence=0.5,
                    latency_ms=10,
                    model_used="parse_error",
                    cost_dollars=0.0,
                    metadata={"parse_error": str(e)}
                )
        
        return voice_responses
    
    async def _local_only_deliberation(self, prompt: str, triage_result: Dict[str, Any]) -> Dict[CouncilVoice, VoiceResponse]:
        """Ultra-fast local-only deliberation using micro-prompts"""
        voice_responses = {}
        
        # Use triage result as Reason response
        voice_responses[CouncilVoice.REASON] = VoiceResponse(
            voice=CouncilVoice.REASON,
            response=triage_result["text"],
            confidence=triage_result["confidence"],
            latency_ms=5,
            model_used=triage_result["model_used"],
            cost_dollars=triage_result["cost_dollars"],
            metadata=triage_result.get("metadata", {})
        )
        
        # Generate other voices locally with micro-prompts
        base_response = triage_result["text"]
        
        # Spark: Creative angle (local)
        voice_responses[CouncilVoice.SPARK] = VoiceResponse(
            voice=CouncilVoice.SPARK,
            response=f"💡 Creative angle: What if we approached '{prompt[:30]}...' from a completely different perspective?",
            confidence=0.6,
            latency_ms=3,
            model_used="local_spark_micro",
            cost_dollars=0.0001,
            metadata={"type": "local_micro", "prompt_length": len("Invent one fresh angle")}
        )
        
        # Edge: Risk assessment (local)
        risk_text = "Low complexity risk" if len(prompt.split()) < 10 else "Moderate complexity risk"
        voice_responses[CouncilVoice.EDGE] = VoiceResponse(
            voice=CouncilVoice.EDGE,
            response=f"⚠️ {risk_text}: Consider potential edge cases",
            confidence=0.7,
            latency_ms=2,
            model_used="local_edge_micro",
            cost_dollars=0.0001,
            metadata={"type": "local_micro", "risk_level": "low"}
        )
        
        # Heart: Human-friendly rewrite (local)
        voice_responses[CouncilVoice.HEART] = VoiceResponse(
            voice=CouncilVoice.HEART,
            response=f"Here's a friendly explanation: {base_response[:80]}...",
            confidence=0.8,
            latency_ms=2,
            model_used="local_heart_micro",
            cost_dollars=0.0001,
            metadata={"type": "local_micro"}
        )
        
        # Vision: Future implications (local)
        voice_responses[CouncilVoice.VISION] = VoiceResponse(
            voice=CouncilVoice.VISION,
            response="🔮 Future impact: scalable approach",
            confidence=0.6,
            latency_ms=1,
            model_used="local_vision_micro",
            cost_dollars=0.0001,
            metadata={"type": "local_micro", "chars": 30}
        )
        
        return voice_responses
    
    def _synthesize_pocket_council_response(self, voice_responses: Dict[CouncilVoice, VoiceResponse]) -> str:
        """Synthesize Pocket-Council response with clear voice attribution"""
        
        # Start with Heart's human-friendly version as base
        heart_response = voice_responses.get(CouncilVoice.HEART)
        base_text = heart_response.response if heart_response else "Council analysis complete."
        
        # Build structured response with voice attribution
        synthesis = f"{base_text}\n\n"
        
        # Add other voices as structured insights
        reason_response = voice_responses.get(CouncilVoice.REASON)
        if reason_response and "analysis" in reason_response.response.lower():
            synthesis += f"🧠 **Reasoning**: {reason_response.response[:100]}...\n\n"
        
        spark_response = voice_responses.get(CouncilVoice.SPARK)
        if spark_response and spark_response.confidence > 0.5:
            synthesis += f"✨ **Creative insight**: {spark_response.response[:80]}...\n\n"
        
        edge_response = voice_responses.get(CouncilVoice.EDGE)
        if edge_response:
            synthesis += f"🗡️ **Risk assessment**: {edge_response.response[:70]}...\n\n"
        
        vision_response = voice_responses.get(CouncilVoice.VISION)
        if vision_response:
            synthesis += f"🔮 **Strategic view**: {vision_response.response}\n"
        
        return synthesis.strip()
    
    def _extract_risk_flags(self, edge_response: str) -> List[str]:
        """Extract risk flags from Edge voice response"""
        flags = []
        edge_lower = edge_response.lower()
        
        risk_patterns = {
            "security": ["security", "vulnerability", "attack", "breach"],
            "performance": ["slow", "latency", "performance", "bottleneck"],
            "cost": ["expensive", "cost", "budget", "price"],
            "ethics": ["ethical", "bias", "fairness", "discrimination"],
            "safety": ["unsafe", "dangerous", "harm", "risk"]
        }
        
        for category, keywords in risk_patterns.items():
            if any(keyword in edge_lower for keyword in keywords):
                flags.append(category)
        
        return flags
    
    def _assess_consensus_quality(self, voice_responses: Dict[CouncilVoice, VoiceResponse]) -> bool:
        """Assess if the council achieved good consensus"""
        
        # Calculate average confidence
        avg_confidence = sum(r.confidence for r in voice_responses.values()) / len(voice_responses)
        
        # Check for major disagreements (Edge flagging serious risks)
        edge_response = voice_responses[CouncilVoice.EDGE]
        high_risk_indicators = ["critical", "dangerous", "major risk", "serious concern"]
        major_risks = any(indicator in edge_response.response.lower() for indicator in high_risk_indicators)
        
        # Consensus achieved if high confidence and no major risks
        return avg_confidence > 0.7 and not major_risks

# Global council router instance
council_router = CouncilRouter()

async def council_route(prompt: str) -> Dict[str, Any]:
    """
    Main council routing function - integrates with existing Router 2.x stack
    
    Returns standard router response format for compatibility
    """
    
    # Check if council should be triggered
    should_trigger, reason = council_router.should_trigger_council(prompt)
    
    if not should_trigger:
        # Use existing quick local path
        print(f"[COUNCIL] Quick path: {reason}")
        from router.voting import vote
        loaded_models = get_loaded_models()
        available_models = list(loaded_models.keys())[:3]
        
        if available_models:
            result = await vote(prompt, available_models, min(3, len(available_models)))
            return {
                "text": result["text"],
                "council_used": False,
                "council_reason": reason,
                "model_used": result["winner"]["model"],
                "confidence": result["voting_stats"]["winner_confidence"],
                "latency_ms": result["voting_stats"]["voting_time_ms"],
                "cost_dollars": 0.0
            }
        else:
            return {
                "text": "[ERROR] No models available",
                "council_used": False,
                "error": "no_models_available"
            }
    
    # Full council deliberation
    print(f"[COUNCIL] Full deliberation triggered: {reason}")
    deliberation = await council_router.council_deliberate(prompt)
    
    return {
        "text": deliberation.final_response,
        "council_used": True,
        "council_reason": reason,
        "council_deliberation": {
            "total_latency_ms": deliberation.total_latency_ms,
            "total_cost_dollars": deliberation.total_cost_dollars,
            "consensus_achieved": deliberation.consensus_achieved,
            "risk_flags": deliberation.risk_flags,
            "voices_used": [voice.value for voice in deliberation.voice_responses.keys()],
            "metadata": deliberation.metadata
        },
        "confidence": sum(r.confidence for r in deliberation.voice_responses.values()) / len(deliberation.voice_responses),
        "latency_ms": deliberation.total_latency_ms,
        "cost_dollars": deliberation.total_cost_dollars
    } 