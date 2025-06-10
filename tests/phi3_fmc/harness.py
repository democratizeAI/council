import os, pytest, yaml, httpx
COUNCIL = os.getenv("COUNCIL_URL", "http://localhost:9010")

def phi3(text):
    r = httpx.post(f"{COUNCIL}/orchestrate", 
                   json={"prompt": text, "temperature": 0.7, "max_tokens": 300, "flags": []}, 
                   timeout=45)
    r.raise_for_status()
    return r.json()["response"]

def load_case(path): return yaml.safe_load(open(path))

@pytest.mark.parametrize("case", [
    "test_ambiguous_goal.yaml",
    "test_critical_alert.yaml",
    "test_conflicting_directives.yaml"])
def test_phi3_awareness(case):
    data = load_case(f"tests/phi3_fmc/{case}")
    if "prompt" in data:         # Scenario 1
        out = phi3(data["prompt"])
        expect = data["expect"]
        assert expect["epic_title"] in out
        assert out.count("Task-") >= expect["subtasks"]
        assert expect["owner"] in out
    elif "alert" in data:        # Scenario 2
        out = phi3(data["alert"])
        assert "rollback_lora.sh" in out
        assert "PRIORITY: CRITICAL" in out.upper()
        assert "high-priority ticket" in out.lower()
    else:                        # Scenario 3
        phi3(data["cmd_1"])
        out = phi3(data["cmd_2"])
        assert "accuracy" in out.lower() and "INT2" in out 