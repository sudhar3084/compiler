"""
code_generator.py — Target Code Generator for CompilerX.

Translates Three-Address Code (TAC) into two readable target representations:
1. Stack-Based Virtual Machine Bytecode (`PUSH_CONST`, `LOAD`, `STORE`, `ADD`, `MUL`, `JZ`, `JMP`, `PRINT`, `HALT`).
2. Register-Based Pseudo-Assembly (`MOV`, `LDR`, `STR`, `ADD`, `MUL`, `CMP`, `B.FALSE`, `JMP`, `OUT`, `HLT`).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from intermediate_code import TACInstruction
from optimizer import is_constant_operand


@dataclass
class TargetInstruction:
    """Represents a single Stack-Machine instruction."""
    opcode: str
    operand: Any = None
    comment: str = ""
    line: int = 1

    def format_operand(self) -> str:
        if self.operand is None:
            return ""
        if isinstance(self.operand, bool):
            return "true" if self.operand else "false"
        if isinstance(self.operand, tuple) and len(self.operand) == 2 and self.operand[0] == "str":
            return f'"{self.operand[1]}"'
        return str(self.operand)

    def to_string(self) -> str:
        if self.opcode == "LABEL":
            return f"{self.operand}:"
        op_str = self.format_operand()
        base = f"    {self.opcode:<12} {op_str}".rstrip()
        if self.comment:
            return f"{base:<34} ; {self.comment}"
        return base

    def to_dict(self, index: int = 0) -> Dict[str, Any]:
        return {
            "Address": f"0x{index * 4:04X}",
            "Opcode": self.opcode,
            "Operand": self.format_operand(),
            "Comment": self.comment,
        }


class TargetCodeGenerator:
    """Generates Stack-VM instructions and Register Pseudo-Assembly from TAC."""

    BINARY_OP_MAP = {
        "+": "ADD",
        "-": "SUB",
        "*": "MUL",
        "/": "DIV",
        "%": "MOD",
        "==": "CMP_EQ",
        "!=": "CMP_NEQ",
        "<": "CMP_LT",
        "<=": "CMP_LTE",
        ">": "CMP_GT",
        ">=": "CMP_GTE",
        "&&": "AND",
        "||": "OR",
    }

    ASM_OP_MAP = {
        "+": "ADD",
        "-": "SUB",
        "*": "MUL",
        "/": "DIV",
        "%": "MOD",
        "==": "CMP_EQ",
        "!=": "CMP_NEQ",
        "<": "CMP_LT",
        "<=": "CMP_LTE",
        ">": "CMP_GT",
        ">=": "CMP_GTE",
        "&&": "AND",
        "||": "OR",
    }

    def generate_stack_code(self, tac_list: List[TACInstruction]) -> List[TargetInstruction]:
        """Generates Stack-Based Virtual Machine instructions from TAC."""
        target: List[TargetInstruction] = []

        for instr in tac_list:
            if instr.op == "LABEL":
                target.append(
                    TargetInstruction(opcode="LABEL", operand=instr.result, line=instr.line)
                )
            elif instr.op == "GOTO":
                target.append(
                    TargetInstruction(
                        opcode="JMP",
                        operand=instr.result,
                        comment=f"Unconditional jump to {instr.result}",
                        line=instr.line,
                    )
                )
            elif instr.op == "IF_FALSE":
                self._emit_push_or_load(target, instr.arg1, instr.line)
                target.append(
                    TargetInstruction(
                        opcode="JZ",
                        operand=instr.result,
                        comment=f"Jump to {instr.result} if false",
                        line=instr.line,
                    )
                )
            elif instr.op == "PRINT":
                self._emit_push_or_load(target, instr.arg1, instr.line)
                target.append(
                    TargetInstruction(
                        opcode="PRINT",
                        comment="Pop and print top of stack with newline",
                        line=instr.line,
                    )
                )
            elif instr.op == "PRINT_INLINE":
                self._emit_push_or_load(target, instr.arg1, instr.line)
                target.append(
                    TargetInstruction(
                        opcode="PRINT_INLINE",
                        comment="Pop and print top of stack (inline)",
                        line=instr.line,
                    )
                )
            elif instr.op == "ASSIGN":
                self._emit_push_or_load(target, instr.arg1, instr.line)
                target.append(
                    TargetInstruction(
                        opcode="STORE",
                        operand=instr.result,
                        comment=f"{instr.result} = {instr.format_operand(instr.arg1)}",
                        line=instr.line,
                    )
                )
            elif instr.op in ("NEG", "NOT"):
                self._emit_push_or_load(target, instr.arg1, instr.line)
                vm_op = "NEG" if instr.op == "NEG" else "NOT"
                target.append(TargetInstruction(opcode=vm_op, line=instr.line))
                target.append(
                    TargetInstruction(
                        opcode="STORE",
                        operand=instr.result,
                        comment=instr.to_string().strip(),
                        line=instr.line,
                    )
                )
            elif instr.op in self.BINARY_OP_MAP:
                self._emit_push_or_load(target, instr.arg1, instr.line)
                self._emit_push_or_load(target, instr.arg2, instr.line)
                vm_op = self.BINARY_OP_MAP[instr.op]
                target.append(TargetInstruction(opcode=vm_op, line=instr.line))
                target.append(
                    TargetInstruction(
                        opcode="STORE",
                        operand=instr.result,
                        comment=instr.to_string().strip(),
                        line=instr.line,
                    )
                )

        target.append(TargetInstruction(opcode="HALT", comment="End of program"))
        return target

    def _emit_push_or_load(
        self, target: List[TargetInstruction], operand: Any, line: int
    ) -> None:
        if is_constant_operand(operand):
            target.append(
                TargetInstruction(opcode="PUSH_CONST", operand=operand, line=line)
            )
        else:
            target.append(
                TargetInstruction(opcode="LOAD", operand=operand, line=line)
            )

    def generate_pseudo_assembly(self, tac_list: List[TACInstruction]) -> str:
        """Generates readable Register-Based Pseudo-Assembly from TAC."""
        lines: List[str] = ["; --- CompilerX Pseudo-Assembly Target Code ---"]
        reg_counter = 0

        def next_reg() -> str:
            nonlocal reg_counter
            r = f"R{reg_counter % 8}"
            reg_counter += 1
            return r

        def fmt_op(val: Any) -> str:
            if isinstance(val, bool):
                return "#1" if val else "#0"
            if isinstance(val, (int, float)):
                return f"#{val}"
            if isinstance(val, tuple) and len(val) == 2 and val[0] == "str":
                return f'"{val[1]}"'
            return f"[{val}]"

        for instr in tac_list:
            if instr.op == "LABEL":
                lines.append(f"{instr.result}:")
            elif instr.op == "GOTO":
                lines.append(f"    JMP     {instr.result}")
            elif instr.op == "IF_FALSE":
                r = next_reg()
                lines.append(f"    MOV     {r}, {fmt_op(instr.arg1)}")
                lines.append(f"    CMP     {r}, #0")
                lines.append(f"    JEQ     {instr.result}")
            elif instr.op in ("PRINT", "PRINT_INLINE"):
                r = next_reg()
                lines.append(f"    MOV     {r}, {fmt_op(instr.arg1)}")
                out_op = "OUT_LN" if instr.op == "PRINT" else "OUT_PART"
                lines.append(f"    {out_op:<7} {r}")
            elif instr.op == "ASSIGN":
                r = next_reg()
                lines.append(f"    MOV     {r}, {fmt_op(instr.arg1)}")
                lines.append(f"    STR     {r}, [{instr.result}]")
            elif instr.op in ("NEG", "NOT"):
                r = next_reg()
                lines.append(f"    MOV     {r}, {fmt_op(instr.arg1)}")
                lines.append(f"    {instr.op:<7} {r}, {r}")
                lines.append(f"    STR     {r}, [{instr.result}]")
            elif instr.op in self.ASM_OP_MAP:
                r1 = next_reg()
                r2 = next_reg()
                asm_op = self.ASM_OP_MAP[instr.op]
                lines.append(f"    MOV     {r1}, {fmt_op(instr.arg1)}")
                lines.append(f"    MOV     {r2}, {fmt_op(instr.arg2)}")
                lines.append(f"    {asm_op:<7} {r1}, {r1}, {r2}")
                lines.append(f"    STR     {r1}, [{instr.result}]")

        lines.append("    HALT")
        return "\n".join(lines)


def format_target_code(instructions: List[TargetInstruction]) -> str:
    """Formats Stack-VM target instructions into a readable string."""
    if not instructions:
        return "; (No target instructions generated)"
    return "\n".join(instr.to_string() for instr in instructions)
