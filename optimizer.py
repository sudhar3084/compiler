"""
optimizer.py — Multi-Pass Intermediate Code Optimizer for CompilerX.

Implements safe, semantics-preserving compiler optimizations on Three-Address Code (TAC):
1. Constant Folding: Evaluates compile-time constant binary and unary expressions.
2. Constant Propagation: Substitutes known constant values of variables and temporaries,
   respecting control-flow joins and loop-carried mutations.
3. Algebraic Simplification & Redundant Operation Elimination:
   - Identity simplifications (x + 0 -> x, x * 1 -> x, x * 0 -> 0, x / 1 -> x, etc.)
   - Local Common Subexpression Elimination (CSE) within basic blocks
   - Copy Propagation (replacing redundant temporary copies)
4. Dead-Code Elimination (DCE):
   - Constant branch resolution (if_false true -> no-op; if_false false -> goto)
   - Unreachable code elimination after unconditional jumps
   - Unused label removal (enabling basic block merging)
   - Dead temporary and overwritten assignment removal
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from intermediate_code import TACInstruction


@dataclass
class OptimizationMetrics:
    """Tracks detailed statistics across optimization passes."""
    original_instruction_count: int = 0
    optimized_instruction_count: int = 0
    constant_foldings: int = 0
    constant_propagations: int = 0
    algebraic_simplifications: int = 0
    common_subexpressions_eliminated: int = 0
    dead_instructions_removed: int = 0
    passes_executed: int = 0
    optimization_log: List[str] = field(default_factory=list)

    @property
    def instructions_removed(self) -> int:
        return max(0, self.original_instruction_count - self.optimized_instruction_count)

    @property
    def reduction_percentage(self) -> float:
        if self.original_instruction_count == 0:
            return 0.0
        return round((self.instructions_removed / self.original_instruction_count) * 100.0, 1)

    @property
    def total_transformations(self) -> int:
        return (
            self.constant_foldings
            + self.constant_propagations
            + self.algebraic_simplifications
            + self.common_subexpressions_eliminated
            + self.dead_instructions_removed
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Original TAC Instructions": self.original_instruction_count,
            "Optimized TAC Instructions": self.optimized_instruction_count,
            "Instructions Eliminated": self.instructions_removed,
            "Code Size Reduction (%)": f"{self.reduction_percentage}%",
            "Constant Foldings": self.constant_foldings,
            "Constant Propagations": self.constant_propagations,
            "Algebraic / Redundant Ops Simplified": (
                self.algebraic_simplifications + self.common_subexpressions_eliminated
            ),
            "Dead Instructions Eliminated": self.dead_instructions_removed,
            "Optimization Passes Run": self.passes_executed,
        }


def is_constant_operand(val: Any) -> bool:
    """Returns True if the TAC operand is a compile-time literal (int, float, bool, or ('str', ...))."""
    if isinstance(val, (int, float, bool)):
        return True
    if isinstance(val, tuple) and len(val) == 2 and val[0] == "str":
        return True
    return False


def is_identifier_operand(val: Any) -> bool:
    """Returns True if the TAC operand is a variable or temporary name."""
    return isinstance(val, str) and len(val) > 0


def is_temp_var(name: Any) -> bool:
    """Returns True if `name` is a compiler-generated temporary (e.g., t1, t2)."""
    return isinstance(name, str) and len(name) >= 2 and name[0] == "t" and name[1:].isdigit()


class TACOptimizer:
    """Iterative multi-pass optimizer for Three-Address Code."""

    BINARY_OPS = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "&&", "||"}

    def __init__(self, max_passes: int = 8):
        self.max_passes = max_passes
        self.metrics = OptimizationMetrics()

    def optimize(self, instructions: List[TACInstruction]) -> Tuple[List[TACInstruction], OptimizationMetrics]:
        current = [instr.copy() for instr in instructions]
        self.metrics = OptimizationMetrics(original_instruction_count=len(current))

        for pass_num in range(1, self.max_passes + 1):
            before_snapshot = [instr.to_string() for instr in current]
            self.metrics.passes_executed = pass_num

            # 1. Constant Propagation, Copy Propagation, CSE & Constant Folding
            current = self._pass_propagate_and_fold(current)

            # 2. Control-Flow & Unreachable Code Optimization
            current = self._pass_branch_and_unreachable_dce(current)

            # 3. Dead Temporary & Redundant Store Elimination
            current = self._pass_dead_store_elimination(current)

            after_snapshot = [instr.to_string() for instr in current]
            if before_snapshot == after_snapshot:
                break

        self.metrics.optimized_instruction_count = len(current)
        return current, self.metrics

    def _find_multi_assigned_vars(self, instructions: List[TACInstruction]) -> Set[str]:
        """
        Finds variables that are assigned more than once or modified after any label.
        Variables NOT in this set are true single-assignment constants and safe to
        propagate across label boundaries; variables IN this set are only propagated
        within a single basic block (cleared at labels/jumps).
        """
        assign_counts: Dict[str, int] = {}
        assigned_after_label: Set[str] = set()
        seen_label = False

        for instr in instructions:
            if instr.op == "LABEL":
                seen_label = True
            elif instr.result and instr.op not in ("GOTO", "IF_FALSE"):
                assign_counts[instr.result] = assign_counts.get(instr.result, 0) + 1
                if seen_label:
                    assigned_after_label.add(instr.result)

        multi = {var for var, count in assign_counts.items() if count > 1}
        return multi | assigned_after_label

    def _pass_propagate_and_fold(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        multi_assigned = self._find_multi_assigned_vars(instructions)
        const_env: Dict[str, Any] = {}
        copy_env: Dict[str, str] = {}
        expr_table: Dict[Tuple[str, Any, Any], str] = {}
        result_list: List[TACInstruction] = []

        for instr in instructions:
            inst = instr.copy()

            # At basic block boundaries (LABEL), invalidate mutable state
            if inst.op == "LABEL":
                const_env = {
                    k: v for k, v in const_env.items() if k not in multi_assigned
                }
                copy_env.clear()
                expr_table.clear()
                result_list.append(inst)
                continue

            # Substitute known constants or copies in arg1
            if is_identifier_operand(inst.arg1):
                orig_arg1 = inst.arg1
                if orig_arg1 in const_env:
                    inst.arg1 = const_env[orig_arg1]
                    self.metrics.constant_propagations += 1
                    self.metrics.optimization_log.append(
                        f"Constant Propagation: replaced '{orig_arg1}' with {inst.format_operand(inst.arg1)}"
                    )
                elif orig_arg1 in copy_env:
                    inst.arg1 = copy_env[orig_arg1]

            # Substitute known constants or copies in arg2
            if is_identifier_operand(inst.arg2):
                orig_arg2 = inst.arg2
                if orig_arg2 in const_env:
                    inst.arg2 = const_env[orig_arg2]
                    self.metrics.constant_propagations += 1
                    self.metrics.optimization_log.append(
                        f"Constant Propagation: replaced '{orig_arg2}' with {inst.format_operand(inst.arg2)}"
                    )
                elif orig_arg2 in copy_env:
                    inst.arg2 = copy_env[orig_arg2]

            # Before updating `inst.result`, invalidate stale CSE/copy entries that depended on `inst.result`
            if inst.result and inst.op not in ("GOTO", "IF_FALSE", "LABEL"):
                target = inst.result
                copy_env = {
                    k: v for k, v in copy_env.items() if k != target and v != target
                }
                expr_table = {
                    k: v
                    for k, v in expr_table.items()
                    if k[1] != target and k[2] != target and v != target
                }

            # Handle Unary Operations (Constant Folding)
            if inst.op in ("NEG", "NOT") and is_constant_operand(inst.arg1):
                folded_ok, folded_val = self._fold_unary(inst.op, inst.arg1)
                if folded_ok:
                    old_str = inst.to_string().strip()
                    inst.op = "ASSIGN"
                    inst.arg1 = folded_val
                    inst.arg2 = None
                    self.metrics.constant_foldings += 1
                    self.metrics.optimization_log.append(
                        f"Constant Folding: '{old_str}' -> '{inst.to_string().strip()}'"
                    )

            # Handle Binary Operations (Constant Folding, Algebraic Identities & CSE)
            elif inst.op in self.BINARY_OPS:
                if is_constant_operand(inst.arg1) and is_constant_operand(inst.arg2):
                    folded_ok, folded_val = self._fold_binary(
                        inst.op, inst.arg1, inst.arg2, inst.var_type
                    )
                    if folded_ok:
                        old_str = inst.to_string().strip()
                        inst.op = "ASSIGN"
                        inst.arg1 = folded_val
                        inst.arg2 = None
                        self.metrics.constant_foldings += 1
                        self.metrics.optimization_log.append(
                            f"Constant Folding: '{old_str}' -> '{inst.to_string().strip()}'"
                        )
                else:
                    # Try Algebraic Simplification
                    simp_ok, simp_val = self._simplify_algebraic(inst.op, inst.arg1, inst.arg2)
                    if simp_ok:
                        old_str = inst.to_string().strip()
                        inst.op = "ASSIGN"
                        inst.arg1 = simp_val
                        inst.arg2 = None
                        self.metrics.algebraic_simplifications += 1
                        self.metrics.optimization_log.append(
                            f"Algebraic Simplification: '{old_str}' -> '{inst.to_string().strip()}'"
                        )
                    else:
                        # Local Common Subexpression Elimination (CSE)
                        expr_key = self._canonical_expr_key(inst.op, inst.arg1, inst.arg2)
                        if expr_key in expr_table:
                            prev_holder = expr_table[expr_key]
                            old_str = inst.to_string().strip()
                            inst.op = "ASSIGN"
                            inst.arg1 = prev_holder
                            inst.arg2 = None
                            self.metrics.common_subexpressions_eliminated += 1
                            self.metrics.optimization_log.append(
                                f"Common Subexpression Elimination: '{old_str}' reused '{prev_holder}'"
                            )
                        elif inst.result:
                            expr_table[expr_key] = inst.result

            # Update environment when a variable/temporary is assigned
            if inst.result and inst.op not in ("GOTO", "IF_FALSE", "LABEL"):
                target = inst.result
                if inst.op == "ASSIGN":
                    if is_constant_operand(inst.arg1):
                        val = inst.arg1
                        if inst.var_type == "float" and isinstance(val, int) and not isinstance(val, bool):
                            val = float(val)
                            inst.arg1 = val
                        const_env[target] = val
                    else:
                        const_env.pop(target, None)
                        if is_identifier_operand(inst.arg1):
                            copy_env[target] = inst.arg1
                else:
                    const_env.pop(target, None)

            if inst.op in ("GOTO", "IF_FALSE"):
                copy_env.clear()
                expr_table.clear()

            result_list.append(inst)

        return result_list

    def _pass_branch_and_unreachable_dce(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        """Simplifies constant conditional jumps, removes unreachable instructions, and prunes unused labels."""
        step1: List[TACInstruction] = []
        unreachable = False

        for inst in instructions:
            if inst.op == "LABEL":
                unreachable = False
                step1.append(inst)
                continue

            if unreachable:
                self.metrics.dead_instructions_removed += 1
                self.metrics.optimization_log.append(
                    f"Dead-Code Elimination: removed unreachable instruction '{inst.to_string().strip()}'"
                )
                continue

            if inst.op == "IF_FALSE" and is_constant_operand(inst.arg1):
                cond_truth = bool(inst.arg1)
                if cond_truth is True:
                    self.metrics.dead_instructions_removed += 1
                    self.metrics.optimization_log.append(
                        f"Branch Optimization: removed never-taken branch '{inst.to_string().strip()}'"
                    )
                    continue
                else:
                    old_str = inst.to_string().strip()
                    jump_inst = TACInstruction(
                        op="GOTO", result=inst.result, line=inst.line
                    )
                    self.metrics.algebraic_simplifications += 1
                    self.metrics.optimization_log.append(
                        f"Branch Optimization: '{old_str}' simplified to unconditional 'goto {inst.result}'"
                    )
                    step1.append(jump_inst)
                    unreachable = True
                    continue

            step1.append(inst)
            if inst.op == "GOTO":
                unreachable = True

        # Remove redundant `goto L` when `L:` is the immediately following instruction
        step2: List[TACInstruction] = []
        for idx, inst in enumerate(step1):
            if (
                inst.op == "GOTO"
                and idx + 1 < len(step1)
                and step1[idx + 1].op == "LABEL"
                and step1[idx + 1].result == inst.result
            ):
                self.metrics.dead_instructions_removed += 1
                self.metrics.optimization_log.append(
                    f"Dead-Code Elimination: removed fallthrough 'goto {inst.result}'"
                )
                continue
            step2.append(inst)

        # Remove labels that are not referenced by any GOTO or IF_FALSE
        referenced_labels: Set[str] = {
            inst.result
            for inst in step2
            if inst.op in ("GOTO", "IF_FALSE") and inst.result is not None
        }
        step3: List[TACInstruction] = []
        for inst in step2:
            if inst.op == "LABEL" and inst.result not in referenced_labels:
                self.metrics.dead_instructions_removed += 1
                self.metrics.optimization_log.append(
                    f"Dead-Code Elimination: removed unreferenced label '{inst.result}:'"
                )
                continue
            step3.append(inst)

        return step3

    def _pass_dead_store_elimination(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        """
        Eliminates assignments to temporary variables (`t1`, `t2`, ...) that are never read,
        as well as overwritten assignments to the same variable within a basic block before any read.
        """
        used_identifiers: Set[str] = set()
        for inst in instructions:
            if is_identifier_operand(inst.arg1):
                used_identifiers.add(inst.arg1)
            if is_identifier_operand(inst.arg2):
                used_identifiers.add(inst.arg2)

        filtered: List[TACInstruction] = []
        for inst in instructions:
            if (
                inst.result
                and is_temp_var(inst.result)
                and inst.op not in ("LABEL", "GOTO", "IF_FALSE", "PRINT", "PRINT_INLINE")
                and inst.result not in used_identifiers
            ):
                self.metrics.dead_instructions_removed += 1
                self.metrics.optimization_log.append(
                    f"Dead-Code Elimination: removed unused temporary '{inst.to_string().strip()}'"
                )
                continue
            filtered.append(inst)

        has_loops_or_jumps = any(i.op in ("LABEL", "GOTO", "IF_FALSE") for i in filtered)
        if not has_loops_or_jumps:
            needed_after: Set[str] = set()
            seen_final_write: Set[str] = set()
            reversed_keep: List[TACInstruction] = []

            for inst in reversed(filtered):
                if inst.result and inst.op not in ("LABEL", "GOTO", "IF_FALSE", "PRINT", "PRINT_INLINE"):
                    target = inst.result
                    if is_temp_var(target):
                        if target not in needed_after:
                            self.metrics.dead_instructions_removed += 1
                            self.metrics.optimization_log.append(
                                f"Dead-Code Elimination: removed dead temporary '{inst.to_string().strip()}'"
                            )
                            continue
                    else:
                        if target in seen_final_write and target not in needed_after:
                            self.metrics.dead_instructions_removed += 1
                            self.metrics.optimization_log.append(
                                f"Dead-Code Elimination: removed overwritten assignment '{inst.to_string().strip()}'"
                            )
                            continue
                        seen_final_write.add(target)
                    needed_after.discard(target)

                if is_identifier_operand(inst.arg1):
                    needed_after.add(inst.arg1)
                if is_identifier_operand(inst.arg2):
                    needed_after.add(inst.arg2)
                reversed_keep.append(inst)

            filtered = list(reversed(reversed_keep))

        return filtered

    @staticmethod
    def _fold_unary(op: str, val: Any) -> Tuple[bool, Any]:
        try:
            if op == "NEG" and isinstance(val, (int, float)) and not isinstance(val, bool):
                return True, -val
            if op == "NOT" and isinstance(val, (bool, int)):
                return True, not bool(val)
        except Exception:
            pass
        return False, None

    @staticmethod
    def _fold_binary(
        op: str, left: Any, right: Any, var_type: Optional[str] = None
    ) -> Tuple[bool, Any]:
        try:
            if isinstance(left, tuple) or isinstance(right, tuple):
                if op == "==":
                    return True, left == right
                if op == "!=":
                    return True, left != right
                return False, None

            if op == "+":
                return True, left + right
            if op == "-":
                return True, left - right
            if op == "*":
                return True, left * right
            if op == "/":
                if right == 0 or right == 0.0:
                    return False, None
                if isinstance(left, int) and isinstance(right, int) and var_type != "float":
                    return True, int(left / right)
                return True, left / right
            if op == "%":
                if right == 0:
                    return False, None
                return True, left % right
            if op == "==":
                return True, left == right
            if op == "!=":
                return True, left != right
            if op == "<":
                return True, left < right
            if op == "<=":
                return True, left <= right
            if op == ">":
                return True, left > right
            if op == ">=":
                return True, left >= right
            if op == "&&":
                return True, bool(left) and bool(right)
            if op == "||":
                return True, bool(left) or bool(right)
        except Exception:
            pass
        return False, None

    @staticmethod
    def _simplify_algebraic(op: str, left: Any, right: Any) -> Tuple[bool, Any]:
        """Simplifies algebraic identities like x + 0 -> x, x * 1 -> x, x * 0 -> 0."""
        if op == "+":
            if right == 0 and not isinstance(right, bool):
                return True, left
            if left == 0 and not isinstance(left, bool):
                return True, right

        if op == "-":
            if right == 0 and not isinstance(right, bool):
                return True, left
            if is_identifier_operand(left) and left == right:
                return True, 0

        if op == "*":
            if right == 1 and not isinstance(right, bool):
                return True, left
            if left == 1 and not isinstance(left, bool):
                return True, right
            if (right == 0 and not isinstance(right, bool)) or (
                left == 0 and not isinstance(left, bool)
            ):
                return True, 0

        if op == "/":
            if right == 1 and not isinstance(right, bool):
                return True, left

        if op == "==" and is_identifier_operand(left) and left == right:
            return True, True
        if op == "!=" and is_identifier_operand(left) and left == right:
            return True, False

        if op == "&&":
            if left is True:
                return True, right
            if right is True:
                return True, left
            if left is False or right is False:
                return True, False
        if op == "||":
            if left is False:
                return True, right
            if right is False:
                return True, left
            if left is True or right is True:
                return True, True

        return False, None

    @staticmethod
    def _canonical_expr_key(op: str, left: Any, right: Any) -> Tuple[str, Any, Any]:
        """Normalizes commutative operations so `a + b` and `b + a` share the same CSE key."""
        if op in ("+", "*", "==", "!=", "&&", "||"):
            ordered = sorted([left, right], key=lambda x: (str(type(x)), str(x)))
            return (op, ordered[0], ordered[1])
        return (op, left, right)
