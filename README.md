# ⚡ CompilerX — A Mini Compiler with Code Optimization and Execution

**CompilerX** is a complete, modular educational compiler and execution environment built in **Python** and **Streamlit**. It demonstrates the entire 7-phase compiler pipeline—from raw source code input in a C-like language to lexical scanning, recursive-descent AST construction, static semantic type checking, Three-Address Code (TAC) generation, multi-pass intermediate code optimization, target bytecode/assembly generation, and safe sandboxed program execution.

## 1. Key Features & 7 Compiler Phases

| Phase | Module | Capabilities |
| :--- | :--- | :--- |
| **1. Lexical Analysis** | `lexer.py` | Scans source code into strongly-typed `Token` objects (`line`, `column`, `type`, `value`). Supports `//` and `/* ... */` comments, string escapes, `int`/`float`/`bool` literals, and reports lexical errors (invalid characters, malformed floats, unterminated strings/comments). |
| **2. Syntax Analysis** | `parser.py`, `ast_nodes.py` | Recursive-descent parser with full operator precedence (`||`, `&&`, `==`/`!=`, `<`/`<=`/`>`/`>=`, `+`/`-`, `*`/`/`/`%`, unary `-`/`!`), panic-mode error recovery, ASCII tree export, JSON export, and Graphviz DOT visualization. |
| **3. Semantic Analysis** | `semantic_analyzer.py` | Hierarchical lexical scope `SymbolTable` (`global`, `if_then`, `while_body`, etc.). Checks duplicate declarations, undeclared variables, type compatibility (`int` to `float` widening, invalid modulo on floats, invalid string arithmetic), and compile-time division by zero. |
| **4. Intermediate Code (TAC)** | `intermediate_code.py` | Generates linear Three-Address Code (`TACInstruction`) using temporaries (`t1`, `t2`, ...) and control-flow labels (`L1`, `L2`, ...). |
| **5. Code Optimization** | `optimizer.py` | Iterative multi-pass optimizer implementing **Constant Folding**, **Constant Propagation** (loop-aware), **Algebraic Identity Simplification** (`x + 0`, `x * 1`, `x * 0`, `x - x`), **Local Common Subexpression Elimination (CSE)**, and **Dead-Code Elimination (DCE)** (unreachable branches, unused labels, dead temporaries). |
| **6. Target Code Generation** | `code_generator.py` | Translates TAC into **Stack-VM Bytecode** (`PUSH_CONST`, `LOAD`, `STORE`, `ADD`, `MUL`, `CMP_GT`, `JZ`, `JMP`, `PRINT`, `HALT`) and **Register Pseudo-Assembly** (`MOV`, `STR`, `ADD`, `CMP`, `JEQ`, `OUT_LN`). |
| **7. Program Execution** | `interpreter.py` | Safe, deterministic `TACInterpreter` and `StackVMInterpreter` (zero `eval()` or `exec()`). Enforces configurable step limits (`max_steps = 10,000`) and output line limits (`max_output_lines = 500`), catches runtime division by zero, and automatically verifies semantic equivalence between unoptimized and optimized TAC. |

## 2. Project Directory Structure

```text
CompilerX/
├── app.py                        # Streamlit web UI & CLI runner (--cli)
├── ast_nodes.py                  # AST node dataclasses, ASCII tree & Graphviz DOT builders
├── lexer.py                      # Phase 1: Lexical Analyzer (Scanner)
├── parser.py                     # Phase 2: Recursive-Descent Syntax Analyzer
├── semantic_analyzer.py          # Phase 3: Scoped Symbol Table & Static Type Checker
├── intermediate_code.py          # Phase 4: Three-Address Code (TAC) Generator
├── optimizer.py                  # Phase 5: Multi-Pass TAC Optimizer & Metrics Tracker
├── code_generator.py             # Phase 6: Stack-VM & Pseudo-Assembly Code Generator
├── interpreter.py                # Phase 7: Safe Interpreter & CompilerPipeline Facade
├── sample_programs.py            # Curated sample programs loaded in the Streamlit UI
├── requirements.txt              # Project dependencies (streamlit>=1.32.0)
├── README.md                     # Complete project documentation
├── VS_CODE_WINDOWS_11_GUIDE.md   # Step-by-step setup guide for VS Code on Windows 11
├── COLLEGE_DEMO_GUIDE.md         # Live demonstration & viva guide for college reviews
├── examples/                     # Standalone .cx sample programs
│   ├── 01_basic_arithmetic_and_branch.cx
│   ├── 02_optimization_showcase.cx
│   ├── 03_while_loop_factorial.cx
│   ├── 04_float_and_boolean_logic.cx
│   ├── 05_fibonacci_and_prime_check.cx
│   ├── 06_cse_and_algebraic_demo.cx
│   └── 07_error_diagnostics_demo.cx
└── tests/                        # Automated unit test suite
    └── test_compiler.py          # 23 unit tests covering all 7 compiler phases
```

## 3. Installation & Quick Start

### Prerequisites
- **Python 3.9+** (Python 3.10, 3.11, or 3.12 recommended)

### Step 1: Create and Activate a Virtual Environment
```bash
# Navigate into the project directory
cd CompilerX

# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Activate on macOS / Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch the Streamlit Web Interface
```bash
streamlit run app.py
```
The interface will open automatically at `http://localhost:8501`.

### Step 4: Run from Command Line (Optional CLI Mode)
You can also compile and run any `.cx` file directly in the terminal without launching a browser:
```bash
# Run default example program
python app.py --cli

# Run a specific example file
python app.py --cli examples/03_while_loop_factorial.cx
```

### Step 5: Run the Automated Unit Tests
```bash
python -m unittest discover -s tests -v
```

## 4. Custom Language Specification (`.cx`)

### Data Types & Variable Declarations
- `int`: Signed integer values (`int x = 10;`)
- `float`: Floating-point values (`float temp = 37.5;`)
- `bool`: Boolean truth values (`bool active = true;`)
- `string`: Double- or single-quoted string literals (`string msg = "Hello";`)

### Supported Operators (Ordered from Highest to Lowest Precedence)
1. **Parentheses**: `( expr )`
2. **Unary Operators**: `-` (arithmetic negation), `+` (unary plus), `!` or `not` (logical negation)
3. **Multiplicative**: `*`, `/`, `%` (modulo requires `int` operands)
4. **Additive**: `+`, `-`
5. **Relational**: `<`, `<=`, `>`, `>=`
6. **Equality**: `==`, `!=`
7. **Logical AND**: `&&` (or keyword `and`)
8. **Logical OR**: `||` (or keyword `or`)
9. **Assignments**: `=`, `+=`, `-=`, `*=`, `/=`

### Control Flow & Statements
- **Conditional Statements**: `if (condition) { ... } else if (condition) { ... } else { ... }`
- **Loops**: `while (condition) { ... }`
- **Output**: `print(expr);` or multi-argument `print("Label:", expr);`
- **Comments**: Single-line `// ...` and multi-line `/* ... */`

### Example Program Walkthrough
```c
int x = 10;
int y = 20;
int result = x + y * 2;

print(result);

if (result > 30) {
    print("Result is greater than 30");
} else {
    print("Result is 30 or less");
}
```
**Expected Output:**
```text
50
Result is greater than 30
```

## 5. Documented Language Limitations

To keep the compiler architecture clean, verifiable, and focused on core Compiler Design principles for academic demonstration, the following boundaries apply:
1. **No User-Defined Functions or Recursion**: All statements execute within the main program entry point and nested lexical blocks (`if`/`else`/`while`), with built-in `print()` supported natively.
2. **No Arrays, Pointers, or Structs**: Only scalar types (`int`, `float`, `bool`, `string`) are supported.
3. **Loop Constructs**: Iteration is expressed via `while` loops (`for` and `do-while` loops can be written equivalently using `while`).
4. **No String Concatenation via `+`**: The `+` operator is strictly numeric (`int`/`float`); multi-item printing is supported via comma-separated arguments in `print("Value:", x);`.
5. **Bounded Execution Steps**: The interpreter enforces a configurable step limit (default `10,000` steps) to guarantee termination and protect the UI against infinite `while (true)` loops.
