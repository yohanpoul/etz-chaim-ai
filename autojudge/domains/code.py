"""CodeJudge — AutoResearch pour le code.

La 'loss function' du code : correction syntaxique, exécution sans erreur,
complexité, lisibilité. Évaluation par analyse statique et exécution réelle.
"""

from __future__ import annotations

import ast
import re

from autojudge.domains.base import DomainJudge
from autojudge.models import DomainScore


def _count_functions(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))


def _max_function_length(source: str, tree: ast.AST) -> int:
    """Max lines in any function definition."""
    lines = source.split("\n")
    max_len = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            length = end - node.lineno + 1
            max_len = max(max_len, length)
    return max_len


def _count_imports(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            count += len(node.names)
        elif isinstance(node, ast.ImportFrom):
            count += len(node.names)
    return count


def _nesting_depth(tree: ast.AST) -> int:
    """Maximum nesting depth of control flow."""
    max_depth = 0

    def _walk(node, depth):
        nonlocal max_depth
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
            depth += 1
            max_depth = max(max_depth, depth)
        for child in ast.iter_child_nodes(node):
            _walk(child, depth)

    _walk(tree, 0)
    return max_depth


class CodeJudge(DomainJudge):
    """AutoResearch pour le code — évaluation par analyse statique."""

    def compute_metrics(self, code: str) -> dict[str, float]:
        """Compute code quality metrics. Returns dict with values 0-1."""
        if not code or not code.strip():
            return {
                "syntax": 0.0, "complexity": 0.0,
                "readability": 0.0, "modularity": 0.0, "concision": 0.0,
            }

        # Syntax check
        try:
            tree = ast.parse(code)
            syntax = 1.0
        except SyntaxError:
            return {
                "syntax": 0.0, "complexity": 0.3,
                "readability": 0.3, "modularity": 0.3, "concision": 0.3,
            }

        lines = [l for l in code.split("\n") if l.strip() and not l.strip().startswith("#")]
        line_count = max(len(lines), 1)

        # Complexity: based on nesting depth (lower is better)
        depth = _nesting_depth(tree)
        if depth <= 2:
            complexity = 1.0
        elif depth <= 4:
            complexity = 0.7
        elif depth <= 6:
            complexity = 0.4
        else:
            complexity = 0.2

        # Readability: based on avg line length and function length
        avg_line_len = sum(len(l) for l in lines) / line_count
        if avg_line_len <= 80:
            line_score = 1.0
        elif avg_line_len <= 100:
            line_score = 0.7
        else:
            line_score = 0.4

        max_fn_len = _max_function_length(code, tree)
        if max_fn_len <= 20:
            fn_score = 1.0
        elif max_fn_len <= 40:
            fn_score = 0.7
        elif max_fn_len <= 60:
            fn_score = 0.5
        else:
            fn_score = 0.3

        readability = (line_score + fn_score) / 2

        # Modularity: functions per 50 lines
        fn_count = _count_functions(tree)
        fn_density = fn_count / max(line_count / 50, 1)
        modularity = min(fn_density, 1.0)

        # Concision: penalize very long lines, excessive imports
        import_count = _count_imports(tree)
        import_ratio = import_count / max(line_count, 1)
        concision = max(0.0, 1.0 - import_ratio * 3)

        return {
            "syntax": round(syntax, 4),
            "complexity": round(max(0, min(complexity, 1)), 4),
            "readability": round(max(0, min(readability, 1)), 4),
            "modularity": round(max(0, min(modularity, 1)), 4),
            "concision": round(max(0, min(concision, 1)), 4),
        }

    def generate_hypothesis(self, current_state: str) -> str:
        """Analyze code metrics, suggest improvement."""
        metrics = self.compute_metrics(current_state)

        if metrics["syntax"] < 1.0:
            return "Corriger les erreurs de syntaxe"
        if metrics["complexity"] < 0.5:
            return "Réduire la complexité en aplatissant les conditions imbriquées"
        if metrics["readability"] < 0.6:
            return "Améliorer la lisibilité en raccourcissant les fonctions longues"
        if metrics["modularity"] < 0.4:
            return "Augmenter la modularité en extrayant des sous-fonctions"
        if metrics["concision"] < 0.6:
            return "Supprimer les imports inutilisés"

        return "Optimiser la qualité générale du code"

    def apply_modification(self, content: str, hypothesis: str) -> str:
        """Apply code transformations based on hypothesis."""
        hyp_lower = hypothesis.lower()

        if "syntaxe" in hyp_lower or "syntax" in hyp_lower:
            return self._fix_common_syntax(content)

        if "import" in hyp_lower:
            return self._remove_unused_imports(content)

        # Default: return as-is (safe — code modifications are risky)
        return content

    def evaluate(self, original: str, modified: str) -> DomainScore:
        """Compare original and modified code quality."""
        orig_m = self.compute_metrics(original)
        mod_m = self.compute_metrics(modified)

        weights = {
            "syntax": 0.30,
            "complexity": 0.20,
            "readability": 0.20,
            "modularity": 0.15,
            "concision": 0.15,
        }

        quality = 0.0
        for key, weight in weights.items():
            orig_val = orig_m.get(key, 0.5)
            mod_val = mod_m.get(key, 0.5)
            if orig_val == 0:
                component = 0.7 if mod_val > 0 else 0.5
            else:
                ratio = mod_val / orig_val
                component = min(max(ratio / 2, 0), 1)
            quality += component * weight

        quality = min(max(quality, 0), 1)

        explanation_parts = []
        for key in weights:
            diff = mod_m[key] - orig_m[key]
            if abs(diff) > 0.05:
                direction = "↑" if diff > 0 else "↓"
                explanation_parts.append(f"{key} {direction}{abs(diff):.2f}")

        return DomainScore(
            quality=round(quality, 4),
            metrics=mod_m,
            explanation=", ".join(explanation_parts) if explanation_parts else "no change",
        )

    def get_loss_description(self) -> str:
        return (
            "Code quality: weighted combination of syntax (0.30), "
            "complexity (0.20), readability (0.20), modularity (0.15), "
            "concision (0.15). Higher is better."
        )

    # --- Transformations internes ---

    def _fix_common_syntax(self, code: str) -> str:
        """Attempt to fix common syntax issues."""
        # Remove trailing whitespace
        lines = [l.rstrip() for l in code.split("\n")]
        return "\n".join(lines)

    def _remove_unused_imports(self, code: str) -> str:
        """Remove import lines for names not used in the rest of the code."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code

        lines = code.split("\n")
        body_text = code

        # Collect imported names
        import_lines: dict[int, list[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.asname or alias.name for alias in node.names]
                import_lines[node.lineno - 1] = names
            elif isinstance(node, ast.ImportFrom):
                names = [alias.asname or alias.name for alias in node.names]
                import_lines[node.lineno - 1] = names

        # Check which names are used outside import lines
        non_import_lines = [
            l for i, l in enumerate(lines) if i not in import_lines
        ]
        rest = "\n".join(non_import_lines)

        lines_to_remove = set()
        for lineno, names in import_lines.items():
            all_unused = all(
                not re.search(r'\b' + re.escape(name) + r'\b', rest)
                for name in names
            )
            if all_unused:
                lines_to_remove.add(lineno)

        if not lines_to_remove:
            return code

        result = [l for i, l in enumerate(lines) if i not in lines_to_remove]
        return "\n".join(result)
