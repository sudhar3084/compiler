"""
interpreter.py — Safe Execution Engine & Unified Pipeline Facade for CompilerX.

Executes compiled programs safely WITHOUT using Python's `eval()` or `exec()`.
Provides:
1. `TACInterpreter`: Executes Three-Address Code (TAC) instructions directly with
   configurable step limits and output line limits to prevent infinite loops.
2. `StackVMInterpreter`: Executes generated Stack-VM target instructions on a virtual
   operand stack machine.
3. `CompilerPipeline`: Orchestrates all 7 compiler phases end-to-end and verifies
   that original and optimized code produce identical runtime output.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ast_nodes import Program, ast_to_graphviz_dot, format_ast_tree
from code_generator import TargetCodeGenerator, TargetInstruction, format_target_code
from intermediate_code import IntermediateCodeGenerator, TACInstruction, format_tac
from lexer import Lexer, LexicalError, Token, TokenType
from optimizer import OptimizationMetrics, TACOptimizer, is_constant_operand, is_temp_var
from parser import Parser, SyntaxErrorDetail
from semantic_analyzer import SemanticAnalyzer, SemanticErrorDetail, SemanticWarning, SymbolTable


@dataclass
class RuntimeErrorDetail:
    """Represents a runtime execution error (e.g., division by zero, infinite loop limit)."""
    message: str
    line: int = 1

    def format(self) -> str:
        return f"[Runtime Error] Line {self.line}: {self.message}"


@dataclass
class ExecutionResult:
    """Holds the result of running a compiled program."""
    output_lines: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    steps_executed: int = 0
    execution_time_ms: float = 0.0
    runtime_error: Optional[RuntimeErrorDetail] = None

    @property
    def output_text(self) -> str:
        return "\n".join(self.output_lines)

    @property
    def succeeded(self) -> bool:
        return self.runtime_error is None


class TACInterpreter:
    """Safe interpreter for Three-Address Code (TAC) instructions."""

    def __init__(self, max_steps: int = 10000, max_output_lines: int = 500):
        self.max_steps = max_steps
        self.max_output_lines = max_output_lines

    def execute(
        self,
        instructions: List[TACInstruction],
        declared_types: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        start_time = time.perf_counter()
        env: Dict[str, Any] = {}
        var_types = declared_types or {}
        output_lines: List[str] = []
        inline_buffer: List[str] = []

        label_map: Dict[str, int] = {}
        for idx, instr in enumerate(instructions):
            if instr.op == "LABEL" and instr.result:
                label_map[instr.result] = idx

        pc = 0
        steps = 0
        num_instr = len(instructions)

        while 0 <= pc < num_instr:
            steps += 1
            if steps > self.max_steps:
                err = RuntimeErrorDetail(
                    message=f"Execution step limit exceeded ({self.max_steps} steps). Possible infinite loop detected.",
                    line=instructions[pc].line,
                )
                return self._finalize(output_lines, inline_buffer, env, steps, start_time, err)

            instr = instructions[pc]
            op = instr.op

            if op == "LABEL":
                pc += 1
                continue

            if op == "GOTO":
                if instr.result not in label_map:
                    err = RuntimeErrorDetail(
                        message=f"Undefined jump target label '{instr.result}'",
                        line=instr.line,
                    )
                    return self._finalize(output_lines, inline_buffer, env, steps, start_time, err)
                pc = label_map[instr.result]
                continue

            if op == "IF_FALSE":
                cond_val = self._resolve(instr.arg1, env)
                if not bool(cond_val):
                    if instr.result not in label_map:
                        err = RuntimeErrorDetail(
                            message=f"Undefined branch target label '{instr.result}'",
                            line=instr.line,
                        )
                        return self._finalize(output_lines, inline_buffer, env, steps, start_time, err)
                    pc = label_map[instr.result]
                else:
                    pc += 1
                continue

            if op == "PRINT_INLINE":
                val = self._resolve(instr.arg1, env)
                inline_buffer.append(self._format_value(val))
                pc += 1
                continue

            if op == "PRINT":
                val = self._resolve(instr.arg1, env)
                inline_buffer.append(self._format_value(val))
                line_str = " ".join(inline_buffer)
                inline_buffer.clear()
                output_lines.append(line_str)
                if len(output_lines) > self.max_output_lines:
                    err = RuntimeErrorDetail(
                        message=f"Maximum output limit ({self.max_output_lines} lines) exceeded.",
                        line=instr.line,
                    )
                    return self._finalize(output_lines, inline_buffer, env, steps, start_time, err)
                pc += 1
                continue

            if op == "ASSIGN":
                val = self._resolve(instr.arg1, env)
                target_type = instr.var_type or var_types.get(instr.result or "")
                val = self._coerce_type(val, target_type)
                if instr.result:
                    env[instr.result] = val
                pc += 1
                continue

            if op in ("NEG", "NOT"):
                val = self._resolve(instr.arg1, env)
                res = (-val) if op == "NEG" else (not bool(val))
                if instr.result:
                    env[instr.result] = res
                pc += 1
                continue

            left = self._resolve(instr.arg1, env)
            right = self._resolve(instr.arg2, env)
            err, res = self._eval_binary(op, left, right, instr.line, instr.var_type)
            if err is not None:
                return self._finalize(output_lines, inline_buffer, env, steps, start_time, err)

            target_type = instr.var_type or var_types.get(instr.result or "")
            res = self._coerce_type(res, target_type)
            if instr.result:
                env[instr.result] = res
            pc += 1

        return self._finalize(output_lines, inline_buffer, env, steps, start_time, None)

    def _resolve(self, operand: Any, env: Dict[str, Any]) -> Any:
        if is_constant_operand(operand):
            if isinstance(operand, tuple) and len(operand) == 2 and operand[0] == "str":
                return operand[1]
            return operand
        if isinstance(operand, str):
            return env.get(operand, 0)
        return operand

    @staticmethod
    def _coerce_type(val: Any, target_type: Optional[str]) -> Any:
        if target_type == "float" and isinstance(val, int) and not isinstance(val, bool):
            return float(val)
        if target_type == "int" and isinstance(val, float):
            return int(val)
        return val

    @staticmethod
    def _format_value(val: Any) -> str:
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, float):
            return f"{val:.6g}" if val != int(val) else f"{val:.1f}"
        return str(val)

    @staticmethod
    def _eval_binary(
        op: str, left: Any, right: Any, line: int, var_type: Optional[str] = None
    ):
        try:
            if op == "+":
                return None, left + right
            if op == "-":
                return None, left - right
            if op == "*":
                return None, left * right
            if op == "/":
                if right == 0 or right == 0.0:
                    return RuntimeErrorDetail("Division by zero during program execution", line), None
                if isinstance(left, int) and isinstance(right, int) and var_type != "float":
                    return None, int(left / right)
                return None, left / right
            if op == "%":
                if right == 0 or right == 0.0:
                    return RuntimeErrorDetail("Modulo by zero during program execution", line), None
                return None, left % right
            if op == "==":
                return None, left == right
            if op == "!=":
                return None, left != right
            if op == "<":
                return None, left < right
            if op == "<=":
                return None, left <= right
            if op == ">":
                return None, left > right
            if op == ">=":
                return None, left >= right
            if op == "&&":
                return None, bool(left) and bool(right)
            if op == "||":
                return None, bool(left) or bool(right)
        except Exception as exc:
            return RuntimeErrorDetail(f"Invalid runtime operation '{op}': {exc}", line), None

        return RuntimeErrorDetail(f"Unknown operator '{op}'", line), None

    @staticmethod
    def _finalize(
        output_lines: List[str],
        inline_buffer: List[str],
        env: Dict[str, Any],
        steps: int,
        start_time: float,
        runtime_error: Optional[RuntimeErrorDetail],
    ) -> ExecutionResult:
        if inline_buffer:
            output_lines.append(" ".join(inline_buffer))
        user_vars = {k: v for k, v in env.items() if not is_temp_var(k)}
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        return ExecutionResult(
            output_lines=output_lines,
            variables=user_vars,
            steps_executed=steps,
            execution_time_ms=elapsed_ms,
            runtime_error=runtime_error,
        )


class StackVMInterpreter:
    """Executes Stack-Based Virtual Machine Target Instructions directly."""

    VM_OP_TO_SYM = {
        "ADD": "+",
        "SUB": "-",
        "MUL": "*",
        "DIV": "/",
        "MOD": "%",
        "CMP_EQ": "==",
        "CMP_NEQ": "!=",
        "CMP_LT": "<",
        "CMP_LTE": "<=",
        "CMP_GT": ">",
        "CMP_GTE": ">=",
        "AND": "&&",
        "OR": "||",
    }

    def __init__(self, max_steps: int = 25000, max_output_lines: int = 500):
        self.max_steps = max_steps
        self.max_output_lines = max_output_lines

    def execute(self, instructions: List[TargetInstruction]) -> ExecutionResult:
        start_time = time.perf_counter()
        stack: List[Any] = []
        memory: Dict[str, Any] = {}
        output_lines: List[str] = []
        inline_buffer: List[str] = []

        label_map: Dict[str, int] = {}
        for idx, instr in enumerate(instructions):
            if instr.opcode == "LABEL" and instr.operand:
                label_map[str(instr.operand)] = idx

        pc = 0
        steps = 0
        n = len(instructions)

        while 0 <= pc < n:
            steps += 1
            if steps > self.max_steps:
                err = RuntimeErrorDetail(
                    f"Stack-VM step limit exceeded ({self.max_steps} steps).",
                    instructions[pc].line,
                )
                return TACInterpreter._finalize(
                    output_lines, inline_buffer, memory, steps, start_time, err
                )

            instr = instructions[pc]
            op = instr.opcode

            if op == "HALT":
                break
            if op == "LABEL":
                pc += 1
                continue
            if op == "PUSH_CONST":
                val = instr.operand
                if isinstance(val, tuple) and len(val) == 2 and val[0] == "str":
                    val = val[1]
                stack.append(val)
                pc += 1
                continue
            if op == "LOAD":
                stack.append(memory.get(str(instr.operand), 0))
                pc += 1
                continue
            if op == "STORE":
                val = stack.pop() if stack else 0
                memory[str(instr.operand)] = val
                pc += 1
                continue
            if op == "JMP":
                pc = label_map[str(instr.operand)]
                continue
            if op == "JZ":
                cond = stack.pop() if stack else False
                if not bool(cond):
                    pc = label_map[str(instr.operand)]
                else:
                    pc += 1
                continue
            if op == "PRINT_INLINE":
                val = stack.pop() if stack else ""
                inline_buffer.append(TACInterpreter._format_value(val))
                pc += 1
                continue
            if op == "PRINT":
                val = stack.pop() if stack else ""
                inline_buffer.append(TACInterpreter._format_value(val))
                output_lines.append(" ".join(inline_buffer))
                inline_buffer.clear()
                if len(output_lines) > self.max_output_lines:
                    err = RuntimeErrorDetail(
                        f"Maximum output limit ({self.max_output_lines} lines) exceeded.",
                        instr.line,
                    )
                    return TACInterpreter._finalize(
                        output_lines, inline_buffer, memory, steps, start_time, err
                    )
                pc += 1
                continue
            if op in ("NEG", "NOT"):
                val = stack.pop() if stack else 0
                stack.append((-val) if op == "NEG" else (not bool(val)))
                pc += 1
                continue
            if op in self.VM_OP_TO_SYM:
                right = stack.pop() if stack else 0
                left = stack.pop() if stack else 0
                sym_op = self.VM_OP_TO_SYM[op]
                err, res = TACInterpreter._eval_binary(sym_op, left, right, instr.line)
                if err is not None:
                    return TACInterpreter._finalize(
                        output_lines, inline_buffer, memory, steps, start_time, err
                    )
                stack.append(res)
                pc += 1
                continue

            pc += 1

        return TACInterpreter._finalize(
            output_lines, inline_buffer, memory, steps, start_time, None
        )


@dataclass
class CompilationReport:
    """Comprehensive artifact containing outputs and metrics from all 7 compiler phases."""
    source_code: str
    tokens: List[Token] = field(default_factory=list)
    lexical_errors: List[LexicalError] = field(default_factory=list)
    ast: Optional[Program] = None
    ast_tree_str: str = ""
    ast_graphviz_dot: str = ""
    syntax_errors: List[SyntaxErrorDetail] = field(default_factory=list)
    symbol_table: Optional[SymbolTable] = None
    semantic_errors: List[SemanticErrorDetail] = field(default_factory=list)
    semantic_warnings: List[SemanticWarning] = field(default_factory=list)
    original_tac: List[TACInstruction] = field(default_factory=list)
    optimized_tac: List[TACInstruction] = field(default_factory=list)
    optimization_metrics: Optional[OptimizationMetrics] = None
    unoptimized_target_code: List[TargetInstruction] = field(default_factory=list)
    optimized_target_code: List[TargetInstruction] = field(default_factory=list)
    pseudo_assembly: str = ""
    unoptimized_execution: Optional[ExecutionResult] = None
    optimized_execution: Optional[ExecutionResult] = None
    compilation_time_ms: float = 0.0

    @property
    def has_errors(self) -> bool:
        return bool(self.lexical_errors or self.syntax_errors or self.semantic_errors)

    @property
    def all_error_messages(self) -> List[str]:
        msgs = [e.format() for e in self.lexical_errors]
        msgs.extend(e.format() for e in self.syntax_errors)
        msgs.extend(e.format() for e in self.semantic_errors)
        if self.optimized_execution and self.optimized_execution.runtime_error:
            msgs.append(self.optimized_execution.runtime_error.format())
        return msgs

    @property
    def outputs_match(self) -> bool:
        if not self.unoptimized_execution or not self.optimized_execution:
            return True
        return self.unoptimized_execution.output_text == self.optimized_execution.output_text


class CompilerPipeline:
    """End-to-end facade orchestrating all 7 phases of CompilerX."""

    def __init__(self, max_steps: int = 10000, max_output_lines: int = 500):
        self.max_steps = max_steps
        self.max_output_lines = max_output_lines

    def compile_and_run(self, source_code: str, run_program: bool = True) -> CompilationReport:
        t0 = time.perf_counter()
        report = CompilationReport(source_code=source_code)

        # Phase 1: Lexical Analysis
        lexer = Lexer(source_code)
        tokens, lex_errors = lexer.tokenize()
        report.tokens = [t for t in tokens if t.type != TokenType.EOF]
        report.lexical_errors = lex_errors

        if lex_errors:
            report.compilation_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            return report

        # Phase 2: Syntax Analysis
        parser = Parser(tokens)
        ast_root, syn_errors = parser.parse()
        report.ast = ast_root
        report.syntax_errors = syn_errors

        if syn_errors:
            report.compilation_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            return report

        # Phase 3: Semantic Analysis
        sem_analyzer = SemanticAnalyzer()
        sym_table, sem_errors, sem_warnings = sem_analyzer.analyze(ast_root)
        report.symbol_table = sym_table
        report.semantic_errors = sem_errors
        report.semantic_warnings = sem_warnings
        report.ast_tree_str = format_ast_tree(ast_root)
        report.ast_graphviz_dot = ast_to_graphviz_dot(ast_root)

        if sem_errors:
            report.compilation_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            return report

        # Phase 4: Intermediate Code Generation (TAC)
        icg = IntermediateCodeGenerator()
        original_tac = icg.generate(ast_root)
        report.original_tac = original_tac

        # Phase 5: Code Optimization
        optimizer = TACOptimizer()
        optimized_tac, opt_metrics = optimizer.optimize(original_tac)
        report.optimized_tac = optimized_tac
        report.optimization_metrics = opt_metrics

        # Phase 6: Target Code Generation
        codegen = TargetCodeGenerator()
        report.unoptimized_target_code = codegen.generate_stack_code(original_tac)
        report.optimized_target_code = codegen.generate_stack_code(optimized_tac)
        report.pseudo_assembly = codegen.generate_pseudo_assembly(optimized_tac)

        report.compilation_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        # Phase 7: Program Execution (Safe Interpreter)
        if run_program:
            interpreter = TACInterpreter(
                max_steps=self.max_steps, max_output_lines=self.max_output_lines
            )
            report.unoptimized_execution = interpreter.execute(original_tac, icg.var_types)
            report.optimized_execution = interpreter.execute(optimized_tac, icg.var_types)

        return report
