#!/usr/bin/env python3
"""
Create Titanic Gauntlet Dataset
380 prompts across 6 domains with proper distribution
"""

import json
import os

def create_titanic_dataset():
    """Create the 380-prompt Titanic Gauntlet dataset"""
    
    # Domain configuration from the YAML - adjusted to total 380
    domains = {
        "math": {"items": 200, "weight": 0.30},
        "reasoning": {"items": 70, "weight": 0.25},  # Increased from 50
        "coding": {"items": 40, "weight": 0.20},    # Increased from 25
        "science": {"items": 35, "weight": 0.15},   # Increased from 30
        "planning": {"items": 20, "weight": 0.05},  # Decreased from 25
        "writing": {"items": 15, "weight": 0.05}    # Decreased from 25
    }
    
    dataset = []
    item_id = 0
    
    # Math domain prompts (200 items, 30% weight)
    math_prompts = [
        "Calculate 2 + 2 and show your work",
        "What is 15% of 240?",
        "Solve for x: 3x + 7 = 22",
        "Find the area of a circle with radius 5 cm",
        "What is the factorial of 6?",
        "Calculate the square root of 144",
        "What is 8! (8 factorial)?",
        "Solve: 2x² - 8x + 6 = 0",
        "Find the derivative of f(x) = x³ + 2x² - 5x + 1",
        "What is log₂(64)?",
        "Calculate the integral of 2x dx from 0 to 3",
        "Find the slope of the line passing through (2,5) and (8,17)",
        "What is the sum of the first 10 prime numbers?",
        "Calculate 3.7 × 8.9 - 2.1",
        "What is 25% of 80% of 160?",
        "Solve the system: x + y = 10, 2x - y = 5",
        "Find the perimeter of a rectangle with length 12 and width 8",
        "What is the volume of a sphere with radius 3?",
        "Calculate (5!)/(3! × 2!)",
        "What is the GCD of 48 and 18?"
    ]
    
    # Generate 200 math prompts by cycling and varying
    for i in range(200):
        base_prompt = math_prompts[i % len(math_prompts)]
        if i >= len(math_prompts):
            # Add variations for subsequent cycles
            variations = [
                f"Step by step: {base_prompt}",
                f"Explain and solve: {base_prompt}",
                f"Show your reasoning: {base_prompt}",
                base_prompt.replace("Calculate", "Compute"),
                base_prompt.replace("Find", "Determine"),
                base_prompt.replace("What is", "Calculate"),
                base_prompt.replace("Solve", "Find the solution to"),
                f"Using mathematical principles, {base_prompt.lower()}",
                f"Work through this problem: {base_prompt}",
                f"Provide a detailed solution: {base_prompt}"
            ]
            base_prompt = variations[i % len(variations)]
        
        dataset.append({
            "id": item_id,
            "prompt": base_prompt,
            "domain": "math",
            "scoring_method": "exact_numeric",
            "weight": 0.30,
            "expected_tokens": 50
        })
        item_id += 1
    
    # Reasoning domain prompts (70 items, 25% weight)
    reasoning_prompts = [
        "If all birds can fly and penguins are birds, why can't penguins fly? Explain this logical puzzle.",
        "You have two coins that add up to 30 cents. One is not a nickel. What are the two coins?",
        "A man lives on the 20th floor. Every morning he takes the elevator down. When he comes home, he takes the elevator to the 10th floor and walks the rest. Why?",
        "Three boxes contain apples and oranges. One contains only apples, one only oranges, one both. All labels are wrong. You can pick one fruit from one box. How do you label them correctly?",
        "If you have 3 switches and 3 light bulbs in another room, how can you determine which switch controls which bulb with only one trip to the room?",
        "A woman has two children. One is a boy. What's the probability the other is also a boy?",
        "You're in a room with 3 doors. Behind one is a car, behind the others are goats. You pick door 1. The host opens door 3 (goat). Should you switch to door 2?",
        "Five pirates have 100 gold coins. They vote on distribution. If majority disagrees, the proposer is thrown overboard. What should the first pirate propose?",
        "A snail climbs a 10-foot wall. Each day it climbs 3 feet, each night it slides down 2 feet. How many days to reach the top?",
        "Two trains approach each other at 60 mph each, 120 miles apart. A fly flies back and forth between them at 80 mph. How far does the fly travel?"
    ]
    
    # Generate 70 reasoning prompts
    for i in range(70):
        if i < len(reasoning_prompts):
            prompt = reasoning_prompts[i]
        else:
            prompt = f"Analyze this complex scenario step by step: {reasoning_prompts[i % len(reasoning_prompts)]}"
        
        dataset.append({
            "id": item_id,
            "prompt": prompt,
            "domain": "reasoning", 
            "scoring_method": "exact_match",
            "weight": 0.25,
            "expected_tokens": 150
        })
        item_id += 1
    
    # Coding domain prompts (40 items, 20% weight)
    coding_prompts = [
        "Write a Python function to calculate the Fibonacci sequence up to n terms",
        "Create a function to check if a string is a palindrome",
        "Write a Python script to find all prime numbers up to 100",
        "Implement a binary search algorithm in Python",
        "Write a function to reverse a linked list",
        "Create a Python function to merge two sorted arrays",
        "Write a function to find the maximum element in a binary tree",
        "Implement quicksort algorithm in Python",
        "Write a function to detect cycles in a linked list",
        "Create a Python class for a stack with push, pop, and peek operations",
        "Write a function to calculate the greatest common divisor of two numbers",
        "Implement a function to find the longest common subsequence",
        "Write a Python function to validate if parentheses are balanced",
        "Create a function to rotate an array to the right by k steps",
        "Write a recursive function to calculate factorial",
        "Implement a function to find the intersection of two arrays",
        "Write a Python function to convert decimal to binary",
        "Create a function to find the second largest element in an array",
        "Write a function to check if a number is prime",
        "Implement a simple hash table in Python",
        "Write a function to find duplicates in an array",
        "Create a Python function to calculate matrix multiplication",
        "Write a function to implement breadth-first search",
        "Implement a function to find anagrams in a list of strings",
        "Write a Python function to compress a string using run-length encoding",
        "Create a function to implement depth-first search",
        "Write a Python function to calculate edit distance",
        "Implement a function to find the kth largest element",
        "Write a function to validate a binary search tree",
        "Create a Python class for a queue using two stacks",
        "Write a function to find the minimum window substring",
        "Implement a function to merge k sorted lists",
        "Write a Python function to calculate coin change combinations",
        "Create a function to find the longest palindromic substring",
        "Write a function to implement topological sorting",
        "Implement a function to find strongly connected components",
        "Write a Python function to calculate maximum subarray sum",
        "Create a function to implement union-find data structure",
        "Write a function to find the median of two sorted arrays",
        "Implement a Python function to solve the knapsack problem"
    ]
    
    # Ensure exactly 40 coding prompts
    for i in range(40):
        prompt = coding_prompts[i % len(coding_prompts)]
        if i >= len(coding_prompts):
            prompt = f"Optimize this solution: {prompt}"
        
        dataset.append({
            "id": item_id,
            "prompt": prompt,
            "domain": "coding",
            "scoring_method": "compile_and_test", 
            "weight": 0.20,
            "expected_tokens": 200
        })
        item_id += 1
    
    # Science domain prompts (35 items, 15% weight)
    science_prompts = [
        "Calculate the orbital velocity needed for a satellite to orbit Earth at 400 km altitude",
        "What is the escape velocity from Earth's surface?",
        "Calculate the gravitational force between Earth and Moon",
        "Determine the energy required to heat 1 kg of water from 20°C to 100°C",
        "What is the wavelength of visible light with frequency 5×10¹⁴ Hz?",
        "Calculate the pH of a 0.1 M HCl solution",
        "What is the half-life of carbon-14 and how is it used in dating?",
        "Calculate the momentum of a 1000 kg car traveling at 25 m/s",
        "What is the pressure at 10 meters depth in water?",
        "Calculate the electric field around a point charge of 1 μC at 1 meter distance"
    ]
    
    for i in range(35):
        if i < len(science_prompts):
            prompt = science_prompts[i]
        else:
            prompt = f"Apply physics principles to solve: {science_prompts[i % len(science_prompts)]}"
        
        dataset.append({
            "id": item_id,
            "prompt": prompt,
            "domain": "science",
            "scoring_method": "numeric_with_units",
            "weight": 0.15,
            "expected_tokens": 100
        })
        item_id += 1
    
    # Planning domain prompts (20 items, 5% weight)
    planning_prompts = [
        "Plan a 7-day vacation to Japan including flights, hotels, and activities",
        "Create a project timeline for developing a mobile app in 6 months",
        "Design a study schedule for preparing for a medical exam in 3 months",
        "Plan the logistics for organizing a 500-person conference",
        "Create a business plan for opening a small restaurant",
        "Plan a route for a cross-country road trip in 2 weeks",
        "Design a workout plan for training for a marathon in 6 months",
        "Plan the renovation of a 3-bedroom house over 4 months",
        "Create a meal prep plan for a family of 4 for one month",
        "Plan the launch strategy for a new software product",
        "Design a budget plan for a young professional's first year",
        "Plan the curriculum for a 16-week programming course",
        "Create a marketing campaign timeline for a product launch",
        "Plan a garden layout for maximum yield in a small space",
        "Design a disaster preparedness plan for a small town",
        "Plan the organization of a large wedding with 200 guests",
        "Create a retirement savings strategy for someone starting at age 25",
        "Plan the setup and management of a home office",
        "Design a supply chain strategy for a manufacturing company",
        "Plan the implementation of a company-wide remote work policy",
        "Create a personal development plan for career advancement",
        "Plan the restoration of a historic building",
        "Design a public transportation system for a growing city",
        "Plan the inventory management for a retail store",
        "Create a social media strategy for a nonprofit organization"
    ]
    
    for i, prompt in enumerate(planning_prompts[:20]):  # Only take first 20
        dataset.append({
            "id": item_id,
            "prompt": prompt,
            "domain": "planning",
            "scoring_method": "em_and_f1",
            "weight": 0.05,
            "expected_tokens": 300
        })
        item_id += 1
    
    # Writing domain prompts (15 items, 5% weight)
    writing_prompts = [
        "Write a creative short story about a robot who discovers emotions",
        "Compose a persuasive essay about the importance of renewable energy",
        "Write a haiku about the changing seasons",
        "Create a character description for a mysterious detective",
        "Write a technical explanation of how machine learning works for beginners",
        "Compose a letter of recommendation for a stellar employee",
        "Write a product description for an innovative kitchen gadget",
        "Create a dialogue between two characters discussing time travel",
        "Write a summary of the major themes in Shakespeare's Hamlet",
        "Compose a motivational speech for high school graduates",
        "Write a restaurant review of your ideal dining experience",
        "Create a press release for a groundbreaking scientific discovery",
        "Write a children's story about friendship and kindness",
        "Compose an article about the future of space exploration",
        "Write a poem about the beauty of nature"
    ]
    
    for i, prompt in enumerate(writing_prompts):  # Exactly 15 items
        dataset.append({
            "id": item_id,
            "prompt": prompt,
            "domain": "writing",
            "scoring_method": "rouge_l",
            "weight": 0.05,
            "expected_tokens": 250
        })
        item_id += 1
    
    # Verify total count
    assert len(dataset) == 380, f"Expected 380 items, got {len(dataset)}"
    
    # Save to datasets directory
    os.makedirs("datasets", exist_ok=True)
    
    with open("datasets/titanic_gauntlet_2025_06.jsonl", "w") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")
    
    print(f"✅ Created Titanic Gauntlet dataset with {len(dataset)} prompts")
    print("📊 Domain distribution:")
    
    domain_counts = {}
    for item in dataset:
        domain = item["domain"]
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    for domain, count in domain_counts.items():
        print(f"   {domain}: {count} prompts")
    
    return len(dataset)

if __name__ == "__main__":
    create_titanic_dataset() 