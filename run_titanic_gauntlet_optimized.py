#!/usr/bin/env python3
"""
Titanic Gauntlet - Optimized with Smart Routing + Async Concurrency
380 prompts across 6 domains with statistical rigor
"""

import asyncio
import httpx
import time
import json
import argparse
from typing import Dict, Any, List
from datetime import datetime

# Configuration
CONCURRENCY = 16          # Concurrent requests (adjust for GPU utilization)
TIMEOUT_MS = 4000         # 4 second timeout for slow prompts
BASE_URL = "http://localhost:8000"

# Titanic Gauntlet Dataset (380 prompts)
GAUNTLET_PROMPTS = {
    "math": [
        "Calculate 17 * 19 and show your work",
        "What is the square root of 144?",
        "Solve: 2x + 5 = 17",
        "Convert 0.75 to a fraction",
        "What is 15% of 240?",
        "Find the area of a circle with radius 7",
        "What is 8! (8 factorial)?",
        "Simplify: (x^2 + 3x + 2) / (x + 1)",
        "What is log₂(64)?",
        "Calculate the mean of: 12, 15, 18, 22, 25",
        "What is 3⁴?",
        "Solve: √(x + 3) = 5",
        "Convert 45° to radians",
        "What is the derivative of x³ + 2x²?",
        "Find GCD(48, 72)",
        "What is 7 × 9 × 11?",
        "Calculate compound interest: $1000 at 5% for 3 years",
        "What is the sum of angles in a hexagon?",
        "Solve: 3x - 7 = 2x + 5",
        "What is 2⁵ × 2³?",
        "Find the slope between (2,3) and (6,11)",
        "What is 156 ÷ 12?",
        "Calculate the perimeter of a rectangle 8×5",
        "What is the cube root of 125?",
        "Solve: 4x² - 16 = 0",
        "What is 25% of 80% of 200?",
        "Find the median of: 3, 7, 12, 15, 18, 21",
        "What is the volume of a sphere with radius 3?",
        "Calculate: (5 + 3) × (7 - 2)",
        "What is the probability of rolling two 6s?",
        "Simplify: 3x + 5x - 2x",
        "What is 144 ÷ 16?",
        "Find the hypotenuse of a 3-4-5 triangle",
        "What is 0.25 as a percentage?",
        "Calculate: 7² - 3²",
        "What is the sum of first 10 natural numbers?",
        "Solve: 5(x - 2) = 25",
        "What is the area of a triangle with base 6 and height 8?",
        "Find the LCM of 12 and 18",
        "What is 64^(1/3)?",
        "Calculate: 15 + 23 - 11 + 8",
        "What is the circumference of a circle with diameter 10?",
        "Solve: x/4 + 3 = 7",
        "What is 2.5 × 4.8?",
        "Find the distance between (-1,2) and (3,5)",
        "What is 9% of 150?",
        "Calculate: (-3)²",
        "What is the surface area of a cube with side 4?",
        "Solve: |x - 5| = 3",
        "What is the reciprocal of 3/7?",
        "Calculate: 24 ÷ 3 × 2",
        "What is the standard deviation of: 2, 4, 6, 8, 10?",
        "Find the roots of x² - 5x + 6 = 0",
        "What is 72 in binary?",
        "Calculate the nth term formula for 2, 5, 8, 11...",
        "What is sin(90°)?",
        "Find the slope of line y = 3x + 2",
        "What is 999 + 1?",
        "Calculate: 3! + 4!",
        "What is the diagonal of a square with side 5?",
        "Solve: 2^x = 32",
        "What is 3.7 + 2.8?",
        "Find the midpoint of (1,3) and (7,9)",
        "What is 40% of 75?",
        "Calculate: 6 × 7 - 8 ÷ 2",
        "What is the sum of interior angles of a pentagon?",
        "Solve: 3x + 2y = 12, x = 2",
        "What is √81?",
        "Calculate the area of a parallelogram with base 8 and height 5",
        "What is 1000 - 347?",
        "Find the value of x if 2x = 18",
        "What is 4.5 × 10²?",
        "Calculate: 16 ÷ 4 + 3 × 2",
        "What is the volume of a rectangular prism 3×4×5?",
        "Solve: x² = 49",
        "What is 7/8 as a decimal?",
        "Find the perimeter of an equilateral triangle with side 9",
        "What is 123 × 0?",
        "Calculate: (2 + 3)²",
        "What is the complement of a 35° angle?",
        "Solve for y: 3y - 9 = 0",
        "What is 5⁰?",
        "Find the area of a trapezoid with bases 6,10 and height 4",
        "What is 88 ÷ 8?",
        "Calculate: 15² - 14²",
        "What is π to 3 decimal places?",
        "Solve: 4x + 1 = 3x + 7",
        "What is the greatest common factor of 24 and 36?",
        "Calculate: 2/3 + 1/6",
        "What is the angle in an equilateral triangle?",
        "Find x: 5x - 10 = 0",
        "What is 250 ÷ 5?",
        "Calculate the diagonal of a rectangle 6×8",
        "What is 0.6 + 0.4?",
        "Solve: x³ = 27",
        "What is 12 × 25?",
        "Find the sum of angles in a triangle",
        "What is 3/4 of 120?",
        "Calculate: 100 - 37",
        "What is the radius if diameter is 16?",
        "Solve: 2(x + 3) = 14",
        "What is 729 ÷ 27?",
        "Find the area of a semicircle with radius 4",
        "What is 1.5²?",
        "Calculate: 8 + 6 × 2",
        "What is the supplement of a 110° angle?",
        "Solve: x/3 = 12",
        "What is 13²?",
        "Find the volume of a cylinder r=2, h=5",
        "What is 456 + 789?",
        "Calculate: √(25 + 144)",
        "What is 20% of 250?",
        "Solve: 7x = 84",
        "What is 64 ÷ 8 + 2?",
        "Find the area of a rhombus with diagonals 6 and 8",
        "What is 3.14 × 2?",
        "Calculate: 18 - 9 + 4",
        "What is the exterior angle of a regular hexagon?",
        "Solve: x + 15 = 23",
        "What is 11 × 11?",
        "Find the perimeter of a circle with radius 5",
        "What is 87 - 29?",
        "Calculate: 4³ ÷ 8",
        "What is cos(0°)?",
        "Solve: 6x + 12 = 48",
        "What is 999 ÷ 3?",
        "Find the area of an isosceles triangle base=10, height=6",
        "What is 2.7 + 1.3?",
        "Calculate: 15% + 25%",
        "What is the sum of first 5 prime numbers?",
        "Solve: x² + 4x = 0",
        "What is 48 ÷ 6?",
        "Find the diagonal of a cube with side 3",
        "What is 5/6 - 1/3?",
        "Calculate: 200 × 0.05",
        "What is the area of a regular pentagon with side 4?"
    ],
    
    "reasoning": [
        "If all Bloops are Razzles and all Razzles are Lazzles, are all Bloops Lazzles?",
        "A train leaves at 3pm going 60mph. Another leaves at 4pm going 80mph. When do they meet?",
        "If today is Wednesday, what day was it 100 days ago?",
        "Mary is twice as old as John. In 5 years, she'll be 1.5 times as old. How old is Mary now?",
        "Complete the pattern: 2, 6, 18, 54, ?",
        "If A→B and B→C, and A is true, what can we conclude about C?",
        "A man has 7 daughters. Each daughter has 1 brother. How many children does he have?",
        "If it takes 5 machines 5 minutes to make 5 widgets, how long for 100 machines to make 100 widgets?",
        "Complete: RED, BLUE, GREEN, YELLOW, ?",
        "If some cats are dogs and some dogs are birds, can some cats be birds?",
        "What comes next: 1, 1, 2, 3, 5, 8, ?",
        "If P implies Q, and not Q, what can we say about P?",
        "A clock shows 3:15. What is the angle between the hands?",
        "If all roses are flowers and some flowers are red, are some roses red?",
        "What number comes next: 1, 4, 9, 16, 25, ?",
        "If you're facing north and turn 270° clockwise, which direction are you facing?",
        "Complete the analogy: Book is to Reading as Fork is to ?",
        "If A is north of B, and C is east of A, what direction is C from B?",
        "What's the next letter: A, D, G, J, ?",
        "If all musicians are artists and no artists are doctors, can a musician be a doctor?",
        "A bat and ball cost $1.10. The bat costs $1 more than the ball. How much is the ball?",
        "If Monday is the 5th, what day of the week is the 23rd?",
        "Complete: 3, 6, 12, 24, ?",
        "If some A are B, and all B are C, then some A are definitely what?",
        "What comes next in: Circle, Square, Triangle, Pentagon, ?",
        "If it's raining, then the ground is wet. The ground is not wet. What can we conclude?",
        "A farmer has 17 sheep. All but 9 die. How many are left?",
        "If you flip a fair coin 3 times and get heads each time, what's the probability of heads on the 4th flip?",
        "Complete: January, March, May, July, ?",
        "If all birds can fly and penguins are birds, can penguins fly?",
        "What number is missing: 2, 4, 8, ?, 32",
        "If A is taller than B, and B is taller than C, who is shortest?",
        "Complete the sequence: MON, TUE, WED, THU, ?",
        "If some doctors are teachers and all teachers are educated, are some doctors educated?",
        "What comes next: 10, 20, 30, 40, ?",
        "If you start facing east and turn 180°, which way are you facing?",
        "Complete: Apple, Banana, Cherry, Date, ?",
        "If no cats are dogs and some pets are cats, can some pets be dogs?",
        "What's the pattern: 1, 3, 7, 15, 31, ?",
        "If today is Friday the 13th, what day is the 20th?",
        "Complete: Hot, Cold, Big, Small, Fast, ?",
        "If all squares are rectangles and some rectangles are large, are some squares large?",
        "What number comes next: 100, 81, 64, 49, ?",
        "If you're at position (0,0) and move 3 units north then 4 units east, where are you?",
        "Complete: Mercury, Venus, Earth, Mars, ?",
        "If some fish swim and all swimming things move, do some fish move?",
        "What's next: 2, 6, 14, 30, ?",
        "If P or Q is true, and P is false, what about Q?",
        "Complete: Red, Orange, Yellow, Green, ?",
        "If all mammals breathe air and whales are mammals, do whales breathe air?",
        "What comes next: 1, 8, 27, 64, ?",
        "If it's 2pm now and a meeting was 3 hours ago, when was the meeting?",
        "Complete: Spring, Summer, Fall, ?",
        "If no vegetables are meat and some food is vegetables, is some food not meat?",
        "What's the pattern: 5, 10, 20, 40, ?",
        "If A implies B, and B implies C, does A imply C?",
        "Complete: Alpha, Beta, Gamma, Delta, ?",
        "If some students study hard and all who study hard succeed, do some students succeed?",
        "What number is next: 3, 9, 27, 81, ?",
        "If you subtract 5 from a number and get 12, what was the original number?",
        "Complete: Do, Re, Mi, Fa, ?",
        "If all cars have wheels and some vehicles are cars, do some vehicles have wheels?",
        "What comes next: 2, 5, 11, 23, ?",
        "If not (P and Q) is true, and P is true, what about Q?",
        "Complete: First, Second, Third, Fourth, ?",
        "If all roses smell sweet and this flower smells sweet, is it a rose?",
        "What's next: 1, 2, 4, 7, 11, ?",
        "If you're 5 miles north of home and travel 3 miles south, how far from home are you?",
        "Complete: Tiny, Small, Medium, Large, ?",
        "If some books are novels and all novels are fiction, are some books fiction?",
        "What number comes next: 6, 12, 24, 48, ?",
        "If either A or B is true, and A is false, what about B?",
        "Complete: Ice, Water, Steam, ?",
        "If all politicians make promises and some promise-makers lie, do some politicians lie?",
        "What's the pattern: 1, 1, 2, 6, 24, ?",
        "If it's currently 7:30pm and you have a 2-hour movie starting at 8pm, when does it end?",
        "Complete: North, South, East, ?",
        "If no reptiles are mammals and some animals are reptiles, are some animals not mammals?",
        "What comes next: 0, 1, 1, 2, 3, 5, ?",
        "If P is necessary for Q, and Q is false, what about P?",
        "Complete: Breakfast, Lunch, Dinner, ?",
        "If all triangles have three sides and this shape has three sides, is it a triangle?",
        "What's next: 4, 9, 16, 25, 36, ?",
        "If you start with 100 and subtract 15 three times, what do you have?",
        "Complete: Primary, Secondary, Tertiary, ?",
        "If some athletes are fast and all fast things are efficient, are some athletes efficient?",
        "What number is missing: 7, 14, 28, ?, 112",
        "If (P and Q) or R is true, and R is false, what about (P and Q)?",
        "Complete: Solid, Liquid, Gas, ?",
        "If all flowers need sunlight and roses are flowers, do roses need sunlight?",
        "What comes next: 64, 32, 16, 8, ?",
        "If you're facing northwest and turn 90° clockwise, which direction are you facing?",
        "Complete: Past, Present, Future, ?",
        "If some computers are fast and no fast things are cheap, are some computers not cheap?",
        "What's the pattern: 2, 3, 5, 8, 13, ?",
        "If not P implies Q, and Q is false, what about P?",
        "Complete: Morning, Afternoon, Evening, ?",
        "If all metals conduct electricity and copper is a metal, does copper conduct electricity?",
        "What number comes next: 1, 11, 21, 1211, ?",
        "If you add 7 to a number and get 20, what was the number?",
        "Complete: Input, Process, Output, ?",
        "If some birds migrate and all migrating things travel, do some birds travel?",
        "What's next: 100, 50, 25, 12.5, ?",
        "If P is sufficient for Q, and P is true, what about Q?"
    ],
    
    "coding": [
        "Write a Python function to find the factorial of a number",
        "How do you reverse a string in JavaScript?",
        "What's the time complexity of binary search?",
        "Write a SQL query to find the second highest salary",
        "How do you handle exceptions in Python?",
        "What's the difference between == and === in JavaScript?",
        "Write a function to check if a number is prime",
        "How do you implement a stack using arrays?",
        "What's a closure in programming?",
        "Write a regex to validate an email address",
        "How do you sort an array in descending order in Python?",
        "What's the difference between var, let, and const in JavaScript?",
        "Write a function to find the maximum element in an array",
        "How do you create a class in Python?",
        "What's recursion and how do you implement it?",
        "Write a SQL query to join two tables",
        "How do you remove duplicates from an array?",
        "What's the difference between GET and POST requests?",
        "Write a function to calculate Fibonacci numbers",
        "How do you handle asynchronous operations in JavaScript?",
        "What's Big O notation?",
        "Write a function to merge two sorted arrays",
        "How do you use list comprehensions in Python?",
        "What's the difference between abstract classes and interfaces?",
        "Write a function to check if a string is a palindrome",
        "How do you implement inheritance in object-oriented programming?",
        "What's a hash table and how does it work?",
        "Write a SQL query with GROUP BY and HAVING clauses",
        "How do you debug code effectively?",
        "What's the difference between synchronous and asynchronous programming?",
        "Write a function to find the longest common subsequence",
        "How do you optimize database queries?",
        "What's dependency injection?",
        "Write a function to implement binary search",
        "How do you handle memory management in programming?",
        "What's the MVC pattern?",
        "Write a function to rotate an array",
        "How do you test your code?",
        "What's the difference between composition and inheritance?",
        "Write a function to find all permutations of a string",
        "How do you secure a web application?",
        "What's a design pattern?",
        "Write a function to implement a linked list",
        "How do you optimize algorithm performance?",
        "What's REST API?",
        "Write a function to check balanced parentheses",
        "How do you handle database transactions?",
        "What's polymorphism in OOP?",
        "Write a function to find the kth largest element",
        "How do you implement caching?",
        "What's the difference between SQL and NoSQL?",
        "Write a function to detect cycles in a linked list",
        "How do you handle version control with Git?",
        "What's a lambda function?",
        "Write a function to implement quicksort",
        "How do you handle concurrent programming?",
        "What's the singleton pattern?",
        "Write a function to find common elements in two arrays",
        "How do you profile and optimize code?",
        "What's functional programming?",
        "Write a function to implement a queue using stacks",
        "How do you handle API rate limiting?",
        "What's encapsulation in OOP?",
        "Write a function to find the shortest path in a graph",
        "How do you implement authentication and authorization?",
        "What's the observer pattern?",
        "Write a function to validate input data",
        "How do you handle cross-origin requests (CORS)?",
        "What's a callback function?",
        "Write a function to implement merge sort",
        "How do you optimize front-end performance?",
        "What's the factory pattern?",
        "Write a function to find anagrams in a list of words",
        "How do you handle database migrations?",
        "What's event-driven programming?",
        "Write a function to implement a trie data structure",
        "How do you handle logging in applications?",
        "What's the strategy pattern?"
    ],
    
    "science": [
        "What is photosynthesis?",
        "Explain Newton's first law of motion",
        "What causes seasons on Earth?",
        "How does DNA replication work?",
        "What is the difference between mass and weight?",
        "Explain the water cycle",
        "What is entropy in thermodynamics?",
        "How do vaccines work?",
        "What causes lightning?",
        "Explain the greenhouse effect",
        "What is evolution by natural selection?",
        "How do magnets work?",
        "What is the structure of an atom?",
        "Explain how batteries generate electricity",
        "What causes tides?",
        "How does the human immune system work?",
        "What is radioactive decay?",
        "Explain plate tectonics",
        "What is the difference between speed and velocity?",
        "How do plants reproduce?",
        "What causes earthquakes?",
        "Explain the carbon cycle",
        "What is quantum mechanics?",
        "How do rockets work in space?",
        "What is the electromagnetic spectrum?",
        "Explain cellular respiration",
        "What causes the Northern Lights?",
        "How does sound travel?",
        "What is genetic engineering?",
        "Explain the periodic table organization",
        "What causes volcanoes?",
        "How does the brain process information?",
        "What is climate change?",
        "Explain how muscles contract",
        "What is nuclear fusion?",
        "How do antibiotics work?",
        "What causes ocean currents?",
        "Explain the theory of relativity",
        "What is mitosis?",
        "How do semiconductors work?",
        "What causes acid rain?",
        "Explain how the heart pumps blood",
        "What is dark matter?",
        "How do catalysts work in chemical reactions?",
        "What causes the ozone layer depletion?",
        "Explain how vision works",
        "What is superconductivity?",
        "How do hormones regulate body functions?",
        "What causes hurricanes?",
        "Explain photosynthesis in detail",
        "What is the Doppler effect?",
        "How do enzymes work?",
        "What causes global warming?",
        "Explain how memory formation works",
        "What is nuclear fission?",
        "How do crystals form?",
        "What causes ice ages?"
    ],
    
    "planning": [
        "Plan a week-long vacation to Japan",
        "How would you organize a wedding for 100 people?",
        "Create a study schedule for final exams",
        "Plan a surprise birthday party",
        "How to start a small business?",
        "Organize a charity fundraising event",
        "Plan a cross-country road trip",
        "Create a workout routine for beginners",
        "Plan a dinner party for 8 people",
        "How to prepare for a job interview?",
        "Organize a school science fair",
        "Plan a budget for a college student",
        "Create a marketing strategy for a new product",
        "Plan a family reunion",
        "How to organize a home office?",
        "Plan a camping trip for a group",
        "Create a meal prep plan for the week",
        "Plan a conference for 200 attendees",
        "How to plan for retirement?",
        "Organize a community garden project"
    ],
    
    "writing": [
        "Write a short story about time travel",
        "Compose a persuasive essay on renewable energy",
        "Write a haiku about autumn",
        "Create a business proposal for a tech startup",
        "Write a letter of complaint to a company",
        "Compose a love poem",
        "Write instructions for making a paper airplane",
        "Create a character description for a novel",
        "Write a news article about a scientific discovery",
        "Compose a thank you note",
        "Write a movie review",
        "Create a social media post for a restaurant",
        "Write a cover letter for a job application",
        "Compose a speech for a graduation ceremony",
        "Write a product description for an online store",
        "Create a blog post about healthy eating",
        "Write a dialogue between two characters",
        "Compose an email to a professor",
        "Write a summary of a research paper",
        "Create a fictional news headline"
    ]
}

async def fire_prompt(client: httpx.AsyncClient, base_url: str, prompt: str, prompt_id: int, timeout_ms: int = TIMEOUT_MS):
    """Fire a single prompt and measure response time"""
    t0 = time.perf_counter()
    try:
        response = await client.post(
            f"{base_url}/hybrid",
            json={"prompt": prompt},
            timeout=timeout_ms / 1000
        )
        response_time_ms = (time.perf_counter() - t0) * 1000
        result = response.json()
        return {
            'success': True,
            'prompt_id': prompt_id,
            'prompt': prompt,
            'result': result,
            'time_ms': response_time_ms,
            'error': None
        }
    except Exception as e:
        response_time_ms = (time.perf_counter() - t0) * 1000
        return {
            'success': False,
            'prompt_id': prompt_id,
            'prompt': prompt,
            'result': None,
            'time_ms': response_time_ms,
            'error': str(e)
        }

async def run_domain_async(domain: str, prompts: List[str], base_url: str, concurrency: int, timeout_ms: int = TIMEOUT_MS):
    """Run all prompts in a domain with async concurrency"""
    
    print(f"\n🎯 DOMAIN: {domain.upper()} ({len(prompts)} prompts)")
    print("-" * 50)
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(concurrency)
    
    async def limited_fire_prompt(client, prompt, prompt_id):
        async with semaphore:
            return await fire_prompt(client, base_url, prompt, prompt_id, timeout_ms)
    
    # Use HTTP/2 with keep-alive for performance
    async with httpx.AsyncClient(
        http2=True,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    ) as client:
        
        # Create tasks for all prompts
        tasks = [
            limited_fire_prompt(client, prompt, i)
            for i, prompt in enumerate(prompts)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
    
    # Process results
    domain_stats = {
        "total": len(prompts),
        "successful": 0,
        "failed": 0,
        "smart_routing": 0,
        "voting_routing": 0,
        "avg_time": 0,
        "times": [],
        "responses": []
    }
    
    for result in results:
        if result['success']:
            domain_stats['successful'] += 1
            domain_stats['times'].append(result['time_ms'])
            
            # Track routing type
            provider = result['result'].get('provider', 'unknown')
            if 'smart' in provider:
                domain_stats['smart_routing'] += 1
            elif 'voting' in provider:
                domain_stats['voting_routing'] += 1
            
            # Store response
            domain_stats['responses'].append({
                'domain': domain,
                'prompt': result['prompt'],
                'response': result['result'].get('text', ''),
                'provider': provider,
                'model_used': result['result'].get('model_used', ''),
                'confidence': result['result'].get('confidence', 0),
                'time_ms': result['time_ms']
            })
            
            print(f"  {result['prompt_id']+1:3d}. {result['prompt'][:60]:<60} | {provider:<12} | {result['time_ms']:5.0f}ms")
        else:
            domain_stats['failed'] += 1
            print(f"  {result['prompt_id']+1:3d}. {result['prompt'][:60]:<60} | ERROR: {result['error']}")
    
    # Calculate statistics
    if domain_stats['times']:
        domain_stats['avg_time'] = sum(domain_stats['times']) / len(domain_stats['times'])
        times_sorted = sorted(domain_stats['times'])
        domain_stats['p50'] = times_sorted[len(times_sorted) // 2]
        domain_stats['p95'] = times_sorted[int(len(times_sorted) * 0.95)]
        domain_stats['p99'] = times_sorted[int(len(times_sorted) * 0.99)]
    
    print(f"\n📈 {domain.upper()} SUMMARY:")
    print(f"   Success Rate: {domain_stats['successful']}/{domain_stats['total']} ({domain_stats['successful']/domain_stats['total']*100:.1f}%)")
    print(f"   Smart Routing: {domain_stats['smart_routing']} prompts")
    print(f"   Voting Routing: {domain_stats['voting_routing']} prompts")
    print(f"   Avg Time: {domain_stats['avg_time']:.0f}ms")
    if domain_stats['times']:
        print(f"   p50: {domain_stats['p50']:.0f}ms, p95: {domain_stats['p95']:.0f}ms, p99: {domain_stats['p99']:.0f}ms")
    
    return domain_stats

async def run_titanic_gauntlet_async(concurrency: int = CONCURRENCY, timeout_ms: int = TIMEOUT_MS):
    """Run the complete Titanic Gauntlet with async concurrency"""
    
    print("🚢 TITANIC GAUNTLET - ASYNC OPTIMIZED")
    print("=" * 80)
    print(f"📊 Dataset: 380 prompts across 6 domains")
    print(f"🎯 Target: Sub-500ms p95 latency for smart routing")
    print(f"⚡ Optimization: Smart routing + {concurrency}-way async concurrency")
    print(f"🌐 HTTP/2 + Keep-Alive connections")
    print(f"⏱️ Timeout: {timeout_ms}ms")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = {
        "total_prompts": 0,
        "successful_responses": 0,
        "failed_responses": 0,
        "domains": {},
        "routing_stats": {
            "smart_routing": 0,
            "voting_routing": 0
        },
        "performance": {
            "total_time": 0,
            "avg_response_time": 0,
            "smart_avg_time": 0,
            "voting_avg_time": 0,
            "p50": 0,
            "p95": 0,
            "p99": 0
        },
        "responses": []
    }
    
    start_time = time.time()
    
    # Process each domain asynchronously
    for domain, prompts in GAUNTLET_PROMPTS.items():
        domain_stats = await run_domain_async(domain, prompts, BASE_URL, concurrency, timeout_ms)
        
        # Aggregate results
        results['domains'][domain] = domain_stats
        results['total_prompts'] += domain_stats['total']
        results['successful_responses'] += domain_stats['successful']
        results['failed_responses'] += domain_stats['failed']
        results['routing_stats']['smart_routing'] += domain_stats['smart_routing']
        results['routing_stats']['voting_routing'] += domain_stats['voting_routing']
        results['responses'].extend(domain_stats['responses'])
    
    total_time = time.time() - start_time
    
    # Calculate overall performance metrics
    all_times = [r['time_ms'] for r in results['responses']]
    smart_times = [r['time_ms'] for r in results['responses'] if 'smart' in r['provider']]
    voting_times = [r['time_ms'] for r in results['responses'] if 'voting' in r['provider']]
    
    results['performance']['total_time'] = total_time
    if all_times:
        all_times_sorted = sorted(all_times)
        results['performance']['avg_response_time'] = sum(all_times) / len(all_times)
        results['performance']['p50'] = all_times_sorted[len(all_times_sorted) // 2]
        results['performance']['p95'] = all_times_sorted[int(len(all_times_sorted) * 0.95)]
        results['performance']['p99'] = all_times_sorted[int(len(all_times_sorted) * 0.99)]
    
    if smart_times:
        smart_times_sorted = sorted(smart_times)
        results['performance']['smart_avg_time'] = sum(smart_times) / len(smart_times)
        results['performance']['smart_p50'] = smart_times_sorted[len(smart_times_sorted) // 2]
        results['performance']['smart_p95'] = smart_times_sorted[int(len(smart_times_sorted) * 0.95)]
        results['performance']['smart_p99'] = smart_times_sorted[int(len(smart_times_sorted) * 0.99)]
    
    if voting_times:
        voting_times_sorted = sorted(voting_times)
        results['performance']['voting_avg_time'] = sum(voting_times) / len(voting_times)
        results['performance']['voting_p95'] = voting_times_sorted[int(len(voting_times_sorted) * 0.95)]
    
    # Final Report
    print("\n" + "=" * 80)
    print("🏆 TITANIC GAUNTLET COMPLETE!")
    print("=" * 80)
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Total Prompts: {results['total_prompts']}")
    print(f"   Successful: {results['successful_responses']} ({results['successful_responses']/results['total_prompts']*100:.1f}%)")
    print(f"   Failed: {results['failed_responses']} ({results['failed_responses']/results['total_prompts']*100:.1f}%)")
    
    print(f"\n⚡ ROUTING EFFICIENCY:")
    total_routed = results['routing_stats']['smart_routing'] + results['routing_stats']['voting_routing']
    if total_routed > 0:
        smart_pct = results['routing_stats']['smart_routing'] / total_routed * 100
        voting_pct = results['routing_stats']['voting_routing'] / total_routed * 100
        print(f"   Smart Routing: {results['routing_stats']['smart_routing']} prompts ({smart_pct:.1f}%)")
        print(f"   Voting Routing: {results['routing_stats']['voting_routing']} prompts ({voting_pct:.1f}%)")
    
    print(f"\n⏱️ PERFORMANCE METRICS:")
    print(f"   Total Runtime: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"   Throughput: {results['total_prompts']/total_time:.1f} prompts/second")
    print(f"   Average Response Time: {results['performance']['avg_response_time']:.0f}ms")
    print(f"   p50: {results['performance']['p50']:.0f}ms")
    print(f"   p95: {results['performance']['p95']:.0f}ms")
    print(f"   p99: {results['performance']['p99']:.0f}ms")
    
    if smart_times and voting_times:
        print(f"\n🎯 SMART ROUTING PERFORMANCE:")
        print(f"   Smart Avg: {results['performance']['smart_avg_time']:.0f}ms")
        print(f"   Smart p50: {results['performance']['smart_p50']:.0f}ms")
        print(f"   Smart p95: {results['performance']['smart_p95']:.0f}ms ({'✅ SUB-500MS' if results['performance']['smart_p95'] < 500 else '❌ OVER 500MS'})")
        print(f"   Smart p99: {results['performance']['smart_p99']:.0f}ms")
        print(f"   Voting p95: {results['performance']['voting_p95']:.0f}ms")
        
        improvement = (results['performance']['voting_avg_time'] - results['performance']['smart_avg_time']) / results['performance']['voting_avg_time'] * 100
        print(f"   Smart Speedup: {improvement:.1f}% faster than voting")
    
    print(f"\n📈 DOMAIN BREAKDOWN:")
    for domain, stats in results['domains'].items():
        success_rate = stats['successful'] / stats['total'] * 100
        p95_str = f"p95: {stats.get('p95', 0):.0f}ms" if stats.get('p95') else "no times"
        print(f"   {domain.upper():<12}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%) | avg: {stats['avg_time']:.0f}ms | {p95_str}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"titanic_gauntlet_async_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n✅ Async Titanic Gauntlet Complete! Smart routing performance optimized.")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Titanic Gauntlet - Async Optimized')
    parser.add_argument('--concurrency', type=int, default=CONCURRENCY, 
                        help=f'Number of concurrent requests (default: {CONCURRENCY})')
    parser.add_argument('--timeout', type=int, default=TIMEOUT_MS,
                        help=f'Timeout in milliseconds (default: {TIMEOUT_MS})')
    
    args = parser.parse_args()
    
    # Run the async gauntlet with specified parameters
    asyncio.run(run_titanic_gauntlet_async(args.concurrency, args.timeout))

if __name__ == "__main__":
    main() 