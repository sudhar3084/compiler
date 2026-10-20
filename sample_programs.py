"""
sample_programs.py — Curated Example Programs for CompilerX.

Provides 7 ready-to-run sample programs demonstrating lexical/syntax/semantic analysis,
arithmetic precedence, floating-point math, boolean conditions, if/else branching,
while loops, code optimization (constant folding, propagation, CSE, DCE), and error diagnostics.
"""

from typing import Dict

SAMPLE_PROGRAMS: Dict[str, Dict[str, str]] = {
    "1. Quick Start: Arithmetic & If/Else (Default)": {
        "filename": "01_basic_arithmetic_and_branch.cx",
        "description": "Demonstrates integer declarations, operator precedence (x + y * 2), print(), and if/else branching.",
        "code": """// Example 1: Basic Arithmetic, Precedence & Conditional Branching
int x = 10;
int y = 20;
int result = x + y * 2;

print(result);

if (result > 30) {
    print("Result is greater than 30");
} else {
    print("Result is 30 or less");
}
""",
    },
    "2. Code Optimization Showcase (Folding, Propagation, CSE & DCE)": {
        "filename": "02_optimization_showcase.cx",
        "description": "Demonstrates Constant Folding, Constant Propagation, Algebraic Identity Simplification, Common Subexpression Elimination, and Dead-Code Elimination.",
        "code": """// Example 2: Compiler Optimization Showcase
// Watch how CompilerX folds constants, simplifies identities, and prunes dead branches!

int base = 4 * 5 + 10;          // Constant folding: 4 * 5 + 10 -> 30
int factor = 2;
int scaled = (base * factor) + 0; // Propagation + Identity (+ 0): -> 60
int copy_val = scaled * 1;        // Algebraic simplification (* 1): -> 60

print("Computed Value:", copy_val);

// Constant condition branch -> else branch is statically eliminated as dead code!
if (copy_val == 60) {
    print("Optimization preserved exact semantics!");
} else {
    print("Unreachable dead branch removed by optimizer");
}
""",
    },
    "3. While Loops: Factorial & Even Sum Calculator": {
        "filename": "03_while_loop_factorial.cx",
        "description": "Demonstrates while loops, modulo (%) operator, compound assignments, and loop-safe optimization.",
        "code": """// Example 3: Iterative Factorial (5!) & Sum of Even Numbers (1..10)
int n = 5;
int factorial = 1;
int counter = 1;

while (counter <= n) {
    factorial = factorial * counter;
    counter = counter + 1;
}

print("Factorial of 5 is:");
print(factorial);

// Sum all even numbers from 1 to 10 using modulo (%)
int i = 1;
int even_sum = 0;
while (i <= 10) {
    if (i % 2 == 0) {
        even_sum = even_sum + i;
    }
    i = i + 1;
}

print("Sum of even numbers (1 to 10):");
print(even_sum);
""",
    },
    "4. Floating-Point Math & Boolean Logic (Physics & Grading)": {
        "filename": "04_float_and_boolean_logic.cx",
        "description": "Demonstrates float variables, mixed int/float widening, logical operators (&&, ||, !), and else-if ladders.",
        "code": """// Example 4: Floating-Point Calculations & Boolean Conditions
float celsius = 37.5;
float fahrenheit = (celsius * 1.8) + 32.0;
bool is_fever = fahrenheit >= 99.5;

print("Temperature in Fahrenheit:");
print(fahrenheit);

int score = 88;
bool attendance_ok = true;

if (score >= 90 && attendance_ok) {
    print("Grade: A+");
} else if (score >= 80 && attendance_ok) {
    print("Grade: A");
} else if (score >= 70 || attendance_ok) {
    print("Grade: B");
} else {
    print("Grade: Needs Improvement");
}

if (is_fever && !false) {
    print("Status: Elevated temperature detected");
}
""",
    },
    "5. Fibonacci Sequence & Primality Test": {
        "filename": "05_fibonacci_and_prime_check.cx",
        "description": "Generates Fibonacci numbers and tests whether a number is prime using nested control structures.",
        "code": """// Example 5: Fibonacci Generator & Prime Number Checker
int terms = 7;
int a = 0;
int b = 1;
int step = 0;

print("First 7 Fibonacci numbers:");
while (step < terms) {
    print(a);
    int next_val = a + b;
    a = b;
    b = next_val;
    step = step + 1;
}

// Check if 29 is a prime number
int candidate = 29;
int divisor = 2;
bool is_prime = true;

while (divisor * divisor <= candidate) {
    if (candidate % divisor == 0) {
        is_prime = false;
    }
    divisor = divisor + 1;
}

if (is_prime) {
    print("29 is a prime number");
} else {
    print("29 is composite");
}
""",
    },
    "6. Common Subexpression & Algebraic Simplification Demo": {
        "filename": "06_cse_and_algebraic_demo.cx",
        "description": "Demonstrates local Common Subexpression Elimination (CSE) and algebraic identities on dynamic loop-computed variables.",
        "code": """// Example 6: Common Subexpression Elimination (CSE) & Algebraic Identities
int a = 12;
int b = 5;

// Loop makes 'a' and 'b' dynamic runtime values (a = 15, b = 8)
while (b < 8) {
    a = a + 1;
    b = b + 1;
}

// 'a + b' is computed twice in the same basic block -> CSE reuses first result!
// Algebraic identities (* 1, + 0, a - a, b * 0) are simplified automatically.
int first_calc = (a + b) * 1;
int second_calc = (a + b) + 0;
int zero_check = (a - a) + (b * 0);

print(first_calc);
print(second_calc);
print(zero_check);
""",
    },
    "7. Semantic Error Diagnostics Demo (Intentional Errors)": {
        "filename": "07_error_diagnostics_demo.cx",
        "description": "Demonstrates CompilerX's error reporting for duplicate declarations, undeclared variables, and type mismatches.",
        "code": """// Example 7: Intentional Semantic Errors for Live Demo
int count = 10;
int count = 20;            // Error 1: Duplicate declaration in same scope

int bad_type = "hello";    // Error 2: Type mismatch (string assigned to int)
float ratio = 15.5 % 2.0;  // Error 3: Modulo '%' requires integer operands

print(undeclared_var + 5); // Error 4: Undeclared variable reference
""",
    },
}
