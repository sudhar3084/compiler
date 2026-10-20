"""
lexer.py — Lexical Analyzer (Scanner) for CompilerX.

Converts raw source code into a stream of strongly-typed Tokens while tracking
exact line and column numbers. Identifies invalid characters, malformed numbers,
unterminated string literals, and unclosed comments with detailed error messages.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TokenType( str, Enum ):
    # Keywords
    INT_KW = "INT_KW"
    FLOAT_KW = "FLOAT_KW"
    BOOL_KW = "BOOL_KW"
    STRING_KW = "STRING_KW"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    PRINT = "PRINT"
    TRUE = "TRUE"
    FALSE = "FALSE"

    # Identifiers & Literals
    IDENTIFIER = "IDENTIFIER"
    INT_LITERAL = "INT_LITERAL"
    FLOAT_LITERAL = "FLOAT_LITERAL"
    STRING_LITERAL = "STRING_LITERAL"

    # Arithmetic Operators
    PLUS = "PLUS"          # +
    MINUS = "MINUS"        # -
    STAR = "STAR"          # *
    SLASH = "SLASH"        # /
    PERCENT = "PERCENT"    # %

    # Assignment & Compound Assignment
    ASSIGN = "ASSIGN"              # =
    PLUS_ASSIGN = "PLUS_ASSIGN"    # +=
    MINUS_ASSIGN = "MINUS_ASSIGN"  # -=
    STAR_ASSIGN = "STAR_ASSIGN"    # *=
    SLASH_ASSIGN = "SLASH_ASSIGN"  # /=

    # Comparison Operators
    EQ = "EQ"      # ==
    NEQ = "NEQ"    # !=
    LT = "LT"      # <
    LTE = "LTE"    # <=
    GT = "GT"      # >
    GTE = "GTE"    # >=

    # Logical Operators
    AND = "AND"    # && or 'and'
    OR = "OR"      # || or 'or'
    NOT = "NOT"    # ! or 'not'

    # Delimiters
    LPAREN = "LPAREN"        # (
    RPAREN = "RPAREN"        # )
    LBRACE = "LBRACE"        # {
    RBRACE = "RBRACE"        # }
    SEMICOLON = "SEMICOLON"  # ;
    COMMA = "COMMA"          # ,

    # End of File
    EOF = "EOF"


KEYWORDS: Dict[str, TokenType] = {
    "int": TokenType.INT_KW,
    "float": TokenType.FLOAT_KW,
    "bool": TokenType.BOOL_KW,
    "string": TokenType.STRING_KW,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "print": TokenType.PRINT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}


TOKEN_CATEGORY: Dict[TokenType, str] = {
    TokenType.INT_KW: "Keyword (Type)",
    TokenType.FLOAT_KW: "Keyword (Type)",
    TokenType.BOOL_KW: "Keyword (Type)",
    TokenType.STRING_KW: "Keyword (Type)",
    TokenType.IF: "Keyword (Control)",
    TokenType.ELSE: "Keyword (Control)",
    TokenType.WHILE: "Keyword (Loop)",
    TokenType.PRINT: "Keyword (Built-in)",
    TokenType.TRUE: "Boolean Literal",
    TokenType.FALSE: "Boolean Literal",
    TokenType.IDENTIFIER: "Identifier",
    TokenType.INT_LITERAL: "Integer Literal",
    TokenType.FLOAT_LITERAL: "Float Literal",
    TokenType.STRING_LITERAL: "String Literal",
    TokenType.PLUS: "Arithmetic Operator",
    TokenType.MINUS: "Arithmetic Operator",
    TokenType.STAR: "Arithmetic Operator",
    TokenType.SLASH: "Arithmetic Operator",
    TokenType.PERCENT: "Arithmetic Operator",
    TokenType.ASSIGN: "Assignment Operator",
    TokenType.PLUS_ASSIGN: "Compound Assignment",
    TokenType.MINUS_ASSIGN: "Compound Assignment",
    TokenType.STAR_ASSIGN: "Compound Assignment",
    TokenType.SLASH_ASSIGN: "Compound Assignment",
    TokenType.EQ: "Comparison Operator",
    TokenType.NEQ: "Comparison Operator",
    TokenType.LT: "Comparison Operator",
    TokenType.LTE: "Comparison Operator",
    TokenType.GT: "Comparison Operator",
    TokenType.GTE: "Comparison Operator",
    TokenType.AND: "Logical Operator",
    TokenType.OR: "Logical Operator",
    TokenType.NOT: "Logical Operator",
    TokenType.LPAREN: "Delimiter",
    TokenType.RPAREN: "Delimiter",
    TokenType.LBRACE: "Delimiter",
    TokenType.RBRACE: "Delimiter",
    TokenType.SEMICOLON: "Delimiter",
    TokenType.COMMA: "Delimiter",
    TokenType.EOF: "End of File",
}


@dataclass
class Token:
    """Represents a single lexical token."""
    type: TokenType
    value: Any
    line: int
    column: int

    @property
    def category(self) -> str:
        return TOKEN_CATEGORY.get(self.type, "Token")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Line": self.line,
            "Column": self.column,
            "Token Type": self.type.value,
            "Category": self.category,
            "Lexeme / Value": repr(self.value) if self.type == TokenType.STRING_LITERAL else str(self.value),
        }


@dataclass
class LexicalError:
    """Represents a lexical analysis error with source location."""
    message: str
    line: int
    column: int
    lexeme: str = ""

    def format(self) -> str:
        return f"[Lexical Error] Line {self.line}, Col {self.column}: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Phase": "Lexical Analysis",
            "Line": self.line,
            "Column": self.column,
            "Lexeme": self.lexeme,
            "Message": self.message,
        }


class Lexer:
    """Lexical Analyzer for the CompilerX language."""

    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.errors: List[LexicalError] = []

    def _current_char(self) -> Optional[str]:
        if self.pos >= self.length:
            return None
        return self.source[self.pos]

    def _peek_char(self, offset: int = 1) -> Optional[str]:
        idx = self.pos + offset
        if idx >= self.length:
            return None
        return self.source[idx]

    def _advance(self) -> Optional[str]:
        ch = self._current_char()
        if ch is None:
            return None
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def tokenize(self) -> Tuple[List[Token], List[LexicalError]]:
        """Scans the entire source string and returns (tokens, lexical_errors)."""
        self.tokens = []
        self.errors = []

        while self.pos < self.length:
            ch = self._current_char()

            # 1. Skip whitespace
            if ch in (" ", "\t", "\r", "\n"):
                self._advance()
                continue

            # 2. Check for comments or division operator
            if ch == "/":
                nxt = self._peek_char()
                if nxt == "/":
                    # Single-line comment
                    self._advance()
                    self._advance()
                    while self._current_char() is not None and self._current_char() != "\n":
                        self._advance()
                    continue
                elif nxt == "*":
                    # Multi-line comment
                    start_line, start_col = self.line, self.column
                    self._advance()
                    self._advance()
                    closed = False
                    while self._current_char() is not None:
                        if self._current_char() == "*" and self._peek_char() == "/":
                            self._advance()
                            self._advance()
                            closed = True
                            break
                        self._advance()
                    if not closed:
                        self.errors.append(
                            LexicalError(
                                message="Unterminated multi-line comment '/* ... */'",
                                line=start_line,
                                column=start_col,
                                lexeme="/*",
                            )
                        )
                    continue

            # 3. String literals
            if ch in ('"', "'"):
                self._scan_string(ch)
                continue

            # 4. Numeric literals (int or float)
            if ch.isdigit():
                self._scan_number()
                continue

            # 5. Identifiers and keywords
            if ch.isalpha() or ch == "_":
                self._scan_identifier_or_keyword()
                continue

            # 6. Multi-character and single-character operators / delimiters
            self._scan_operator_or_delimiter()

        self.tokens.append(Token(TokenType.EOF, "EOF", self.line, self.column))
        return self.tokens, self.errors

    def _scan_string(self, quote_char: str) -> None:
        start_line, start_col = self.line, self.column
        self._advance()  # Consume opening quote
        chars: List[str] = []

        while self._current_char() is not None:
            ch = self._current_char()
            if ch == quote_char:
                self._advance()  # Consume closing quote
                value = "".join(chars)
                self.tokens.append(
                    Token(TokenType.STRING_LITERAL, value, start_line, start_col)
                )
                return
            if ch == "\n":
                # Unterminated string before newline
                self.errors.append(
                    LexicalError(
                        message=f"Unterminated string literal starting with {quote_char}",
                        line=start_line,
                        column=start_col,
                        lexeme=quote_char + "".join(chars),
                    )
                )
                return
            if ch == "\\":
                self._advance()
                esc = self._current_char()
                if esc is None:
                    break
                escape_map = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}
                chars.append(escape_map.get(esc, esc))
                self._advance()
            else:
                chars.append(self._advance())

        self.errors.append(
            LexicalError(
                message=f"Unterminated string literal reaching end of file",
                line=start_line,
                column=start_col,
                lexeme=quote_char + "".join(chars),
            )
        )

    def _scan_number(self) -> None:
        start_line, start_col = self.line, self.column
        num_chars: List[str] = []
        dot_count = 0

        while self._current_char() is not None and (
            self._current_char().isdigit() or self._current_char() == "."
        ):
            if self._current_char() == ".":
                dot_count += 1
            num_chars.append(self._advance())

        # Check for invalid trailing identifier characters directly attached to number (e.g., 123abc)
        if self._current_char() is not None and (
            self._current_char().isalpha() or self._current_char() == "_"
        ):
            while self._current_char() is not None and (
                self._current_char().isalnum() or self._current_char() in ("_", ".")
            ):
                num_chars.append(self._advance())
            bad_lexeme = "".join(num_chars)
            self.errors.append(
                LexicalError(
                    message=f"Invalid numeric literal or identifier '{bad_lexeme}' (identifiers cannot start with a digit)",
                    line=start_line,
                    column=start_col,
                    lexeme=bad_lexeme,
                )
            )
            return

        lexeme = "".join(num_chars)
        if dot_count > 1 or lexeme.endswith("."):
            self.errors.append(
                LexicalError(
                    message=f"Malformed floating-point literal '{lexeme}'",
                    line=start_line,
                    column=start_col,
                    lexeme=lexeme,
                )
            )
            return

        if dot_count == 1:
            self.tokens.append(
                Token(TokenType.FLOAT_LITERAL, float(lexeme), start_line, start_col)
            )
        else:
            self.tokens.append(
                Token(TokenType.INT_LITERAL, int(lexeme), start_line, start_col)
            )

    def _scan_identifier_or_keyword(self) -> None:
        start_line, start_col = self.line, self.column
        chars: List[str] = []
        while self._current_char() is not None and (
            self._current_char().isalnum() or self._current_char() == "_"
        ):
            chars.append(self._advance())

        word = "".join(chars)
        token_type = KEYWORDS.get(word, TokenType.IDENTIFIER)
        if token_type == TokenType.TRUE:
            self.tokens.append(Token(token_type, True, start_line, start_col))
        elif token_type == TokenType.FALSE:
            self.tokens.append(Token(token_type, False, start_line, start_col))
        else:
            self.tokens.append(Token(token_type, word, start_line, start_col))

    def _scan_operator_or_delimiter(self) -> None:
        start_line, start_col = self.line, self.column
        ch = self._current_char()
        nxt = self._peek_char()

        # Two-character operators
        two_char_ops = {
            "==": TokenType.EQ,
            "!=": TokenType.NEQ,
            "<=": TokenType.LTE,
            ">=": TokenType.GTE,
            "&&": TokenType.AND,
            "||": TokenType.OR,
            "+=": TokenType.PLUS_ASSIGN,
            "-=": TokenType.MINUS_ASSIGN,
            "*=": TokenType.STAR_ASSIGN,
            "/=": TokenType.SLASH_ASSIGN,
        }
        if nxt is not None and (ch + nxt) in two_char_ops:
            op_str = ch + nxt
            self._advance()
            self._advance()
            self.tokens.append(Token(two_char_ops[op_str], op_str, start_line, start_col))
            return

        # Check for single '&' or '|' which are invalid in our subset unless doubled
        if ch in ("&", "|"):
            self._advance()
            expected = ch * 2
            self.errors.append(
                LexicalError(
                    message=f"Invalid operator '{ch}'. Did you mean '{expected}'?",
                    line=start_line,
                    column=start_col,
                    lexeme=ch,
                )
            )
            return

        # Single-character operators and delimiters
        single_char_ops = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "=": TokenType.ASSIGN,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "!": TokenType.NOT,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ";": TokenType.SEMICOLON,
            ",": TokenType.COMMA,
        }
        if ch in single_char_ops:
            self._advance()
            self.tokens.append(Token(single_char_ops[ch], ch, start_line, start_col))
            return

        # Invalid / unrecognized character
        bad_char = self._advance()
        self.errors.append(
            LexicalError(
                message=f"Unrecognized character '{bad_char}'",
                line=start_line,
                column=start_col,
                lexeme=bad_char,
            )
        )
