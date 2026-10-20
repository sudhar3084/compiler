"""
app.py — Interactive Streamlit Web Interface & CLI Runner for CompilerX.

Title: CompilerX — A Mini Compiler with Code Optimization and Execution
Technology: Python, Streamlit, and standard Python libraries.

Provides:
- Source code editor with 7 example programs + custom file upload
- Compile & Run, Compile Only, Clear, and Reset buttons
- Configurable safety limits (Max Execution Steps & Max Output Lines)
- Interactive Tabs for all 7 Compiler Phases:
  1. Program Output & Diagnostics Console
  2. Side-by-Side Original vs. Optimized Code Comparison & Optimization Log
  3. Phase 1: Lexical Analysis (Token Table & Category Breakdown)
  4. Phase 2: Syntax Analysis (Graphviz Visual AST, ASCII Tree & JSON AST)
  5. Phase 3: Semantic Analysis (Scoped Symbol Table & Type/Scope Checks)
  6. Phase 4 & 5: Intermediate Code (Three-Address Code & Optimization Metrics)
  7. Phase 6: Target Code Generation (Stack-VM Bytecode & Register Pseudo-Assembly)
"""

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from code_generator import format_target_code
from intermediate_code import format_tac
from interpreter import CompilationReport, CompilerPipeline
from sample_programs import SAMPLE_PROGRAMS


DEFAULT_EXAMPLE_KEY = "1. Quick Start: Arithmetic & If/Else (Default)"


def _build_unified_diff(original_text: str, optimized_text: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            original_text.splitlines(),
            optimized_text.splitlines(),
            fromfile="Original_TAC.ir",
            tofile="Optimized_TAC.ir",
            lineterm="",
        )
    )
    return "\n".join(diff_lines) if diff_lines else "// Original and Optimized TAC are identical."


def render_streamlit_app() -> None:
    """Renders the full Streamlit web application."""
    import streamlit as st

    st.set_page_config(
        page_title="CompilerX — Mini Compiler & Optimizer",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for clean cards, badges, and console styling
    st.markdown(
        """
        <style>
        .main-header {
            background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 100%);
            color: #ffffff;
            padding: 1.4rem 1.8rem;
            border-radius: 12px;
            margin-bottom: 1.2rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        }
        .main-header h1 {
            margin: 0;
            font-size: 1.85rem;
            font-weight: 700;
            color: #ffffff;
        }
        .main-header p {
            margin: 0.35rem 0 0 0;
            font-size: 0.98rem;
            color: #cbd5e1;
        }
        .console-box {
            background-color: #0d1117;
            color: #3fb950;
            font-family: 'Courier New', Courier, monospace;
            padding: 1.1rem 1.3rem;
            border-radius: 8px;
            border: 1px solid #30363d;
            min-height: 110px;
            white-space: pre-wrap;
            font-size: 0.96rem;
            line-height: 1.5;
        }
        .console-error {
            background-color: #2d1215;
            color: #ff7b72;
            font-family: 'Courier New', Courier, monospace;
            padding: 1.1rem 1.3rem;
            border-radius: 8px;
            border: 1px solid #f85149;
            white-space: pre-wrap;
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header Banner
    st.markdown(
        """
        <div class="main-header">
            <h1>⚡ CompilerX — A Mini Compiler with Code Optimization and Execution</h1>
            <p>End-to-End Educational Compiler Pipeline: Lexical Analysis • Recursive-Descent AST • Semantic Type Checker • TAC • Multi-Pass Optimizer • Stack VM & Safe Interpreter</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Initialize Session State
    if "selected_example" not in st.session_state:
        st.session_state.selected_example = DEFAULT_EXAMPLE_KEY
    if "source_code" not in st.session_state:
        st.session_state.source_code = SAMPLE_PROGRAMS[DEFAULT_EXAMPLE_KEY]["code"]
    if "editor_key_counter" not in st.session_state:
        st.session_state.editor_key_counter = 0
    if "last_report" not in st.session_state:
        pipeline = CompilerPipeline()
        st.session_state.last_report = pipeline.compile_and_run(
            st.session_state.source_code, run_program=True
        )

    # Sidebar Controls & Language Reference
    with st.sidebar:
        st.header("🛠️ Compiler Controls")

        example_names = list(SAMPLE_PROGRAMS.keys())
        chosen_example = st.selectbox(
            "📚 Load Example Program",
            options=example_names,
            index=example_names.index(st.session_state.selected_example)
            if st.session_state.selected_example in example_names
            else 0,
            help="Choose one of the pre-built sample programs to explore CompilerX features.",
        )

        if chosen_example != st.session_state.selected_example:
            st.session_state.selected_example = chosen_example
            st.session_state.source_code = SAMPLE_PROGRAMS[chosen_example]["code"]
            st.session_state.editor_key_counter += 1
            pipeline = CompilerPipeline()
            st.session_state.last_report = pipeline.compile_and_run(
                st.session_state.source_code, run_program=True
            )
            st.rerun()

        st.caption(SAMPLE_PROGRAMS[chosen_example]["description"])

        st.divider()
        st.subheader("⚙️ Execution Guardrails")
        max_steps = st.slider(
            "Max Interpreter Steps (Loop Guard)",
            min_value=100,
            max_value=50000,
            value=10000,
            step=500,
            help="Prevents infinite while-loops from freezing the application.",
        )
        max_output_lines = st.slider(
            "Max Output Console Lines",
            min_value=50,
            max_value=2000,
            value=500,
            step=50,
            help="Caps maximum printed lines during execution.",
        )

        st.divider()
        with st.expander("📖 CompilerX Language Quick Guide", expanded=False):
            st.markdown(
                """
                **Supported Types:**
                - `int`, `float`, `bool`, `string`

                **Declarations & Assignments:**
                ```c
                int x = 10;
                float pi = 3.14;
                bool ok = true;
                string msg = "Hello";
                x = x + 5;
                ```

                **Operators:**
                - Arithmetic: `+`, `-`, `*`, `/`, `%`
                - Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
                - Logical: `&&` (`and`), `||` (`or`), `!` (`not`)

                **Control Flow & Output:**
                ```c
                if (x > 10) {
                    print(x);
                } else {
                    print("Small");
                }

                while (x > 0) {
                    x = x - 1;
                }
                ```
                """
            )

    # Main Workspace Layout: Editor + Action Bar
    col_editor, col_quick_status = st.columns([3, 2], gap="large")

    with col_editor:
        st.subheader("📝 Source Code Editor (`.cx`)")
        editor_widget_key = f"code_editor_{st.session_state.editor_key_counter}"
        current_code = st.text_area(
            label="Write or edit your C-like CompilerX program below:",
            value=st.session_state.source_code,
            height=330,
            key=editor_widget_key,
        )
        st.session_state.source_code = current_code

        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
        with btn_col1:
            compile_and_run_clicked = st.button(
                "▶️ Compile & Run", type="primary", use_container_width=True
            )
        with btn_col2:
            compile_only_clicked = st.button(
                "🔨 Compile Only", use_container_width=True
            )
        with btn_col3:
            reset_clicked = st.button(
                "🔄 Reset Example", use_container_width=True
            )
        with btn_col4:
            clear_clicked = st.button(
                "🗑️ Clear Editor", use_container_width=True
            )

        if reset_clicked:
            st.session_state.source_code = SAMPLE_PROGRAMS[st.session_state.selected_example]["code"]
            st.session_state.editor_key_counter += 1
            pipeline = CompilerPipeline(max_steps=max_steps, max_output_lines=max_output_lines)
            st.session_state.last_report = pipeline.compile_and_run(
                st.session_state.source_code, run_program=True
            )
            st.rerun()

        if clear_clicked:
            st.session_state.source_code = ""
            st.session_state.editor_key_counter += 1
            st.session_state.last_report = None
            st.rerun()

        if compile_and_run_clicked:
            pipeline = CompilerPipeline(max_steps=max_steps, max_output_lines=max_output_lines)
            st.session_state.last_report = pipeline.compile_and_run(
                st.session_state.source_code, run_program=True
            )

        if compile_only_clicked:
            pipeline = CompilerPipeline(max_steps=max_steps, max_output_lines=max_output_lines)
            st.session_state.last_report = pipeline.compile_and_run(
                st.session_state.source_code, run_program=False
            )

    report: CompilationReport = st.session_state.last_report

    with col_quick_status:
        st.subheader("🖥️ Program Output & Status")
        if report is None or not st.session_state.source_code.strip():
            st.info("Enter source code in the editor and click **Compile & Run** to begin.")
        elif report.has_errors:
            st.error(
                f"Compilation halted with {len(report.all_error_messages)} error(s)."
            )
            err_text = "\n".join(report.all_error_messages)
            st.markdown(
                f'<div class="console-error">{err_text}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.success(
                f"Compilation succeeded in {report.compilation_time_ms:.2f} ms!"
            )
            if report.optimized_execution is not None:
                exec_res = report.optimized_execution
                if exec_res.runtime_error:
                    st.error("Runtime Error Encountered")
                    st.markdown(
                        f'<div class="console-error">{exec_res.runtime_error.format()}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    out_display = (
                        exec_res.output_text
                        if exec_res.output_lines
                        else "(Program executed successfully with no printed output)"
                    )
                    st.markdown(
                        f'<div class="console-box">{out_display}</div>',
                        unsafe_allow_html=True,
                    )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Output Equivalence", "Verified ✓" if report.outputs_match else "Mismatch!")
                    c2.metric("VM Steps Executed", exec_res.steps_executed)
                    c3.metric("Exec Time", f"{exec_res.execution_time_ms:.2f} ms")
            else:
                st.info("Compiled without execution (`Compile Only` mode). Click **Compile & Run** to execute.")

            if report.semantic_warnings:
                with st.expander(f"⚠️ Semantic Warnings ({len(report.semantic_warnings)})", expanded=True):
                    for w in report.semantic_warnings:
                        st.warning(w.format())

    if report is None or not st.session_state.source_code.strip():
        return

    st.divider()

    # Top-Level Compilation & Optimization Metrics Bar
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Tokens Scanned", len(report.tokens))
    m2.metric(
        "Symbols Declared",
        len(report.symbol_table.all_symbols) if report.symbol_table else 0,
    )
    orig_tac_len = len(report.original_tac)
    opt_tac_len = len(report.optimized_tac)
    m3.metric("Original TAC", orig_tac_len)
    m4.metric(
        "Optimized TAC",
        opt_tac_len,
        delta=f"-{orig_tac_len - opt_tac_len} instr" if orig_tac_len >= opt_tac_len else None,
        delta_color="inverse",
    )
    reduction_pct = (
        report.optimization_metrics.reduction_percentage
        if report.optimization_metrics
        else 0.0
    )
    m5.metric("TAC Reduction", f"{reduction_pct}%")
    m6.metric(
        "Target Instructions",
        len(report.optimized_target_code),
        delta=f"-{len(report.unoptimized_target_code) - len(report.optimized_target_code)} ops"
        if len(report.unoptimized_target_code) >= len(report.optimized_target_code)
        else None,
        delta_color="inverse",
    )

    # Detailed Phase Inspection Tabs
    tabs = st.tabs(
        [
            "🔄 1. Code Optimization & Comparison",
            "🔤 2. Lexical Analysis (Tokens)",
            "🌳 3. Syntax Analysis (AST)",
            "📋 4. Semantic Analysis & Symbols",
            "⚙️ 5. Intermediate Code (TAC)",
            "💻 6. Target Code & Assembly",
            "📊 7. Runtime Memory & Statistics",
        ]
    )

    # Tab 1: Side-by-Side Comparison of Original vs Optimized Code
    with tabs[0]:
        st.subheader("Original vs. Optimized Intermediate & Target Code Comparison")
        if report.has_errors:
            st.warning("Fix compilation errors above to view code optimization results.")
        else:
            col_orig, col_opt = st.columns(2)
            orig_tac_str = format_tac(report.original_tac)
            opt_tac_str = format_tac(report.optimized_tac)

            with col_orig:
                st.markdown(f"**Original Three-Address Code ({len(report.original_tac)} instructions)**")
                st.code(orig_tac_str, language="c")

            with col_opt:
                st.markdown(f"**Optimized Three-Address Code ({len(report.optimized_tac)} instructions)**")
                st.code(opt_tac_str, language="c")

            if report.optimization_metrics:
                opt_m = report.optimization_metrics
                oc1, oc2, oc3, oc4 = st.columns(4)
                oc1.metric("Constant Foldings", opt_m.constant_foldings)
                oc2.metric("Constant Propagations", opt_m.constant_propagations)
                oc3.metric(
                    "Algebraic / CSE Simplifications",
                    opt_m.algebraic_simplifications + opt_m.common_subexpressions_eliminated,
                )
                oc4.metric("Dead Instructions Removed", opt_m.dead_instructions_removed)

                with st.expander("🔍 Step-by-Step Optimization Transformations Log", expanded=True):
                    if opt_m.optimization_log:
                        for idx, entry in enumerate(opt_m.optimization_log, 1):
                            st.markdown(f"`{idx:02d}.` {entry}")
                    else:
                        st.info("No optimizations were applicable (code is already minimal).")

                with st.expander("📄 Unified Diff (Original TAC vs. Optimized TAC)", expanded=False):
                    st.code(_build_unified_diff(orig_tac_str, opt_tac_str), language="diff")

    # Tab 2: Lexical Analysis
    with tabs[1]:
        st.subheader("Phase 1: Lexical Analysis — Token Stream")
        if report.lexical_errors:
            st.error(f"Found {len(report.lexical_errors)} Lexical Error(s):")
            st.table([e.to_dict() for e in report.lexical_errors])

        if report.tokens:
            token_dicts = [t.to_dict() for t in report.tokens]
            st.dataframe(token_dicts, use_container_width=True, hide_index=True)
        else:
            st.info("No tokens found.")

    # Tab 3: Syntax Analysis (AST)
    with tabs[2]:
        st.subheader("Phase 2: Syntax Analysis — Abstract Syntax Tree (AST)")
        if report.syntax_errors:
            st.error(f"Found {len(report.syntax_errors)} Syntax Error(s):")
            st.table([e.to_dict() for e in report.syntax_errors])
        elif report.ast:
            ast_sub1, ast_sub2, ast_sub3 = st.tabs(
                ["🎨 Visual Graphviz Diagram", "🌲 ASCII Tree Hierarchy", "📦 Serialized JSON AST"]
            )
            with ast_sub1:
                try:
                    st.graphviz_chart(report.ast_graphviz_dot, use_container_width=True)
                except Exception:
                    st.code(report.ast_graphviz_dot, language="dot")
            with ast_sub2:
                st.code(report.ast_tree_str, language="text")
            with ast_sub3:
                st.json(report.ast.to_dict())

    # Tab 4: Semantic Analysis & Symbol Table
    with tabs[3]:
        st.subheader("Phase 3: Semantic Analysis & Symbol Table")
        if report.semantic_errors:
            st.error(f"Found {len(report.semantic_errors)} Semantic Error(s):")
            st.table([e.to_dict() for e in report.semantic_errors])
        else:
            st.success("All variable declarations, scopes, types, and operations passed semantic validation.")

        if report.symbol_table and report.symbol_table.all_symbols:
            st.markdown("#### Scoped Symbol Table")
            st.dataframe(
                report.symbol_table.to_list_of_dicts(),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No symbols declared in the program.")

    # Tab 5: Intermediate Code (TAC)
    with tabs[4]:
        st.subheader("Phase 4 & 5: Three-Address Code (TAC) Quadruple Table")
        if report.has_errors:
            st.warning("TAC generation skipped due to upstream errors.")
        else:
            tac_view_col1, tac_view_col2 = st.columns(2)
            with tac_view_col1:
                st.markdown("#### Unoptimized TAC Quadruples")
                st.dataframe(
                    [instr.to_dict(i) for i, instr in enumerate(report.original_tac, 1)],
                    use_container_width=True,
                    hide_index=True,
                )
            with tac_view_col2:
                st.markdown("#### Optimized TAC Quadruples")
                st.dataframe(
                    [instr.to_dict(i) for i, instr in enumerate(report.optimized_tac, 1)],
                    use_container_width=True,
                    hide_index=True,
                )

    # Tab 6: Target Code Generation
    with tabs[5]:
        st.subheader("Phase 6: Target Code Generation (Stack-VM & Pseudo-Assembly)")
        if report.has_errors:
            st.warning("Target code generation skipped due to upstream errors.")
        else:
            tgt_col1, tgt_col2 = st.columns(2)
            with tgt_col1:
                st.markdown(
                    f"#### Stack-VM Bytecode ({len(report.optimized_target_code)} instructions)"
                )
                st.code(format_target_code(report.optimized_target_code), language="nasm")
                with st.expander("View Unoptimized Stack-VM Bytecode"):
                    st.code(format_target_code(report.unoptimized_target_code), language="nasm")
            with tgt_col2:
                st.markdown("#### Register-Based Pseudo-Assembly")
                st.code(report.pseudo_assembly, language="nasm")
                with st.expander("View Target Instruction Table"):
                    st.dataframe(
                        [
                            instr.to_dict(i)
                            for i, instr in enumerate(report.optimized_target_code)
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

    # Tab 7: Runtime Memory State & Compilation Statistics
    with tabs[6]:
        st.subheader("Phase 7: Program Execution Memory State & Pipeline Summary")
        if report.has_errors:
            st.warning("Program execution skipped due to compilation errors.")
        elif report.optimized_execution:
            mem_col, stat_col = st.columns(2)
            with mem_col:
                st.markdown("#### Final Variable Memory State (Post-Execution)")
                vars_dict = report.optimized_execution.variables
                if vars_dict:
                    mem_rows = [
                        {
                            "Variable": k,
                            "Runtime Type": type(v).__name__,
                            "Final Value": str(v),
                        }
                        for k, v in vars_dict.items()
                    ]
                    st.dataframe(mem_rows, use_container_width=True, hide_index=True)
                else:
                    st.info("No user variables in final memory state.")

            with stat_col:
                st.markdown("#### Optimization & Execution Metrics Summary")
                if report.optimization_metrics:
                    metrics_dict: Dict[str, Any] = report.optimization_metrics.to_dict()
                    metrics_dict["Compilation Time (ms)"] = f"{report.compilation_time_ms:.3f} ms"
                    metrics_dict["Unoptimized Runtime Steps"] = (
                        report.unoptimized_execution.steps_executed
                        if report.unoptimized_execution
                        else 0
                    )
                    metrics_dict["Optimized Runtime Steps"] = (
                        report.optimized_execution.steps_executed
                    )
                    metrics_dict["Semantic Equivalence Verified"] = (
                        "Yes (Identical Output)" if report.outputs_match else "Mismatch"
                    )
                    summary_rows = [
                        {"Metric": k, "Value": str(v)} for k, v in metrics_dict.items()
                    ]
                    st.dataframe(summary_rows, use_container_width=True, hide_index=True)


def run_cli(file_path: Optional[str] = None) -> int:
    """Command-line interface for running CompilerX without a browser."""
    if file_path:
        source = Path(file_path).read_text(encoding="utf-8")
        title = file_path
    else:
        source = SAMPLE_PROGRAMS[DEFAULT_EXAMPLE_KEY]["code"]
        title = DEFAULT_EXAMPLE_KEY

    print("=" * 72)
    print(f"CompilerX CLI — Compiling & Running: {title}")
    print("=" * 72)

    pipeline = CompilerPipeline()
    report = pipeline.compile_and_run(source, run_program=True)

    if report.has_errors:
        print("\n[COMPILATION FAILED]")
        for err in report.all_error_messages:
            print(" ", err)
        return 1

    print(f"\n[1] Lexical Analysis: {len(report.tokens)} tokens scanned.")
    print(f"[2] Syntax Analysis: AST built successfully.")
    print(
        f"[3] Semantic Analysis: {len(report.symbol_table.all_symbols) if report.symbol_table else 0} symbols verified."
    )
    print("\n[4] Original Three-Address Code (TAC):")
    print(format_tac(report.original_tac))

    print("\n[5] Optimized Three-Address Code (TAC):")
    print(format_tac(report.optimized_tac))
    if report.optimization_metrics:
        print(
            f"    -> Reduced from {report.optimization_metrics.original_instruction_count} to "
            f"{report.optimization_metrics.optimized_instruction_count} instructions "
            f"({report.optimization_metrics.reduction_percentage}% reduction)."
        )

    print("\n[6] Target Code (Stack-VM Bytecode):")
    print(format_target_code(report.optimized_target_code))

    if report.optimized_execution:
        print("\n[7] Program Runtime Output:")
        print("-" * 40)
        print(report.optimized_execution.output_text)
        print("-" * 40)
        print(f"Final Variables: {report.optimized_execution.variables}")
        print(f"Unoptimized vs Optimized Output Match: {report.outputs_match}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--cli", "-c"):
        target_file = sys.argv[2] if len(sys.argv) > 2 else None
        sys.exit(run_cli(target_file))
    else:
        render_streamlit_app()
