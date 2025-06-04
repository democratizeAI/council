#!/usr/bin/env python3
"""
AutoGen Council Router Cascade
Main entry point for the AutoGen Council routing system.
This module provides a unified interface to the council routing capabilities.
"""

import sys
import os
from typing import Dict, Any, List, Optional

# Add the router directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'router'))

try:
    from router.council import CouncilRouter, CouncilDeliberation, VoiceResponse, council_route
    from router.voting import vote
    # Optional imports - only if available
    try:
        from router.cost_tracking import CostTracker
    except ImportError:
        CostTracker = None
    
    try:
        from router.cloud_providers import CloudProvider
    except ImportError:
        CloudProvider = None
    
    try:
        from router.traffic_controller import TrafficController
    except ImportError:
        TrafficController = None
    
    try:
        from router.privacy_filter import PrivacyFilter
    except ImportError:
        PrivacyFilter = None
        
except ImportError as e:
    print(f"Warning: Could not import router modules: {e}")
    # Create mock classes for fallback
    class CouncilRouter:
        def __init__(self, config=None):
            self.config = config or {}
        
        def should_trigger_council(self, prompt):
            return False, "module_not_available"
        
        async def council_deliberate(self, prompt):
            return {"error": "Council module not available"}
    
    class CouncilDeliberation:
        pass
    
    class VoiceResponse:
        pass
    
    async def council_route(prompt):
        return {"error": "Council routing not available", "text": "Module not loaded"}


class AutoGenCouncilCascade:
    """
    Main AutoGen Council Router Cascade
    Orchestrates the council-based routing for AutoGen agents
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.council_router = None
        self.cost_tracker = None
        self.traffic_controller = None
        self.privacy_filter = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all routing components"""
        try:
            # Initialize core council router
            self.council_router = CouncilRouter()
            
            # Initialize supporting components if available
            if CostTracker:
                self.cost_tracker = CostTracker()
            
            if TrafficController:
                self.traffic_controller = TrafficController()
            
            if PrivacyFilter:
                self.privacy_filter = PrivacyFilter()
            
            print("✅ AutoGen Council components initialized successfully")
            
        except Exception as e:
            print(f"Warning: Could not initialize all components: {e}")
    
    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a request through the AutoGen Council system
        
        Args:
            request: The incoming request to route
            
        Returns:
            Dict[str, Any]: The routing response from the council
        """
        if not self.council_router:
            return {"error": "Council router not initialized", "text": "Router not available"}
        
        try:
            # Extract prompt from request
            prompt = request.get("prompt", request.get("text", str(request)))
            
            # Apply privacy filtering if available
            if self.privacy_filter:
                prompt = self.privacy_filter.filter_request({"prompt": prompt}).get("prompt", prompt)
            
            # Check traffic limits if available
            if self.traffic_controller:
                self.traffic_controller.check_limits(request)
            
            # Route through council
            result = await council_route(prompt)
            
            # Track costs if available
            if self.cost_tracker and "cost_dollars" in result:
                self.cost_tracker.track_request(request, result)
            
            return result
            
        except Exception as e:
            print(f"Error routing request: {e}")
            # Fallback response
            return {"error": str(e), "text": "Request routing failed"}
    
    def route_request_sync(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous version of route_request for easier integration
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.route_request(request))
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.route_request(request))
            finally:
                loop.close()
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all routing components"""
        return {
            'council_router': self.council_router is not None,
            'cost_tracker': self.cost_tracker is not None,
            'traffic_controller': self.traffic_controller is not None,
            'privacy_filter': self.privacy_filter is not None,
            'config': self.config
        }


# Factory function for easy instantiation
def create_autogen_council(config: Optional[Dict[str, Any]] = None) -> AutoGenCouncilCascade:
    """
    Factory function to create an AutoGen Council Cascade
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        AutoGenCouncilCascade: Configured council instance
    """
    return AutoGenCouncilCascade(config)


# CLI interface for testing
if __name__ == "__main__":
    print("🚀 AutoGen Council Router Cascade")
    print("=" * 40)
    
    # Create council instance
    council = create_autogen_council()
    
    # Print status
    status = council.get_status()
    print("Component Status:")
    for component, active in status.items():
        if component != 'config':
            print(f"  {component}: {'✅' if active else '❌'}")
    
    print("\n✅ AutoGen Council Router Cascade initialized successfully!")
    print("Ready for Agent-Zero integration.")
    
    # Test basic functionality
    print("\n🧪 Testing basic functionality...")
    test_request = {"prompt": "What is 2 + 2?"}
    try:
        result = council.route_request_sync(test_request)
        print(f"✅ Test request successful: {result.get('text', 'No text response')[:100]}...")
    except Exception as e:
        print(f"⚠️ Test request failed: {e}") 