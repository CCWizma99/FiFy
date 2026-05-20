import sys
import os

# Add the project root to sys.path if needed
sys.path.append(os.getcwd())

from scraper.executor import _minimize_html

sample_html = """
<html>
<body>
    <div class="header">Header</div>
    <ul class="product-grid">
        <li class="item" data-id="1">Product 1</li>
        <li class="item" data-id="2">Product 2</li>
        <li class="item" data-id="3">Product 3</li>
    </ul>
    <div class="footer">
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </div>
    <div class="repeating" class="foo">A</div>
    <div class="repeating" class="foo">B</div>
    <div class="repeating" class="foo">C</div>
</body>
</html>
"""

# Case 2: Identical attributes
sample_html_identical = """
<html>
<body>
    <div class="product-card">Card 1</div>
    <div class="product-card">Card 2</div>
    <div class="product-card">Card 3</div>
</body>
</html>
"""

print("--- TEST 1: Unique attributes (should NOT prune) ---")
minimized1 = _minimize_html(sample_html)
print(f"Original length: {len(sample_html)}")
print(f"Minimized length: {len(minimized1)}")
print(minimized1)

print("\n--- TEST 2: Identical attributes (SHOULD prune) ---")
minimized2 = _minimize_html(sample_html_identical)
print(f"Original length: {len(sample_html_identical)}")
print(f"Minimized length: {len(minimized2)}")
print(minimized2)

# Case 3: Mixed unique attributes
sample_html_mixed = """
<html>
<body>
    <div class="product" data-id="1">P1</div>
    <div class="product" data-id="2">P2</div>
    <div class="product" data-id="1">P3 (Repeat of P1)</div>
</body>
</html>
"""

print("\n--- TEST 3: Mixed unique attributes (Should only prune P3) ---")
minimized3 = _minimize_html(sample_html_mixed)
print(minimized3)
