#!/usr/bin/env python3
"""
Terminal Chat Demo for AutoGen Council v3.0.0 
Showcases the Think-Act-Reflect consciousness system with stub detection
"""

import asyncio
import time
import sys
import json
from typing import Dict, Any, List
from pathlib import Path
import requests

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from router_cascade import RouterCascade
    LOCAL_MODE = True
except ImportError:
    LOCAL_MODE = False
    print("⚠️ Running in API mode - make sure server is running on localhost:8000")

class TerminalChatDemo:
    """Interactive terminal chat demonstrating the consciousness system"""
    
    def __init__(self):
        self.session_id = f"terminal_demo_{int(time.time())}"
        self.message_count = 0
        self.chat_history = []
        
        if LOCAL_MODE:
            self.router = RouterCascade()
        else:
            self.api_base = "http://localhost:8000"
            
        # Demo test cases to showcase capabilities
        self.demo_cases = [
            {
                "prompt": "What is 25 * 17?",
                "expected": "math specialist with quick calculation",
                "type": "math_basic"
            },
            {
                "prompt": "Write a Python function to calculate factorial",
                "expected": "code specialist with working function",
                "type": "code_generation"
            },
            {
                "prompt": "def custom_function(): pass",
                "expected": "CloudRetry due to stub detection",
                "type": "stub_template"
            },
            {
                "prompt": "Hello! I can help you with anything",
                "expected": "CloudRetry due to generic AI response",
                "type": "stub_generic"
            },
            {
                "prompt": "Explain quantum computing briefly",
                "expected": "knowledge specialist with concise explanation",
                "type": "knowledge"
            },
            {
                "prompt": "If all cats are animals and some animals are dogs, what can we conclude?",
                "expected": "logic specialist with reasoning",
                "type": "logic"
            }
        ]
    
    def print_banner(self):
        """Print the demo banner"""
        print("=" * 80)
        print("🚀 AUTOGEN COUNCIL v3.0.0 - TERMINAL CHAT DEMO")
        print("=" * 80)
        print("🧠 Think-Act-Reflect Consciousness System")
        print("🛡️ Enhanced Stub Detection & CloudRetry")
        print("⚡ Agent-0 First Architecture (≤250ms)")
        print("🎯 5 Specialist Democracy with Consensus Fusion")
        print("💭 Reflection Memory System")
        print()
        if LOCAL_MODE:
            print("🔧 Mode: Local RouterCascade")
        else:
            print("🌐 Mode: API Client to localhost:8000")
        print("💬 Type 'demo' for guided tour, 'exit' to quit")
        print("=" * 80)
    
    async def send_message_local(self, prompt: str) -> Dict[str, Any]:
        """Send message using local RouterCascade"""
        try:
            result = await self.router.route_query(prompt)
            return result
        except Exception as e:
            return {
                "text": f"Local routing error: {str(e)}",
                "specialist": "error",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def send_message_api(self, prompt: str) -> Dict[str, Any]:
        """Send message using API client"""
        try:
            response = requests.post(
                f"{self.api_base}/vote",
                json={
                    "prompt": prompt,
                    "session_id": self.session_id,
                    "use_context": True
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "text": f"API error: {response.status_code}",
                    "specialist": "api_error",
                    "confidence": 0.0,
                    "error": response.text
                }
        except Exception as e:
            return {
                "text": f"Connection error: {str(e)}",
                "specialist": "connection_error", 
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def send_message(self, prompt: str) -> Dict[str, Any]:
        """Send message using appropriate method"""
        if LOCAL_MODE:
            return await self.send_message_local(prompt)
        else:
            return await self.send_message_api(prompt)
    
    def display_response(self, response: Dict[str, Any], prompt: str):
        """Display formatted response"""
        self.message_count += 1
        
        print(f"\n📤 [{self.message_count}] User:")
        print(f"   {prompt}")
        
        print(f"\n🤖 [{self.message_count}] Assistant:")
        text = response.get("text", "No response")
        specialist = response.get("specialist", "unknown")
        confidence = response.get("confidence", 0.0)
        
        # Wrap long text
        if len(text) > 70:
            words = text.split()
            lines = []
            current_line = "   "
            for word in words:
                if len(current_line + word) > 70:
                    lines.append(current_line.rstrip())
                    current_line = "   " + word + " "
                else:
                    current_line += word + " "
            lines.append(current_line.rstrip())
            print("\n".join(lines))
        else:
            print(f"   {text}")
        
        # Show metadata
        print(f"\n📊 Meta:")
        print(f"   🎯 Specialist: {specialist}")
        print(f"   📈 Confidence: {confidence:.2f}")
        
        if "latency_ms" in response:
            latency = response["latency_ms"]
            print(f"   ⏱️ Latency: {latency:.0f}ms")
        
        if "voting_stats" in response:
            stats = response["voting_stats"]
            if "specialists_tried" in stats:
                tried = stats["specialists_tried"]
                print(f"   👥 Specialists: {', '.join(tried[:3])}{'...' if len(tried) > 3 else ''}")
            
            if "agent0_shortcut" in stats:
                print(f"   🚀 Agent-0 Shortcut: ✅")
            
            if "consensus_fusion" in stats:
                print(f"   🤝 Consensus Fusion: ✅")
        
        # Check for CloudRetry or stub detection
        if "CloudRetry" in text or "stub" in text.lower():
            print(f"   🛡️ Stub Detection: ✅ (CloudRetry triggered)")
        
        if "error" in response:
            print(f"   ❌ Error: {response['error']}")
        
        print()
    
    async def run_demo_cases(self):
        """Run through the demo test cases"""
        print("🎮 GUIDED DEMO - Testing Core Capabilities")
        print("=" * 60)
        
        for i, case in enumerate(self.demo_cases, 1):
            print(f"\n🧪 Test Case {i}/{len(self.demo_cases)}: {case['type']}")
            print(f"Expected: {case['expected']}")
            print("-" * 50)
            
            response = await self.send_message(case['prompt'])
            self.display_response(response, case['prompt'])
            
            # Brief pause between test cases
            await asyncio.sleep(1)
        
        print("🎉 Demo Complete! Try your own questions or type 'exit' to quit.")
    
    async def interactive_chat(self):
        """Run interactive chat loop"""
        while True:
            try:
                user_input = input("💬 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Thanks for trying AutoGen Council v3.0.0!")
                    break
                
                if user_input.lower() == 'demo':
                    await self.run_demo_cases()
                    continue
                
                if user_input.lower() == 'clear':
                    print("\n" * 50)  # Clear screen
                    self.print_banner()
                    continue
                
                if user_input.lower() == 'stats':
                    await self.show_stats()
                    continue
                
                if not user_input:
                    continue
                
                # Send message and display response
                print("🔄 Processing...")
                start_time = time.time()
                
                response = await self.send_message(user_input)
                
                wall_time = (time.time() - start_time) * 1000
                print(f"🕐 Wall time: {wall_time:.0f}ms")
                
                self.display_response(response, user_input)
                
                # Store in history
                self.chat_history.append({
                    "prompt": user_input,
                    "response": response,
                    "timestamp": time.time()
                })
                
            except KeyboardInterrupt:
                print("\n👋 Thanks for trying AutoGen Council v3.0.0!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue
    
    async def show_stats(self):
        """Show session statistics"""
        print("\n📊 SESSION STATISTICS")
        print("=" * 40)
        print(f"💬 Messages: {len(self.chat_history)}")
        print(f"🆔 Session: {self.session_id}")
        print(f"🕐 Duration: {time.time() - float(self.session_id.split('_')[-1]):.0f}s")
        
        if self.chat_history:
            # Calculate average latency
            latencies = [r['response'].get('latency_ms', 0) for r in self.chat_history]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            print(f"⏱️ Avg Latency: {avg_latency:.0f}ms")
            
            # Count specialists used
            specialists = [r['response'].get('specialist', 'unknown') for r in self.chat_history]
            specialist_counts = {}
            for spec in specialists:
                specialist_counts[spec] = specialist_counts.get(spec, 0) + 1
            
            print("👥 Specialists Used:")
            for spec, count in sorted(specialist_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {spec}: {count}x")
        
        print()
    
    async def run(self):
        """Main demo runner"""
        self.print_banner()
        await self.interactive_chat()

async def main():
    """Main entry point"""
    demo = TerminalChatDemo()
    await demo.run()

if __name__ == "__main__":
    print("🚀 Starting AutoGen Council Terminal Demo...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo terminated by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1) 