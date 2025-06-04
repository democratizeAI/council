import json

def get_model_config():
    return {
        "model": "mistral-7b-instruct",
        "context_window": 8192
    }

def get_alternate_model():
    return {
        "model": "llama2-70b-chat",
        "context_window": 4096
    }

def get_fallback_model():
    return {
        "model": "mixtral-8x7b",
        "context_window": 32768
    } 