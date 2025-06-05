#!/usr/bin/env python3
"""
🧠 PHASE B: Conversation Summarizer
==================================

Lightweight summarizer for maintaining context without token bloat.
Uses BART-large-cnn-samsum for conversation-aware summarization.
"""

import logging
import time
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ConversationSummary:
    """Conversation summary with metadata"""
    summary_text: str
    token_count: int
    original_length: int
    compression_ratio: float
    timestamp: float

class ConversationSummarizer:
    """Efficient conversation summarizer with caching"""
    
    def __init__(self):
        self.pipeline = None
        self.ready = False
        self.cache = {}  # Simple LRU cache
        self.max_cache_size = 100
        
    def _load_model(self):
        """Load BART summarization model on first use"""
        if self.pipeline is not None:
            return
            
        try:
            from transformers import pipeline
            
            logger.info("🧠 Loading BART summarizer for conversations...")
            
            # Use conversation-optimized BART model
            self.pipeline = pipeline(
                "summarization",
                model="philschmid/bart-large-cnn-samsum",  # Conversation-tuned
                device=0 if self._has_cuda() else -1,  # GPU if available
                max_length=80,   # Hard limit for Phase B
                min_length=30,   # Ensure substantial summaries
                do_sample=False, # Deterministic for caching
                truncation=True
            )
            
            self.ready = True
            logger.info("✅ BART summarizer ready")
            
        except ImportError:
            logger.warning("⚠️ Transformers not available - using fallback summarizer")
            self.ready = False
        except Exception as e:
            logger.error(f"❌ Summarizer loading failed: {e}")
            self.ready = False
    
    def _has_cuda(self) -> bool:
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _simple_truncate(self, text: str, max_tokens: int = 80) -> str:
        """Fallback: simple truncation when BART unavailable"""
        words = text.split()
        if len(words) <= max_tokens:
            return text
        return " ".join(words[:max_tokens]) + "..."
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()[:16]
    
    def _manage_cache(self):
        """Keep cache size under limit"""
        if len(self.cache) > self.max_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self.cache.keys())[:10]
            for key in oldest_keys:
                del self.cache[key]
    
    def summarize_conversation(self, conversation_text: str, max_tokens: int = 80) -> ConversationSummary:
        """
        Summarize conversation text to max_tokens limit
        
        Args:
            conversation_text: Full conversation history
            max_tokens: Maximum tokens in summary (default 80)
            
        Returns:
            ConversationSummary with compressed context
        """
        start_time = time.time()
        original_length = len(conversation_text.split())
        
        # Check cache first
        cache_key = self._get_cache_key(conversation_text)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            logger.debug(f"🧠 Cache hit for conversation summary")
            return cached
        
        # Load model if needed
        if not self.ready:
            self._load_model()
        
        # Generate summary
        if self.ready and self.pipeline:
            try:
                # Prepare conversation for BART
                # Format: "User: ... Assistant: ..." for conversation model
                formatted_text = conversation_text
                if len(formatted_text) > 1024:  # Truncate very long conversations
                    formatted_text = formatted_text[-1024:]
                
                # Generate summary with BART
                result = self.pipeline(formatted_text)
                summary_text = result[0]["summary_text"]
                
                # Ensure we don't exceed token limit
                summary_words = summary_text.split()
                if len(summary_words) > max_tokens:
                    summary_text = " ".join(summary_words[:max_tokens]) + "..."
                
                logger.debug(f"🧠 BART summary: {original_length} → {len(summary_words)} words")
                
            except Exception as e:
                logger.warning(f"🧠 BART summarization failed: {e}, using truncation")
                summary_text = self._simple_truncate(conversation_text, max_tokens)
        else:
            # Fallback to simple truncation
            summary_text = self._simple_truncate(conversation_text, max_tokens)
        
        # Create summary object
        summary = ConversationSummary(
            summary_text=summary_text,
            token_count=len(summary_text.split()),
            original_length=original_length,
            compression_ratio=original_length / len(summary_text.split()) if len(summary_text.split()) > 0 else 1.0,
            timestamp=time.time()
        )
        
        # Cache the result
        self.cache[cache_key] = summary
        self._manage_cache()
        
        logger.debug(f"🧠 Conversation summarized: {original_length} → {summary.token_count} tokens "
                    f"(compression: {summary.compression_ratio:.1f}x)")
        
        return summary
    
    def update_session_summary(self, session_id: str, user_msg: str, assistant_msg: str) -> Optional[str]:
        """
        Update session summary with new conversation turn
        
        Args:
            session_id: Session identifier
            user_msg: User message
            assistant_msg: Assistant response
            
        Returns:
            Updated session summary or None if failed
        """
        try:
            # Try to read previous context from scratchpad
            try:
                from common.scratchpad import read as sp_read, write as sp_write
                
                # Get recent conversation history
                prev_entries = sp_read(session_id, limit=3)
                prev_context = "\n".join([entry.content for entry in prev_entries])
                
            except ImportError:
                logger.debug("🧠 Scratchpad not available - using in-memory summary")
                prev_context = ""
            
            # Build conversation text
            conversation_parts = []
            if prev_context:
                conversation_parts.append(prev_context)
            conversation_parts.append(f"User: {user_msg}")
            conversation_parts.append(f"Assistant: {assistant_msg}")
            
            full_conversation = "\n".join(conversation_parts)
            
            # Generate summary
            summary = self.summarize_conversation(full_conversation, max_tokens=80)
            
            # Store summary back to scratchpad if available
            try:
                sp_write(
                    session_id, 
                    "conversation_summary", 
                    summary.summary_text,
                    tags=["summary", "conversation"],
                    entry_type="summary",
                    metadata={
                        "compression_ratio": summary.compression_ratio,
                        "original_tokens": summary.original_length,
                        "summary_tokens": summary.token_count
                    }
                )
                logger.debug(f"🧠 Session summary updated for {session_id}")
            except:
                pass  # Graceful degradation if scratchpad unavailable
            
            return summary.summary_text
            
        except Exception as e:
            logger.error(f"🧠 Session summary update failed: {e}")
            return None

# Global summarizer instance
SUMMARIZER = ConversationSummarizer()

def summarize_text(text: str, max_tokens: int = 80) -> str:
    """Convenience function for quick text summarization"""
    summary = SUMMARIZER.summarize_conversation(text, max_tokens)
    return summary.summary_text

def update_session_context(session_id: str, user_msg: str, assistant_msg: str) -> Optional[str]:
    """Convenience function for session context updates"""
    return SUMMARIZER.update_session_summary(session_id, user_msg, assistant_msg) 