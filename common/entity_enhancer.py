#!/usr/bin/env python3
"""
🧠 PHASE B: Named-Entity & Coreference Enhancer
==============================================

Optional enhancement for richer context using spaCy NLP.
Adds entity recognition and coreference resolution.
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EntityInfo:
    """Named entity information"""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0

@dataclass 
class EnhancedContext:
    """Enhanced context with entities and coreferences"""
    entities: List[EntityInfo]
    entity_summary: str
    original_text: str
    enhanced_prompt: str

class EntityEnhancer:
    """Named-entity and coreference processor"""
    
    def __init__(self):
        self.nlp = None
        self.ready = False
        
    def _load_spacy(self):
        """Load spaCy model on first use"""
        if self.nlp is not None:
            return
            
        try:
            import spacy
            
            logger.info("🧠 Loading spaCy for entity enhancement...")
            
            # Try different spaCy models in order of preference
            models_to_try = [
                "en_core_web_sm",    # Standard English model
                "en_core_web_md",    # Medium model with vectors
                "en_core_web_lg",    # Large model (if available)
            ]
            
            for model_name in models_to_try:
                try:
                    self.nlp = spacy.load(model_name)
                    logger.info(f"✅ Loaded spaCy model: {model_name}")
                    self.ready = True
                    return
                except OSError:
                    continue
            
            # If no models found, try to download en_core_web_sm
            logger.info("🔧 No spaCy models found, attempting to download en_core_web_sm...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], 
                         capture_output=True, check=False)
            
            # Try loading again
            self.nlp = spacy.load("en_core_web_sm")
            self.ready = True
            logger.info("✅ Downloaded and loaded en_core_web_sm")
            
        except Exception as e:
            logger.warning(f"⚠️ spaCy loading failed: {e} - entity enhancement disabled")
            self.ready = False
    
    def extract_entities(self, text: str) -> List[EntityInfo]:
        """Extract named entities from text"""
        if not self.ready:
            self._load_spacy()
        
        if not self.ready or not self.nlp:
            return []
        
        try:
            doc = self.nlp(text)
            entities = []
            
            for ent in doc.ents:
                # Filter for interesting entity types
                if ent.label_ in {"PERSON", "ORG", "GPE", "EVENT", "PRODUCT", "WORK_OF_ART", 
                                "LAW", "LANGUAGE", "DATE", "TIME", "MONEY", "QUANTITY"}:
                    entities.append(EntityInfo(
                        text=ent.text,
                        label=ent.label_,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=1.0  # spaCy doesn't provide confidence scores
                    ))
            
            return entities
            
        except Exception as e:
            logger.debug(f"🧠 Entity extraction failed: {e}")
            return []
    
    def _format_entity_summary(self, entities: List[EntityInfo]) -> str:
        """Create compact entity summary"""
        if not entities:
            return ""
        
        # Group entities by type
        entity_groups = {}
        for entity in entities:
            if entity.label not in entity_groups:
                entity_groups[entity.label] = []
            entity_groups[entity.label].append(entity.text)
        
        # Create compact summary
        parts = []
        for label, texts in entity_groups.items():
            # Remove duplicates and limit to 3 per type
            unique_texts = list(dict.fromkeys(texts))[:3]
            if unique_texts:
                parts.append(f"{label}: {', '.join(unique_texts)}")
        
        return "; ".join(parts)
    
    def enhance_prompt(self, user_message: str, base_prompt: str = "") -> EnhancedContext:
        """
        Enhance prompt with entity information
        
        Args:
            user_message: User's input message
            base_prompt: Base prompt to enhance
            
        Returns:
            EnhancedContext with entity information
        """
        # Extract entities
        entities = self.extract_entities(user_message)
        entity_summary = self._format_entity_summary(entities)
        
        # Build enhanced prompt
        if entity_summary and len(entity_summary) < 200:  # Keep entity info concise
            enhanced_prompt = f"[entities: {entity_summary}]\n{base_prompt}"
        else:
            enhanced_prompt = base_prompt
        
        return EnhancedContext(
            entities=entities,
            entity_summary=entity_summary,
            original_text=user_message,
            enhanced_prompt=enhanced_prompt
        )
    
    def resolve_coreferences(self, text: str) -> str:
        """
        Simple coreference resolution (basic pronoun replacement)
        
        Note: Full coreference resolution requires specialized models.
        This provides basic pronoun context enhancement.
        """
        if not self.ready:
            self._load_spacy()
        
        if not self.ready or not self.nlp:
            return text
        
        try:
            doc = self.nlp(text)
            
            # Simple heuristic: find recent nouns for pronoun replacement context
            entities_and_nouns = []
            for token in doc:
                if token.ent_type_ in {"PERSON", "ORG"} or (token.pos_ == "NOUN" and not token.is_stop):
                    entities_and_nouns.append(token.text)
            
            # If we have context and pronouns, add a note
            pronouns = [token.text for token in doc if token.pos_ == "PRON"]
            
            if entities_and_nouns and pronouns:
                context_note = f" [context: {', '.join(entities_and_nouns[-3:])}]"
                return text + context_note
            
            return text
            
        except Exception as e:
            logger.debug(f"🧠 Coreference resolution failed: {e}")
            return text

# Global enhancer instance
ENHANCER = EntityEnhancer()

def enhance_user_prompt(user_message: str, base_prompt: str = "") -> str:
    """
    Convenience function for prompt enhancement
    
    Args:
        user_message: User's input
        base_prompt: Base prompt to enhance
        
    Returns:
        Enhanced prompt with entity information
    """
    try:
        enhanced = ENHANCER.enhance_prompt(user_message, base_prompt)
        return enhanced.enhanced_prompt
    except Exception as e:
        logger.debug(f"🧠 Prompt enhancement failed: {e}")
        return base_prompt

def extract_entities_from_text(text: str) -> List[Dict[str, str]]:
    """
    Convenience function for entity extraction
    
    Returns:
        List of entity dictionaries with 'text' and 'label' keys
    """
    try:
        entities = ENHANCER.extract_entities(text)
        return [{"text": e.text, "label": e.label} for e in entities]
    except Exception as e:
        logger.debug(f"🧠 Entity extraction failed: {e}")
        return [] 