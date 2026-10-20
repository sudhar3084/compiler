"""
tests/test_compiler.py — Comprehensive Automated Unit Test Suite for CompilerX.

Tests all 7 compiler phases and UI integration:
1. Lexical Analysis: Valid tokens, comments, strings, floats, and lexical errors
   (invalid characters, malformed numbers, unterminated strings/comments).
2. Syntax Analysis: AST structure, operator precedence, nested control flow,
   compound assignments, and syntax error detection with line/column numbers.
3. Semantic Analysis: Scoped symbol table, duplicate declarations, undeclared variables,
   type mismatches, invalid modulo/condition types, and compile-time division by zero.
4. Intermediate Code Generation: Three-Address Code (TAC) generation for arithmetic,
   if/else branches, and while loops.
5. Code Optimization: Constant folding, constant propagation, algebraic identity
   simplification, common subexpression elimination (CSE), dead-code elimination (DCE),
   and semantic equivalence between unoptimized and optimized TAC.
6. Target Code Generation: Stack-VM bytecode and Register Pseudo-Assembly generation.
7. Program Execution: Safe TACInterpreter and StackVMInterpreter execution, runtime
   division-by-zero detection, infinite loop step-limit protection, output line-limit
   protection, and verification across all sample programs.
"""

import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure CompilerX root directory is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ast_nodes import BinaryOp, VarDecl, WhileStmt, ast_to_graphviz_dot, format_ast_tree
from code_generator import format_target_code
from interpreter import CompilerPipeline, StackVMInterpreter
from lexer import Lexer, TokenType
from parser import Parser
from sample_programs import SAMPLE_PROGRAMS
from semantic_analyzer import SemanticAnalyzer


class TestPhase1Lexer(unittest.TestCase):
    """Unit tests for Phase 1: Lexical Analysis."""

    def test_valid_tokens_and_keywords(self):
        code = 'int x = 10; float y = 3.14; bool flag = true; string s = "hi";'
        tokens, errors = Lexer(code).tokenize()
        self.assertEqual(len(errors), 0)
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        self.assertIn(TokenType.INT_KW, types)
        self.assertIn(TokenType.FLOAT_KW, types)
        self.assertIn(TokenType.BOOL_KW, types)
        self.assertIn(TokenType.STRING_KW, types)
        self.assertIn(TokenType.INT_LITERAL, types)
        self.assertIn(TokenType.FLOAT_LITERAL, types)
        self.assertIn(TokenType.STRING_LITERAL, types)

    def test_single_and_multiline_comments_ignored(self):
        code = """
        // Single line comment
        int a = 5; /* inline block comment */
        /* multi-line
           comment */
        print(a);
        """
        tokens, errors = Lexer(code).tokenize()
        self.assertEqual(len(errors), 0)
        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        self.assertEqual(len(non_eof), 10)

    def test_lexical_error_invalid_characters(self):
        code = "int x = 10 @ $ #;"
        _, errors = Lexer(code).tokenize()
        self.assertEqual(len(errors), 3)
        self.assertEqual(errors[0].lexeme, "@")
        self.assertEqual(errors[0].line, 1)

    def test_lexical_error_malformed_numbers_and_identifiers(self):
        code = "float a = 12.34.56;\nint 99bad = 1;"
        _, errors = Lexer(code).tokenize()
        self.assertEqual(len(errors), 2)
        self.assertIn("Malformed floating-point", errors[0].message)
        self.assertEqual(errors[0].line, 1)
        self.assertIn("cannot start with a digit", errors[1].message)
        self.assertEqual(errors[1].line, 2)

    def test_lexical_error_unterminated_string_and_comment(self):
        code1 = 'print("unterminated string\n);'
        _, errors1 = Lexer(code1).tokenize()
        self.assertEqual(len(errors1), 1)
        self.assertIn("Unterminated string", errors1[0].message)

        code2 = "int x = 1; /* unclosed comment"
        _, errors2 = Lexer(code2).tokenize()
        self.assertEqual(len(errors2), 1)
        self.assertIn("Unterminated multi-line comment", errors2[0].message)


class TestPhase2Parser(unittest.TestCase):
    """Unit tests for Phase 2: Syntax Analysis & AST Construction."""

    def test_operator_precedence_ast(self):
        code = "int result = 10 + 20 * 2;"
        tokens, _ = Lexer(code).tokenize()
        program, errors = Parser(tokens).parse()
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(program.statements), 1)
        decl = program.statements[0]
        self.assertIsInstance(decl, VarDecl)
        self.assertIsInstance(decl.initializer, BinaryOp)
        self.assertEqual(decl.initializer.op, "+")
        self.assertIsInstance(decl.initializer.right, BinaryOp)
        self.assertEqual(decl.initializer.right.op, "*")

    def test_if_else_and_while_ast(self):
        code = """
        int i = 0;
        while (i < 3) {
            if (i == 1) {
                print("One");
            } else {
                print(i);
            }
            i += 1;
        }
        """
        tokens, _ = Lexer(code).tokenize()
        program, errors = Parser(tokens).parse()
        self.assertEqual(len(errors), 0)
        self.assertIsInstance(program.statements[1], WhileStmt)
        tree_str = format_ast_tree(program)
        dot_str = ast_to_graphviz_dot(program)
        self.assertIn("WhileStmt", tree_str)
        self.assertIn("IfStmt", tree_str)
        self.assertIn("digraph AST", dot_str)

    def test_syntax_error_missing_semicolon_and_paren(self):
        code = "int x = 10\nprint(x);"
        tokens, _ = Lexer(code).tokenize()
        _, errors = Parser(tokens).parse()
        self.assertGreaterEqual(len(errors), 1)
        self.assertIn("Expected ';'", errors[0].message)

        code2 = "if (x > 5 { print(x); }"
        tokens2, _ = Lexer(code2).tokenize()
        _, errors2 = Parser(tokens2).parse()
        self.assertGreaterEqual(len(errors2), 1)
        self.assertIn("Expected ')'", errors2[0].message)


class TestPhase3SemanticAnalyzer(unittest.TestCase):
    """Unit tests for Phase 3: Semantic Analysis & Type Checking."""

    def _analyze(self, code: str):
        tokens, lex_err = Lexer(code).tokenize()
        self.assertEqual(len(lex_err), 0)
        ast, syn_err = Parser(tokens).parse()
        self.assertEqual(len(syn_err), 0)
        return SemanticAnalyzer().analyze(ast)

    def test_valid_declarations_and_widening(self):
        code = "int a = 10; float b = a + 2.5; print(b);"
        sym_table, errors, _ = self._analyze(code)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(sym_table.all_symbols), 2)

    def test_duplicate_declaration_error(self):
        code = "int x = 5;\nint x = 10;"
        _, errors, _ = self._analyze(code)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].category, "Duplicate Declaration")
        self.assertEqual(errors[0].line, 2)

    def test_undeclared_variable_error(self):
        code = "int x = y + 1;"
        _, errors, _ = self._analyze(code)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].category, "Undeclared Variable")

    def test_type_mismatch_and_invalid_modulo(self):
        code = 'int x = "hello"; float f = 5.5 % 2.0;'
        _, errors, _ = self._analyze(code)
        self.assertEqual(len(errors), 2)
        categories = [e.category for e in errors]
        self.assertIn("Type Mismatch", categories)
        self.assertIn("Invalid Operation", categories)

    def test_compile_time_division_by_zero_detection(self):
        code = "int x = 100 / 0;"
        _, errors, _ = self._analyze(code)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].category, "Division by Zero")


class TestPhase4And5TACAndOptimization(unittest.TestCase):
    """Unit tests for Phase 4 (TAC Generation) and Phase 5 (Code Optimization)."""

    def test_constant_folding_and_propagation_and_dce(self):
        code = """
        int x = 10;
        int y = 20;
        int result = x + y * 2;
        print(result);
        if (result > 30) {
            print("Result is greater than 30");
        } else {
            print("Result is 30 or less");
        }
        """
        pipeline = CompilerPipeline()
        report = pipeline.compile_and_run(code)
        self.assertFalse(report.has_errors)
        self.assertLess(len(report.optimized_tac), len(report.original_tac))
        self.assertGreater(report.optimization_metrics.constant_foldings, 0)
        self.assertGreater(report.optimization_metrics.constant_propagations, 0)
        self.assertGreater(report.optimization_metrics.dead_instructions_removed, 0)

        expected_output = "50\nResult is greater than 30"
        self.assertEqual(report.optimized_execution.output_text, expected_output)
        self.assertEqual(report.unoptimized_execution.output_text, expected_output)
        self.assertTrue(report.outputs_match)

    def test_algebraic_identities_and_cse(self):
        code = """
        int a = 12;
        int b = 5;
        while (b < 8) {
            a = a + 1;
            b = b + 1;
        }
        int p = (a + b) * 1;
        int q = (a + b) + 0;
        int z = (a - a) + (b * 0);
        print(p);
        print(q);
        print(z);
        """
        pipeline = CompilerPipeline()
        report = pipeline.compile_and_run(code)
        self.assertFalse(report.has_errors)
        self.assertGreaterEqual(report.optimization_metrics.algebraic_simplifications, 3)
        self.assertGreaterEqual(report.optimization_metrics.common_subexpressions_eliminated, 1)
        self.assertEqual(report.optimized_execution.output_lines, ["23", "23", "0"])
        self.assertTrue(report.outputs_match)

    def test_while_loop_optimization_safety(self):
        """Ensures loop counters are NEVER unsoundly constant-propagated across loop iterations."""
        code = """
        int i = 1;
        int sum = 0;
        while (i <= 5) {
            sum = sum + i;
            i = i + 1;
        }
        print(sum);
        """
        pipeline = CompilerPipeline()
        report = pipeline.compile_and_run(code)
        self.assertFalse(report.has_errors)
        self.assertEqual(report.optimized_execution.output_text, "15")
        self.assertEqual(report.unoptimized_execution.output_text, "15")
        self.assertTrue(report.outputs_match)


class TestPhase6And7TargetGenAndInterpreter(unittest.TestCase):
    """Unit tests for Phase 6 (Target Code Generation) and Phase 7 (Safe Interpreter)."""

    def test_target_code_and_stack_vm_execution(self):
        code = """
        int x = 10;
        int y = 20;
        int result = x + y * 2;
        print(result);
        if (result > 30) {
            print("Result is greater than 30");
        } else {
            print("Result is 30 or less");
        }
        """
        pipeline = CompilerPipeline()
        report = pipeline.compile_and_run(code)
        stack_str = format_target_code(report.optimized_target_code)
        self.assertIn("PUSH_CONST", stack_str)
        self.assertIn("PRINT", stack_str)
        self.assertIn("HALT", stack_str)
        self.assertIn("OUT_LN", report.pseudo_assembly)

        vm = StackVMInterpreter()
        vm_unopt_res = vm.execute(report.unoptimized_target_code)
        vm_opt_res = vm.execute(report.optimized_target_code)
        self.assertEqual(vm_unopt_res.output_text, "50\nResult is greater than 30")
        self.assertEqual(vm_opt_res.output_text, "50\nResult is greater than 30")

    def test_runtime_division_by_zero_caught_safely(self):
        code = """
        int d = 5;
        while (d > 0) {
            d = d - 1;
        }
        int crash = 100 / d;
        print(crash);
        """
        pipeline = CompilerPipeline()
        report = pipeline.compile_and_run(code)
        self.assertFalse(report.has_errors)
        self.assertIsNotNone(report.optimized_execution.runtime_error)
        self.assertIn("Division by zero", report.optimized_execution.runtime_error.message)

    def test_infinite_loop_protection(self):
        code = """
        int x = 1;
        while (x > 0) {
            x = x + 1;
        }
        """
        pipeline = CompilerPipeline(max_steps=250)
        report = pipeline.compile_and_run(code)
        self.assertIsNotNone(report.optimized_execution.runtime_error)
        self.assertIn("step limit exceeded", report.optimized_execution.runtime_error.message)

    def test_output_line_limit_protection(self):
        code = """
        int i = 0;
        while (i < 100) {
            print(i);
            i = i + 1;
        }
        """
        pipeline = CompilerPipeline(max_output_lines=10)
        report = pipeline.compile_and_run(code)
        self.assertIsNotNone(report.optimized_execution.runtime_error)
        self.assertIn("Maximum output limit", report.optimized_execution.runtime_error.message)

    def test_all_curated_sample_programs(self):
        pipeline = CompilerPipeline()
        vm = StackVMInterpreter()
        for name, item in SAMPLE_PROGRAMS.items():
            report = pipeline.compile_and_run(item["code"])
            if "Intentional Errors" in name:
                self.assertTrue(report.has_errors, f"Expected errors in {name}")
                self.assertGreaterEqual(len(report.semantic_errors), 3)
            else:
                self.assertFalse(
                    report.has_errors,
                    f"Sample {name} failed compilation: {report.all_error_messages}",
                )
                self.assertTrue(
                    report.outputs_match,
                    f"Sample {name} output mismatch after optimization",
                )
                self.assertIsNone(report.optimized_execution.runtime_error)
                vm_res = vm.execute(report.optimized_target_code)
                self.assertEqual(
                    vm_res.output_text,
                    report.optimized_execution.output_text,
                    f"Stack-VM output mismatch on {name}",
                )


class TestStreamlitAppSmoke(unittest.TestCase):
    """Verifies that app.py CLI and Streamlit UI rendering execute without errors."""

    def test_cli_execution(self):
        import app

        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = app.run_cli()
        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("Result is greater than 30", output)

    def test_streamlit_render_function_with_mock(self):
        """Simulates Streamlit execution to verify all tabs and widgets in app.py run cleanly."""
        import app

        class DummySessionState(dict):
            def __getattr__(self, item):
                return self.get(item)

            def __setattr__(self, key, value):
                self[key] = value

        mock_st = types.ModuleType("streamlit")
        mock_st.session_state = DummySessionState()
        mock_st.set_page_config = MagicMock()
        mock_st.markdown = MagicMock()
        mock_st.header = MagicMock()
        mock_st.subheader = MagicMock()
        mock_st.caption = MagicMock()
        mock_st.divider = MagicMock()
        mock_st.info = MagicMock()
        mock_st.success = MagicMock()
        mock_st.warning = MagicMock()
        mock_st.error = MagicMock()
        mock_st.code = MagicMock()
        mock_st.json = MagicMock()
        mock_st.table = MagicMock()
        mock_st.dataframe = MagicMock()
        mock_st.graphviz_chart = MagicMock()
        mock_st.metric = MagicMock()
        mock_st.rerun = MagicMock()
        mock_st.sidebar = MagicMock()
        mock_st.expander = MagicMock()
        mock_st.selectbox = MagicMock(return_value=app.DEFAULT_EXAMPLE_KEY)
        mock_st.slider = MagicMock(side_effect=lambda label, **kw: kw.get("value", 1000))
        mock_st.text_area = MagicMock(
            return_value=SAMPLE_PROGRAMS[app.DEFAULT_EXAMPLE_KEY]["code"]
        )
        mock_st.button = MagicMock(return_value=False)

        def make_cols(spec, **kwargs):
            count = spec if isinstance(spec, int) else len(spec)
            cols = []
            for _ in range(count):
                c = MagicMock()
                c.__enter__ = MagicMock(return_value=c)
                c.__exit__ = MagicMock(return_value=False)
                cols.append(c)
            return cols

        mock_st.columns = MagicMock(side_effect=make_cols)
        mock_st.tabs = MagicMock(side_effect=lambda labels: make_cols(len(labels)))

        with patch.dict(sys.modules, {"streamlit": mock_st}):
            app.render_streamlit_app()

        self.assertTrue(mock_st.set_page_config.called)
        self.assertTrue(mock_st.tabs.called)
        self.assertTrue(mock_st.dataframe.called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
