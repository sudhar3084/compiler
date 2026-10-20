"""
ast_nodes.py — Abstract Syntax Tree (AST) Node Definitions & Visualizers for CompilerX.

Defines strongly-typed dataclasses representing the syntactic structure of programs
in the CompilerX C-like language, along with serializers for JSON, ASCII tree diagrams,
and Graphviz DOT graphs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    line: int = 1
    column: int = 1

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class Program(ASTNode):
    """Root AST node representing a complete program."""
    statements: List[ASTNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Program",
            "line": self.line,
            "column": self.column,
            "statements": [stmt.to_dict() for stmt in self.statements],
        }


@dataclass
class Block(ASTNode):
    """Represents a brace-enclosed block of statements `{ ... }`."""
    statements: List[ASTNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Block",
            "line": self.line,
            "column": self.column,
            "statements": [stmt.to_dict() for stmt in self.statements],
        }


@dataclass
class VarDecl(ASTNode):
    """Represents a variable declaration such as `int x = 10;` or `float y;`."""
    var_type: str = "int"
    name: str = ""
    initializer: Optional[ASTNode] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "VarDecl",
            "var_type": self.var_type,
            "name": self.name,
            "initializer": self.initializer.to_dict() if self.initializer else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Assignment(ASTNode):
    """Represents a variable assignment such as `x = x + 1;`."""
    name: str = ""
    value: Optional[ASTNode] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Assignment",
            "name": self.name,
            "value": self.value.to_dict() if self.value else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class PrintStmt(ASTNode):
    """Represents a `print(expr, ...);` statement."""
    expressions: List[ASTNode] = field(default_factory=list)

    @property
    def expression(self) -> Optional[ASTNode]:
        """Convenience property for single-argument print statements."""
        return self.expressions[0] if self.expressions else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "PrintStmt",
            "expressions": [expr.to_dict() for expr in self.expressions],
            "line": self.line,
            "column": self.column,
        }


@dataclass
class IfStmt(ASTNode):
    """Represents an `if (condition) { ... } else { ... }` statement."""
    condition: Optional[ASTNode] = None
    then_branch: Optional[Block] = None
    else_branch: Optional[ASTNode] = None  # Can be Block or nested IfStmt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "IfStmt",
            "condition": self.condition.to_dict() if self.condition else None,
            "then_branch": self.then_branch.to_dict() if self.then_branch else None,
            "else_branch": self.else_branch.to_dict() if self.else_branch else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class WhileStmt(ASTNode):
    """Represents a `while (condition) { ... }` loop statement."""
    condition: Optional[ASTNode] = None
    body: Optional[Block] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "WhileStmt",
            "condition": self.condition.to_dict() if self.condition else None,
            "body": self.body.to_dict() if self.body else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class BinaryOp(ASTNode):
    """Represents a binary operation such as `a + b`, `x > 30`, or `p && q`."""
    op: str = ""
    left: Optional[ASTNode] = None
    right: Optional[ASTNode] = None
    inferred_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "BinaryOp",
            "op": self.op,
            "inferred_type": self.inferred_type,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class UnaryOp(ASTNode):
    """Represents a unary operation such as `-x` or `!flag`."""
    op: str = ""
    operand: Optional[ASTNode] = None
    inferred_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "UnaryOp",
            "op": self.op,
            "inferred_type": self.inferred_type,
            "operand": self.operand.to_dict() if self.operand else None,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Literal(ASTNode):
    """Represents a constant literal value (int, float, bool, string)."""
    value: Any = None
    literal_type: str = "int"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Literal",
            "value": self.value,
            "literal_type": self.literal_type,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Identifier(ASTNode):
    """Represents a variable reference in an expression."""
    name: str = ""
    inferred_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Identifier",
            "name": self.name,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
        }


def format_ast_tree(node: Optional[ASTNode], prefix: str = "", is_last: bool = True, is_root: bool = True) -> str:
    """Renders an AST into a human-readable ASCII tree diagram."""
    if node is None:
        return ""

    connector = "" if is_root else ("└── " if is_last else "├── ")
    child_prefix = "" if is_root else (prefix + ("    " if is_last else "│   "))

    label = _get_node_label(node)
    lines = [f"{prefix}{connector}{label}"]

    children = _get_node_children(node)
    for idx, (edge_label, child_node) in enumerate(children):
        last_child = idx == len(children) - 1
        if edge_label:
            edge_conn = "└── " if last_child else "├── "
            sub_prefix = child_prefix + ("    " if last_child else "│   ")
            lines.append(f"{child_prefix}{edge_conn}[{edge_label}]")
            lines.append(format_ast_tree(child_node, sub_prefix, True, False))
        else:
            lines.append(format_ast_tree(child_node, child_prefix, last_child, False))

    return "\n".join(line for line in lines if line)


def _get_node_label(node: ASTNode) -> str:
    if isinstance(node, Program):
        return f"Program (lines: {len(node.statements)} stmts)"
    if isinstance(node, Block):
        return f"Block ({len(node.statements)} stmts)"
    if isinstance(node, VarDecl):
        return f"VarDecl(type={node.var_type}, name='{node.name}') [L{node.line}:{node.column}]"
    if isinstance(node, Assignment):
        return f"Assignment(name='{node.name}') [L{node.line}:{node.column}]"
    if isinstance(node, PrintStmt):
        return f"PrintStmt(args={len(node.expressions)}) [L{node.line}:{node.column}]"
    if isinstance(node, IfStmt):
        return f"IfStmt [L{node.line}:{node.column}]"
    if isinstance(node, WhileStmt):
        return f"WhileStmt [L{node.line}:{node.column}]"
    if isinstance(node, BinaryOp):
        type_str = f" : {node.inferred_type}" if node.inferred_type else ""
        return f"BinaryOp('{node.op}'{type_str}) [L{node.line}:{node.column}]"
    if isinstance(node, UnaryOp):
        type_str = f" : {node.inferred_type}" if node.inferred_type else ""
        return f"UnaryOp('{node.op}'{type_str}) [L{node.line}:{node.column}]"
    if isinstance(node, Literal):
        val_repr = f'"{node.value}"' if node.literal_type == "string" else repr(node.value)
        return f"Literal({val_repr} : {node.literal_type})"
    if isinstance(node, Identifier):
        type_str = f" : {node.inferred_type}" if node.inferred_type else ""
        return f"Identifier('{node.name}'{type_str})"
    return node.__class__.__name__


def _get_node_children(node: ASTNode) -> List[tuple]:
    children = []
    if isinstance(node, (Program, Block)):
        for stmt in node.statements:
            children.append(("", stmt))
    elif isinstance(node, VarDecl):
        if node.initializer is not None:
            children.append(("init", node.initializer))
    elif isinstance(node, Assignment):
        if node.value is not None:
            children.append(("value", node.value))
    elif isinstance(node, PrintStmt):
        for idx, expr in enumerate(node.expressions):
            label = f"arg[{idx}]" if len(node.expressions) > 1 else "expr"
            children.append((label, expr))
    elif isinstance(node, IfStmt):
        if node.condition:
            children.append(("condition", node.condition))
        if node.then_branch:
            children.append(("then", node.then_branch))
        if node.else_branch:
            children.append(("else", node.else_branch))
    elif isinstance(node, WhileStmt):
        if node.condition:
            children.append(("condition", node.condition))
        if node.body:
            children.append(("body", node.body))
    elif isinstance(node, BinaryOp):
        if node.left:
            children.append(("left", node.left))
        if node.right:
            children.append(("right", node.right))
    elif isinstance(node, UnaryOp):
        if node.operand:
            children.append(("operand", node.operand))
    return children


def ast_to_graphviz_dot(root: Optional[ASTNode]) -> str:
    """Generates a Graphviz DOT graph definition for visualizing the AST in Streamlit."""
    if root is None:
        return "digraph AST { node [shape=box]; }"

    lines = [
        "digraph AST {",
        '    rankdir=TB;',
        '    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, margin="0.15,0.08"];',
        '    edge [fontname="Helvetica", fontsize=9, color="#555555"];',
    ]
    counter = [0]

    def visit(node: ASTNode) -> str:
        counter[0] += 1
        node_id = f"n{counter[0]}"
        color = "#E3F2FD"
        border = "#1E88E5"

        if isinstance(node, Program):
            label = "Program"
            color, border = "#EDE7F6", "#5E35B1"
        elif isinstance(node, Block):
            label = "Block { ... }"
            color, border = "#F3E5F5", "#8E24AA"
        elif isinstance(node, VarDecl):
            label = f"VarDecl\\n{node.var_type} {node.name}"
            color, border = "#E8F5E9", "#43A047"
        elif isinstance(node, Assignment):
            label = f"Assign\\n{node.name} ="
            color, border = "#E8F5E9", "#43A047"
        elif isinstance(node, PrintStmt):
            label = "print()"
            color, border = "#FFF3E0", "#FB8C00"
        elif isinstance(node, IfStmt):
            label = "if / else"
            color, border = "#FFF8E1", "#FDD835"
        elif isinstance(node, WhileStmt):
            label = "while"
            color, border = "#FFF8E1", "#FDD835"
        elif isinstance(node, BinaryOp):
            label = f"Op: {node.op}"
            color, border = "#E0F7FA", "#00ACC1"
        elif isinstance(node, UnaryOp):
            label = f"Unary: {node.op}"
            color, border = "#E0F7FA", "#00ACC1"
        elif isinstance(node, Literal):
            val_str = str(node.value).replace('"', '\\"')
            label = f"{node.literal_type}\\n{val_str}"
            color, border = "#F1F8E9", "#7CB342"
        elif isinstance(node, Identifier):
            label = f"Id: {node.name}"
            color, border = "#E3F2FD", "#1E88E5"
        else:
            label = node.__class__.__name__

        lines.append(
            f'    {node_id} [label="{label}", fillcolor="{color}", color="{border}"];'
        )

        for edge_label, child in _get_node_children(node):
            child_id = visit(child)
            if edge_label:
                lines.append(f'    {node_id} -> {child_id} [label="{edge_label}"];')
            else:
                lines.append(f"    {node_id} -> {child_id};")

        return node_id

    visit(root)
    lines.append("}")
    return "\n".join(lines)
