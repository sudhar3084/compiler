# 🎓 College Project Demonstration & Viva Guide: CompilerX

This guide prepares you to present **CompilerX — A Mini Compiler with Code Optimization and Execution** during a Compiler Design lab review, mini-project evaluation, or viva examination.

## 1. 60-Second Project Pitch (Opening Statement)

> *"CompilerX is an end-to-end educational compiler written in Python with an interactive Streamlit dashboard. Unlike simple wrappers that pass source code to Python's `eval()`, CompilerX implements all seven classical compiler phases from scratch: a hand-written Lexical Scanner, a Recursive-Descent Parser that builds an Abstract Syntax Tree, a Scoped Semantic & Type Analyzer, a Three-Address Code (TAC) Intermediate Code Generator, a Multi-Pass Code Optimizer supporting Constant Folding, Constant Propagation, Algebraic Simplification, Common Subexpression Elimination, and Dead-Code Elimination, a Stack-VM and Pseudo-Assembly Target Code Generator, and a safe Virtual Machine Interpreter with infinite-loop protection."*

## 2. Phase-by-Phase Technical Explanation

Use the default example program (`1. Quick Start: Arithmetic & If/Else`) to walk your evaluator through each tab in the UI:

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

### Phase 1: Lexical Analysis (`lexer.py`) — *Tab 2: Lexical Analysis*
- **What it does**: Reads raw characters and groups them into meaningful **lexemes** mapped to `Token(type, value, line, column)`.
- **How it works**: Uses a deterministic character-by-character finite-state scan. Strips whitespace and comments (`//` and `/* ... */`), recognizes keywords (`int`, `float`, `if`, `else`, `while`, `print`), parses numeric and string literals, and tracks exact `line` and `column` coordinates.
- **Error Handling**: Detects invalid symbols (`@`, `$`, `#`), malformed numbers (`12.34.56` or `99abc`), and unterminated strings or comments without crashing.

### Phase 2: Syntax Analysis (`parser.py`, `ast_nodes.py`) — *Tab 3: Syntax Analysis (AST)*
- **What it does**: Validates token grammar and builds a hierarchical **Abstract Syntax Tree (AST)**.
- **How it works**: Implements a **Recursive-Descent Parser** where operator precedence is encoded directly into the call hierarchy:
  `_parse_logical_or` -> `_parse_logical_and` -> `_parse_equality` -> `_parse_comparison` -> `_parse_additive` -> `_parse_multiplicative` -> `_parse_unary` -> `_parse_primary`.
- **Why `x + y * 2` parses correctly**: Because `_parse_additive` calls `_parse_multiplicative` for its right-hand operand, `y * 2` is bound deeper in the tree as a child `BinaryOp('*')` under `BinaryOp('+')`.
- **Error Recovery**: Uses **Panic-Mode Synchronization** (synchronizing on `;` and `}`) so a missing semicolon on line 1 does not trigger cascading false errors on every subsequent line.

### Phase 3: Semantic Analysis (`semantic_analyzer.py`) — *Tab 4: Semantic Analysis & Symbols*
- **What it does**: Enforces context-sensitive language rules that a context-free grammar cannot catch.
- **How it works**: Traverses the AST while maintaining a scoped `SymbolTable` (`global`, `if_then_1`, `while_body_1`).
- **Checks Performed**:
  1. **Undeclared Variable Check**: Rejects references to variables not declared in the current or enclosing scope.
  2. **Duplicate Declaration Check**: Prevents declaring the same variable twice in the same scope.
  3. **Type Inference & Compatibility**: Allows safe implicit widening (`int` -> `float`), rejects assigning `string` to `int`, and enforces that modulo (`%`) only operates on `int` operands.
  4. **Compile-Time Division by Zero**: Statically catches `x / 0` or `x % 0`.

### Phase 4: Intermediate Code Generation (`intermediate_code.py`) — *Tab 5: Intermediate Code (TAC)*
- **What it does**: Translates the hierarchical AST into machine-independent **Three-Address Code (TAC)** quadruples (`Op`, `Arg1`, `Arg2`, `Result`).
- **How it works**: Breaks complex expressions into simple binary operations using compiler-generated temporaries (`t1`, `t2`, `t3`) and translates `if/else` and `while` constructs into conditional jumps (`if_false t3 goto L1`) and labels (`L1:`, `L2:`).
- **Original TAC generated for the default example (13 instructions)**:
  ```text
      x = 10
      y = 20
      t1 = y * 2
      t2 = x + t1
      result = t2
      print result
      t3 = result > 30
      if_false t3 goto L1
      print "Result is greater than 30"
      goto L2
  L1:
      print "Result is 30 or less"
  L2:
  ```

### Phase 5: Code Optimization (`optimizer.py`) — *Tab 1: Code Optimization & Comparison*
- **What it does**: Transforms Original TAC into a smaller, faster, semantically equivalent Optimized TAC.
- **5 Optimization Passes Implemented**:
  1. **Constant Propagation**: Substitutes `y = 20` and `x = 10` into `t1 = 20 * 2` and `t2 = 10 + 40`. Importantly, `_find_multi_assigned_vars()` detects variables mutated inside `while` loops so loop counters are never unsoundly treated as constants!
  2. **Constant Folding**: Evaluates `20 * 2 -> 40`, `10 + 40 -> 50`, and `50 > 30 -> true` at compile time.
  3. **Algebraic Identity Simplification**: Simplifies `expr + 0 -> expr`, `expr * 1 -> expr`, `expr * 0 -> 0`, `a - a -> 0`, and `a == a -> true`.
  4. **Common Subexpression Elimination (CSE)**: Reuses previously computed expressions (`a + b`) within the same basic block instead of recomputing them.
  5. **Dead-Code & Branch Elimination (DCE)**: Recognizes `if_false true goto L1` can never jump, removes the branch, eliminates the unreachable `else` block (`print "Result is 30 or less"`), removes unreferenced labels (`L1:`, `L2:`), and prunes unused temporaries (`t1`, `t2`, `t3`).
- **Optimized TAC for the default example (5 instructions — 61.5% reduction!)**:
  ```text
      x = 10
      y = 20
      result = 50
      print 50
      print "Result is greater than 30"
  ```

### Phase 6: Target Code Generation (`code_generator.py`) — *Tab 6: Target Code & Assembly*
- **What it does**: Lowers TAC into two low-level target representations:
  1. **Stack-VM Bytecode**: Uses `PUSH_CONST`, `LOAD`, `STORE`, `ADD`, `MUL`, `CMP_GT`, `JZ`, `JMP`, `PRINT`, and `HALT`.
  2. **Register Pseudo-Assembly**: Uses 8 virtual registers (`R0`–`R7`) with `MOV`, `STR`, `ADD`, `CMP`, `JEQ`, `OUT_LN`, and `HALT`.

### Phase 7: Program Execution (`interpreter.py`) — *Top Output Console & Tab 7*
- **What it does**: Safely executes both the **Unoptimized TAC** and **Optimized TAC** (and Stack-VM instructions) without `eval()` or `exec()`.
- **Safety & Verification**:
  - Automatically checks `report.outputs_match` to prove that optimization preserved exact program behavior (`50` and `Result is greater than 30`).
  - Protects against infinite loops (`while (true)`) via `max_steps` and catches runtime division by zero (`100 / d` when `d` becomes `0` at runtime).

## 3. Recommended Live Demo Script (5 Minutes)

1. **Demo 1 — Default Program & Optimization (1.5 mins)**:
   - Select **"1. Quick Start: Arithmetic & If/Else (Default)"** and click **Compile & Run**.
   - Point out the output console (`50` and `Result is greater than 30`), then open **Tab 1 (Code Optimization & Comparison)** to show how 13 TAC instructions were reduced to 5 instructions (61.5% reduction) by folding `10 + 20 * 2 = 50` and pruning the unreachable `else` branch.
2. **Demo 2 — AST & Symbol Table Inspection (1 min)**:
   - Click **Tab 2 (Lexical Analysis)** to show the Token Table, **Tab 3 (Syntax Analysis)** to show the interactive Graphviz AST diagram, and **Tab 4 (Semantic Analysis)** to show the Scoped Symbol Table.
3. **Demo 3 — Loops & CSE Optimization (1.5 mins)**:
   - Select **"3. While Loops: Factorial & Even Sum Calculator"** and **"6. Common Subexpression & Algebraic Simplification Demo"** from the sidebar.
   - Show that loop counters execute accurately (`5! = 120`, even sum = `30`) and that Common Subexpression Elimination reuses `a + b` after the loop.
4. **Demo 4 — Error Diagnostics (1 min)**:
   - Select **"7. Semantic Error Diagnostics Demo (Intentional Errors)"** to show how duplicate declarations, type mismatches, and undeclared variables are caught with exact line and column numbers.

## 4. Common Viva Questions & Model Answers

- **Q1: Why didn't you use Python's `eval()` or `exec()` to run the code?**
  - *Answer*: Using `eval()` bypasses the compiler pipeline and poses severe security risks (arbitrary code execution). Instead, CompilerX compiles source code through an AST into Three-Address Code and Stack-VM instructions, and executes those instructions step-by-step in a custom virtual machine with bounded step limits.
- **Q2: How does your optimizer avoid breaking `while` loops during Constant Propagation?**
  - *Answer*: Before propagating constants across basic blocks, `_find_multi_assigned_vars()` scans the TAC to identify any variable reassigned more than once or modified after a `LABEL`. At any loop header (`LABEL`), those mutable variables are invalidated from the constant environment so loop conditions are always evaluated dynamically at runtime.
- **Q3: How does the parser enforce that `*` has higher precedence than `+`?**
  - *Answer*: In a recursive-descent parser, higher-precedence operators appear deeper in the grammar production chain. `_parse_additive()` calls `_parse_multiplicative()` to parse its left and right operands, ensuring multiplication nodes are constructed lower in the AST and evaluated first.
