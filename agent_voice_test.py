#!/usr/bin/env python3
"""
agent_voice_test.py - Test every agent's voice and show current dialogue capability
Based on the agent roadmap provided by the user
"""
import requests
import json
import subprocess
from datetime import datetime

def test_agent(name, test_func, description):
    """Test an agent and return status"""
    try:
        result = test_func()
        print(f"✅ {name}: {description}")
        if isinstance(result, dict):
            print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
        else:
            print(f"   Response: {str(result)[:200]}...")
        return True
    except Exception as e:
        print(f"❌ {name}: {description}")
        print(f"   Error: {str(e)[:200]}...")
        return False

def test_council():
    """Test Council (Opus-Architect + Council deliberation)"""
    response = requests.post(
        "http://localhost:9000/orchestrate",
        json={"prompt": "Quick status check", "route": ["gpt-4o-mini"]},
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def test_council_health():
    """Test Council health endpoint"""
    response = requests.get("http://localhost:9000/health", timeout=5)
    response.raise_for_status()
    return response.json()

def test_tinyllama():
    """Test TinyLlama direct"""
    response = requests.get("http://localhost:8005/health", timeout=5)
    response.raise_for_status()
    return response.json()

def test_builder_tickets():
    """Test Builder-swarm tickets"""
    response = requests.get("http://localhost:8005/tickets/B-01", timeout=5)
    response.raise_for_status()
    return response.json()

def test_gemini():
    """Test Gemini health"""
    response = requests.get("http://localhost:8002/health", timeout=5)
    response.raise_for_status()
    return response.json()

def test_prometheus():
    """Test Prometheus metrics"""
    response = requests.get("http://localhost:9090/api/v1/query?query=up", timeout=5)
    response.raise_for_status()
    return response.json()

def test_ledger():
    """Test GateKeeper via git log"""
    result = subprocess.run(
        ["git", "log", "-1", "--oneline", "docs/ledger/"],
        capture_output=True, text=True, timeout=5
    )
    if result.returncode == 0:
        return {"latest_commit": result.stdout.strip()}
    else:
        raise Exception(f"Git failed: {result.stderr}")

def main():
    print("🎭 AGENT VOICE TEST - Testing All Council Members")
    print("=" * 60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()

    agents = [
        ("Council API Health", test_council_health, "Basic health check"),
        ("Council Orchestrate", test_council, "Full orchestration with Opus-Architect"),
        ("TinyLlama", test_tinyllama, "Direct LLM service"),
        ("Builder Tickets", test_builder_tickets, "Builder-swarm ticket API"),
        ("Gemini Service", test_gemini, "Auditor service health"),
        ("Prometheus", test_prometheus, "Metrics and monitoring"),
        ("GateKeeper (Ledger)", test_ledger, "Git-based ledger commits"),
    ]

    results = {}
    for name, test_func, description in agents:
        results[name] = test_agent(name, test_func, description)
        print()

    print("📊 SUMMARY")
    print("=" * 60)
    working = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Agents responding: {working}/{total}")
    
    if working >= 3:
        print("🎉 Sufficient agents online for basic Council conversations!")
    else:
        print("⚠️  Need more agents online for full Council capability")

    print("\n🔧 TO BRING SILENT AGENTS ONLINE:")
    if not results.get("Builder Tickets"):
        print("- Builder: Endpoint exists but needs ledger integration")
    if not results.get("Prometheus"):
        print("- Prometheus: Fix config restart loop")
    if not results.get("Gemini Service"):
        print("- Gemini: Add /audit endpoint for autonomous reporting")

if __name__ == "__main__":
    main() 