# preference_model/dataset.py
import redis, json, pathlib, random
from collections import defaultdict

def build_preference_pairs():
    """Extract feedback from Redis and build (prompt, choice_a, choice_b, label) tuples"""
    r = redis.Redis(host='redis', port=6379, db=0)
    ROOT = pathlib.Path("/opt/lumina/reward")
    ROOT.mkdir(parents=True, exist_ok=True)
    
    pairs = []
    
    # Get all feedback keys
    feedback_keys = r.keys('feedback:*')
    
    for key in feedback_keys:
        # Extract feedback data with scores
        feedback_data = r.zrange(key, 0, -1, withscores=True)
        
        # Group by prompt to create pairs
        prompt_responses = defaultdict(list)
        
        for response_bytes, score in feedback_data:
            try:
                response = json.loads(response_bytes.decode('utf-8'))
                prompt = response.get('prompt', '')
                choice = response.get('response', '')
                
                prompt_responses[prompt].append({
                    'choice': choice,
                    'score': score
                })
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Create pairs from responses to same prompt
        for prompt, responses in prompt_responses.items():
            if len(responses) >= 2:
                # Sort by score and create pairs
                responses.sort(key=lambda x: x['score'], reverse=True)
                
                for i in range(len(responses) - 1):
                    for j in range(i + 1, len(responses)):
                        higher_choice = responses[i]
                        lower_choice = responses[j]
                        
                        # Only create pair if there's meaningful score difference
                        if higher_choice['score'] - lower_choice['score'] > 0.1:
                            pairs.append({
                                'prompt': prompt,
                                'choice_a': higher_choice['choice'],
                                'choice_b': lower_choice['choice'], 
                                'label': 0  # choice_a is preferred (higher score)
                            })
                            
                            # Also add reverse for balance
                            pairs.append({
                                'prompt': prompt,
                                'choice_a': lower_choice['choice'],
                                'choice_b': higher_choice['choice'],
                                'label': 1  # choice_b is preferred (was originally higher)
                            })
    
    # Shuffle and write to JSONL
    random.shuffle(pairs)
    
    with open(ROOT/"pairs.jsonl", 'w') as f:
        for pair in pairs:
            f.write(json.dumps(pair) + '\n')
    
    print(f"Built {len(pairs)} preference pairs from {len(feedback_keys)} feedback keys")
    return len(pairs)

if __name__ == "__main__":
    build_preference_pairs() 