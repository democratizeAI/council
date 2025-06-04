#!/usr/bin/env python3
import re

def test_code_extraction():
    # The actual code from the litmus test
    code = '''```python
def gcd(a, b):
    while b!= 0:
        a, b = b, a % b
    return a
```

### Exercise 2: ...'''

    print("Original code:")
    print(repr(code))
    print("\nOriginal code:")
    print(code)
    
    # Test extraction
    match = re.search(r'```python\s*(.*?)\s*```', code, re.DOTALL | re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        print(f"\nExtracted code:")
        print(repr(extracted))
        print(f"\nExtracted code (formatted):")
        print(extracted)
        
        try:
            compile(extracted, '<string>', 'exec')
            print('✅ Compiles successfully')
        except Exception as e:
            print(f'❌ Compilation error: {e}')
            print(f'Error at character: {e.offset if hasattr(e, "offset") else "unknown"}')
    else:
        print("❌ No match found")

if __name__ == "__main__":
    test_code_extraction() 