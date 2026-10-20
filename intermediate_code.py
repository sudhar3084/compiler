"""
intermediate_code.py — Three-Address Code (TAC) Generator for CompilerX.

Translates the validated Abstract Syntax Tree (AST) into linear Three-Address Code (TAC)
instructions using temporary variables (t1, t2, ...) and control-flow labels (L1, L2, ...).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ast_nodes import (
    ASTNode,
    Assignment,
    BinaryOp,
    Block,
    Identifier,
    IfStmt,
    Literal,
    PrintStmt,
    Program,
    UnaryOp,
    VarDecl,
    WhileStmt,
)


@dataclass
class TACInstruction:
    """
    Represents a single Three-Address Code instruction.

    Supported opcodes (`op`):
    - "ASSIGN": result = arg1
    - Binary ops ("+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "&&", "||"):
      result = arg1 op arg2
    - Unary ops ("NEG", "NOT"):
      result = op arg1
    - "LABEL": result: (label definition)
    - "GOTO": goto result
    - "IF_FALSE": if_false arg1 goto result
    - "PRINT": print arg1
    - "PRINT_INLINE": print_inline arg1 (for multi-arg print before final newline)
    """
    op: str
    arg1: Any = None
    arg2: Any = None
    result: Optional[str] = None
    line: int = 1
    var_type: Optional[str] = None
    comment: str = ""

    def format_operand(self, val: Any) -> str:
        if val is None:
            return ""
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, str):
            # Distinguish string literals (stored as ('str', text)) vs identifier names
            return val
        if isinstance(val, tuple) and len(val) == 2 and val[0] == "str":
            return f'"{val[1]}"'
        return str(val)

    def to_string(self) -> str:
        a1 = self.format_operand(self.arg1)
        a2 = self.format_operand(self.arg2)
        res = self.result or ""

        if self.op == "LABEL":
            return f"{res}:"
        if self.op == "GOTO":
            return f"    goto {res}"
        if self.op == "IF_FALSE":
            return f"    if_false {a1} goto {res}"
        if self.op == "PRINT":
            return f"    print {a1}"
        if self.op == "PRINT_INLINE":
            return f"    print_inline {a1}"
        if self.op == "ASSIGN":
            return f"    {res} = {a1}"
        if self.op == "NEG":
            return f"    {res} = -{a1}"
        if self.op == "NOT":
            return f"    {res} = !{a1}"
        # Binary operation
        return f"    {res} = {a1} {self.op} {a2}"

    def to_dict(self, index: int = 0) -> Dict[str, Any]:
        return {
            "#": index,
            "Op": self.op,
            "Arg 1": self.format_operand(self.arg1),
            "Arg 2": self.format_operand(self.arg2),
            "Result": self.result or "",
            "TAC Statement": self.to_string().strip(),
        }

    def copy(self) -> "TACInstruction":
        return TACInstruction(
            op=self.op,
            arg1=self.arg1,
            arg2=self.arg2,
            result=self.result,
            line=self.line,
            var_type=self.var_type,
            comment=self.comment,
        )


class IntermediateCodeGenerator:
    """Generates Three-Address Code (TAC) from an AST."""

    DEFAULT_VALUES = {
        "int": 0,
        "float": 0.0,
        "bool": False,
        "string": ("str", ""),
    }

    def __init__(self):
        self.instructions: List[TACInstruction] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.var_types: Dict[str, str] = {}

    def _new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def _new_label(self) -> str:
        self.label_counter += 1
        return f"L{self.label_counter}"

    def generate(self, program: Program) -> List[TACInstruction]:
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0
        self.var_types = {}

        for stmt in program.statements:
            self._gen_statement(stmt)

        return self.instructions

    def _gen_statement(self, node: ASTNode) -> None:
        if isinstance(node, VarDecl):
            self.var_types[node.name] = node.var_type
            if node.initializer is not None:
                val = self._gen_expression(node.initializer)
            else:
                val = self.DEFAULT_VALUES.get(node.var_type, 0)
            self.instructions.append(
                TACInstruction(
                    op="ASSIGN",
                    arg1=val,
                    result=node.name,
                    line=node.line,
                    var_type=node.var_type,
                )
            )

        elif isinstance(node, Assignment):
            val = self._gen_expression(node.value)
            self.instructions.append(
                TACInstruction(
                    op="ASSIGN",
                    arg1=val,
                    result=node.name,
                    line=node.line,
                    var_type=self.var_types.get(node.name),
                )
            )

        elif isinstance(node, PrintStmt):
            if len(node.expressions) == 1:
                val = self._gen_expression(node.expressions[0])
                self.instructions.append(
                    TACInstruction(op="PRINT", arg1=val, line=node.line)
                )
            else:
                for idx, expr in enumerate(node.expressions):
                    val = self._gen_expression(expr)
                    op_name = "PRINT" if idx == len(node.expressions) - 1 else "PRINT_INLINE"
                    self.instructions.append(
                        TACInstruction(op=op_name, arg1=val, line=node.line)
                    )

        elif isinstance(node, Block):
            for stmt in node.statements:
                self._gen_statement(stmt)

        elif isinstance(node, IfStmt):
            self._gen_if(node)

        elif isinstance(node, WhileStmt):
            self._gen_while(node)

    def _gen_if(self, node: IfStmt) -> None:
        cond_val = self._gen_expression(node.condition)
        else_label = self._new_label()

        if node.else_branch is None:
            self.instructions.append(
                TACInstruction(
                    op="IF_FALSE",
                    arg1=cond_val,
                    result=else_label,
                    line=node.line,
                )
            )
            self._gen_statement(node.then_branch)
            self.instructions.append(
                TACInstruction(op="LABEL", result=else_label, line=node.line)
            )
        else:
            end_label = self._new_label()
            self.instructions.append(
                TACInstruction(
                    op="IF_FALSE",
                    arg1=cond_val,
                    result=else_label,
                    line=node.line,
                )
            )
            self._gen_statement(node.then_branch)
            self.instructions.append(
                TACInstruction(op="GOTO", result=end_label, line=node.line)
            )
            self.instructions.append(
                TACInstruction(op="LABEL", result=else_label, line=node.line)
            )
            self._gen_statement(node.else_branch)
            self.instructions.append(
                TACInstruction(op="LABEL", result=end_label, line=node.line)
            )

    def _gen_while(self, node: WhileStmt) -> None:
        start_label = self._new_label()
        end_label = self._new_label()

        self.instructions.append(
            TACInstruction(op="LABEL", result=start_label, line=node.line)
        )
        cond_val = self._gen_expression(node.condition)
        self.instructions.append(
            TACInstruction(
                op="IF_FALSE",
                arg1=cond_val,
                result=end_label,
                line=node.line,
            )
        )
        self._gen_statement(node.body)
        self.instructions.append(
            TACInstruction(op="GOTO", result=start_label, line=node.line)
        )
        self.instructions.append(
            TACInstruction(op="LABEL", result=end_label, line=node.line)
        )

    def _gen_expression(self, node: ASTNode) -> Any:
        if isinstance(node, Literal):
            if node.literal_type == "string":
                return ("str", node.value)
            return node.value

        if isinstance(node, Identifier):
            return node.name

        if isinstance(node, UnaryOp):
            operand_val = self._gen_expression(node.operand)
            temp = self._new_temp()
            op_code = "NEG" if node.op == "-" else "NOT"
            self.instructions.append(
                TACInstruction(
                    op=op_code,
                    arg1=operand_val,
                    result=temp,
                    line=node.line,
                    var_type=node.inferred_type,
                )
            )
            return temp

        if isinstance(node, BinaryOp):
            left_val = self._gen_expression(node.left)
            right_val = self._gen_expression(node.right)
            temp = self._new_temp()
            self.instructions.append(
                TACInstruction(
                    op=node.op,
                    arg1=left_val,
                    arg2=right_val,
                    result=temp,
                    line=node.line,
                    var_type=node.inferred_type,
                )
            )
            return temp

        return 0


def format_tac(instructions: List[TACInstruction]) -> str:
    """Formats a list of TACInstruction objects into clean multi-line text."""
    if not instructions:
        return "// (No TAC instructions generated)"
    return "\n".join(instr.to_string() for instr in instructions)
