"""
semantic_analyzer.py — Semantic Analyzer & Symbol Table Manager for CompilerX.

Performs static semantic checks over the Abstract Syntax Tree (AST):
1. Variable declaration tracking and duplicate declaration detection per scope.
2. Undeclared variable usage detection.
3. Static type inference and type-compatibility checking across assignments,
   binary/unary operations, and boolean conditions.
4. Detection of invalid operations (e.g., modulo '%' on floats/strings, arithmetic on
   strings, compile-time division/modulo by zero).
5. Unused variable warnings and uninitialized variable usage warnings.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
class Symbol:
    """Represents an entry in the compiler's Symbol Table."""
    name: str
    data_type: str
    scope: str
    line: int
    column: int
    initialized: bool = False
    usage_count: int = 0
    initial_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Variable Name": self.name,
            "Data Type": self.data_type,
            "Scope": self.scope,
            "Declared Line": self.line,
            "Declared Col": self.column,
            "Initialized": "Yes" if self.initialized else "No",
            "Initial Expression": self.initial_value if self.initial_value is not None else "—",
            "References": self.usage_count,
        }


@dataclass
class SemanticErrorDetail:
    """Represents a semantic error with exact line and column metadata."""
    message: str
    line: int
    column: int
    category: str = "Type / Scope Error"

    def format(self) -> str:
        return f"[Semantic Error] Line {self.line}, Col {self.column} ({self.category}): {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Phase": "Semantic Analysis",
            "Category": self.category,
            "Line": self.line,
            "Column": self.column,
            "Message": self.message,
        }


@dataclass
class SemanticWarning:
    """Represents a non-fatal semantic warning (e.g., unused variable)."""
    message: str
    line: int
    column: int

    def format(self) -> str:
        return f"[Semantic Warning] Line {self.line}, Col {self.column}: {self.message}"


class SymbolTable:
    """Hierarchical lexical scope symbol table with full history retention."""

    def __init__(self):
        self.scope_stack: List[Tuple[str, Dict[str, Symbol]]] = [("global", {})]
        self.all_symbols: List[Symbol] = []
        self._scope_counter = 0

    @property
    def current_scope_name(self) -> str:
        return self.scope_stack[-1][0]

    def enter_scope(self, prefix: str = "block") -> str:
        self._scope_counter += 1
        scope_name = f"{prefix}_{self._scope_counter}"
        self.scope_stack.append((scope_name, {}))
        return scope_name

    def exit_scope(self) -> None:
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()

    def declare(self, symbol: Symbol) -> Optional[Symbol]:
        """Declares a symbol in the current scope. Returns existing Symbol if duplicate in current scope."""
        _, current_dict = self.scope_stack[-1]
        if symbol.name in current_dict:
            return current_dict[symbol.name]
        current_dict[symbol.name] = symbol
        self.all_symbols.append(symbol)
        return None

    def lookup(self, name: str) -> Optional[Symbol]:
        """Searches from innermost scope to global scope for `name`."""
        for _, scope_dict in reversed(self.scope_stack):
            if name in scope_dict:
                return scope_dict[name]
        return None

    def to_list_of_dicts(self) -> List[Dict[str, Any]]:
        return [sym.to_dict() for sym in self.all_symbols]


class SemanticAnalyzer:
    """Performs semantic analysis and type checking over an AST."""

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[SemanticErrorDetail] = []
        self.warnings: List[SemanticWarning] = []

    def analyze(self, program: Program) -> Tuple[SymbolTable, List[SemanticErrorDetail], List[SemanticWarning]]:
        self.symbol_table = SymbolTable()
        self.errors = []
        self.warnings = []

        for stmt in program.statements:
            self._visit_statement(stmt)

        # Check for unused variables
        for sym in self.symbol_table.all_symbols:
            if sym.usage_count == 0:
                self.warnings.append(
                    SemanticWarning(
                        message=f"Variable '{sym.name}' ({sym.data_type}) is declared but never used",
                        line=sym.line,
                        column=sym.column,
                    )
                )

        return self.symbol_table, self.errors, self.warnings

    def _visit_statement(self, node: ASTNode) -> None:
        if isinstance(node, VarDecl):
            self._visit_var_decl(node)
        elif isinstance(node, Assignment):
            self._visit_assignment(node)
        elif isinstance(node, PrintStmt):
            self._visit_print(node)
        elif isinstance(node, IfStmt):
            self._visit_if(node)
        elif isinstance(node, WhileStmt):
            self._visit_while(node)
        elif isinstance(node, Block):
            self._visit_block(node, "block")

    def _visit_var_decl(self, node: VarDecl) -> None:
        init_type: Optional[str] = None
        init_repr: Optional[str] = None
        if node.initializer is not None:
            init_type = self._visit_expression(node.initializer)
            init_repr = self._expr_summary(node.initializer)

        existing = self.symbol_table.lookup(node.name)
        # Check duplicate declaration in current scope
        _, cur_scope_dict = self.symbol_table.scope_stack[-1]
        if node.name in cur_scope_dict:
            prev = cur_scope_dict[node.name]
            self.errors.append(
                SemanticErrorDetail(
                    message=f"Duplicate declaration of variable '{node.name}' in scope '{ self.symbol_table.current_scope_name }' (previously declared at line {prev.line}, col {prev.column})",
                    line=node.line,
                    column=node.column,
                    category="Duplicate Declaration",
                )
            )
            return

        if existing is not None:
            self.warnings.append(
                SemanticWarning(
                    message=f"Variable '{node.name}' shadows outer variable declared at line {existing.line}",
                    line=node.line,
                    column=node.column,
                )
            )

        if init_type is not None and init_type != "error":
            if not self._is_assignable(target_type=node.var_type, value_type=init_type):
                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Type mismatch in declaration of '{node.name}': cannot assign value of type '{init_type}' to variable of type '{node.var_type}'",
                        line=node.line,
                        column=node.column,
                        category="Type Mismatch",
                    )
                )

        sym = Symbol(
            name=node.name,
            data_type=node.var_type,
            scope=self.symbol_table.current_scope_name,
            line=node.line,
            column=node.column,
            initialized=node.initializer is not None,
            usage_count=0,
            initial_value=init_repr,
        )
        self.symbol_table.declare(sym)

    def _visit_assignment(self, node: Assignment) -> None:
        sym = self.symbol_table.lookup(node.name)
        val_type = self._visit_expression(node.value) if node.value else "error"

        if sym is None:
            self.errors.append(
                SemanticErrorDetail(
                    message=f"Assignment to undeclared variable '{node.name}'",
                    line=node.line,
                    column=node.column,
                    category="Undeclared Variable",
                )
            )
            return

        sym.initialized = True
        if val_type != "error" and not self._is_assignable(target_type=sym.data_type, value_type=val_type):
            self.errors.append(
                SemanticErrorDetail(
                    message=f"Type mismatch in assignment to '{node.name}': cannot assign '{val_type}' to '{sym.data_type}'",
                    line=node.line,
                    column=node.column,
                    category="Type Mismatch",
                )
            )

    def _visit_print(self, node: PrintStmt) -> None:
        for expr in node.expressions:
            self._visit_expression(expr)

    def _visit_if(self, node: IfStmt) -> None:
        if node.condition:
            cond_type = self._visit_expression(node.condition)
            if cond_type not in ("bool", "int", "float", "error"):
                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Invalid condition type '{cond_type}' in 'if' statement (expected boolean or numeric condition)",
                        line=node.condition.line,
                        column=node.condition.column,
                        category="Invalid Condition",
                    )
                )
        if node.then_branch:
            self._visit_block(node.then_branch, "if_then")
        if node.else_branch:
            if isinstance(node.else_branch, IfStmt):
                self._visit_if(node.else_branch)
            elif isinstance(node.else_branch, Block):
                self._visit_block(node.else_branch, "if_else")

    def _visit_while(self, node: WhileStmt) -> None:
        if node.condition:
            cond_type = self._visit_expression(node.condition)
            if cond_type not in ("bool", "int", "float", "error"):
                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Invalid condition type '{cond_type}' in 'while' loop (expected boolean or numeric condition)",
                        line=node.condition.line,
                        column=node.condition.column,
                        category="Invalid Condition",
                    )
                )
        if node.body:
            self._visit_block(node.body, "while_body")

    def _visit_block(self, block: Block, scope_prefix: str) -> None:
        self.symbol_table.enter_scope(scope_prefix)
        for stmt in block.statements:
            self._visit_statement(stmt)
        self.symbol_table.exit_scope()

    def _visit_expression(self, node: ASTNode) -> str:
        if isinstance(node, Literal):
            return node.literal_type

        if isinstance(node, Identifier):
            sym = self.symbol_table.lookup(node.name)
            if sym is None:
                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Use of undeclared variable '{node.name}'",
                        line=node.line,
                        column=node.column,
                        category="Undeclared Variable",
                    )
                )
                node.inferred_type = "error"
                return "error"
            sym.usage_count += 1
            if not sym.initialized:
                self.warnings.append(
                    SemanticWarning(
                        message=f"Variable '{node.name}' may be used before being initialized (defaults to 0)",
                        line=node.line,
                        column=node.column,
                    )
                )
            node.inferred_type = sym.data_type
            return sym.data_type

        if isinstance(node, UnaryOp):
            op_type = self._visit_expression(node.operand)
            if op_type == "error":
                node.inferred_type = "error"
                return "error"

            if node.op == "-":
                if op_type not in ("int", "float"):
                    self.errors.append(
                        SemanticErrorDetail(
                            message=f"Invalid unary negation '-' on operand of type '{op_type}'",
                            line=node.line,
                            column=node.column,
                            category="Invalid Operation",
                        )
                    )
                    node.inferred_type = "error"
                    return "error"
                node.inferred_type = op_type
                return op_type

            if node.op == "!":
                if op_type not in ("bool", "int", "float"):
                    self.errors.append(
                        SemanticErrorDetail(
                            message=f"Invalid logical NOT '!' on operand of type '{op_type}'",
                            line=node.line,
                            column=node.column,
                            category="Invalid Operation",
                        )
                    )
                    node.inferred_type = "error"
                    return "error"
                node.inferred_type = "bool"
                return "bool"

        if isinstance(node, BinaryOp):
            left_type = self._visit_expression(node.left)
            right_type = self._visit_expression(node.right)

            if left_type == "error" or right_type == "error":
                node.inferred_type = "error"
                return "error"

            op = node.op

            # 1. Arithmetic operators: +, -, *, /, %
            if op in ("+", "-", "*", "/", "%"):
                # Check literal division/modulo by zero
                if op in ("/", "%") and self._is_literal_zero(node.right):
                    self.errors.append(
                        SemanticErrorDetail(
                            message=f"Division or modulo by zero detected at compile time ('{op} 0')",
                            line=node.line,
                            column=node.column,
                            category="Division by Zero",
                        )
                    )
                    node.inferred_type = "error"
                    return "error"

                if op == "%":
                    if left_type != "int" or right_type != "int":
                        self.errors.append(
                            SemanticErrorDetail(
                                message=f"Modulo operator '%' requires integer operands, got '{left_type}' and '{right_type}'",
                                line=node.line,
                                column=node.column,
                                category="Invalid Operation",
                            )
                        )
                        node.inferred_type = "error"
                        return "error"
                    node.inferred_type = "int"
                    return "int"

                if left_type in ("int", "float") and right_type in ("int", "float"):
                    res_type = "float" if ("float" in (left_type, right_type)) else "int"
                    node.inferred_type = res_type
                    return res_type

                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Invalid arithmetic operator '{op}' between '{left_type}' and '{right_type}'",
                        line=node.line,
                        column=node.column,
                        category="Invalid Operation",
                    )
                )
                node.inferred_type = "error"
                return "error"

            # 2. Relational operators: <, <=, >, >=
            if op in ("<", "<=", ">", ">="):
                if left_type in ("int", "float") and right_type in ("int", "float"):
                    node.inferred_type = "bool"
                    return "bool"
                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Cannot compare '{left_type}' and '{right_type}' using '{op}'",
                        line=node.line,
                        column=node.column,
                        category="Invalid Operation",
                    )
                )
                node.inferred_type = "error"
                return "error"

            # 3. Equality operators: ==, !=
            if op in ("==", "!="):
                if left_type == right_type or (
                    left_type in ("int", "float") and right_type in ("int", "float")
                ):
                    node.inferred_type = "bool"
                    return "bool"
                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Cannot compare incompatible types '{left_type}' and '{right_type}' using '{op}'",
                        line=node.line,
                        column=node.column,
                        category="Invalid Operation",
                    )
                )
                node.inferred_type = "error"
                return "error"

            # 4. Logical operators: &&, ||
            if op in ("&&", "||"):
                if left_type in ("bool", "int") and right_type in ("bool", "int"):
                    node.inferred_type = "bool"
                    return "bool"
                self.errors.append(
                    SemanticErrorDetail(
                        message=f"Logical operator '{op}' requires boolean operands, got '{left_type}' and '{right_type}'",
                        line=node.line,
                        column=node.column,
                        category="Invalid Operation",
                    )
                )
                node.inferred_type = "error"
                return "error"

        return "error"

    @staticmethod
    def _is_assignable(target_type: str, value_type: str) -> bool:
        if target_type == value_type:
            return True
        # Implicit widening from int to float is valid in C-like languages
        if target_type == "float" and value_type == "int":
            return True
        return False

    @staticmethod
    def _is_literal_zero(node: Optional[ASTNode]) -> bool:
        if isinstance(node, Literal) and node.literal_type in ("int", "float"):
            return node.value == 0 or node.value == 0.0
        if isinstance(node, UnaryOp) and node.op == "-" and isinstance(node.operand, Literal):
            return node.operand.value == 0 or node.operand.value == 0.0
        return False

    def _expr_summary(self, node: ASTNode) -> str:
        if isinstance(node, Literal):
            return f'"{node.value}"' if node.literal_type == "string" else str(node.value)
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, UnaryOp):
            return f"{node.op}{self._expr_summary(node.operand)}"
        if isinstance(node, BinaryOp):
            return f"({self._expr_summary(node.left)} {node.op} {self._expr_summary(node.right)})"
        return "..."
