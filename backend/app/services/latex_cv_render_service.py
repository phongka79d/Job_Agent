"""Render CV drafts through a stored LaTeX template."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


class LatexCvRenderService:
    """Compiles a sanitized draft preview into PDF using a local LaTeX compiler."""

    def write_pdf(
        self,
        output_path: Path,
        *,
        template_source: str,
        preview: dict[str, Any],
    ) -> Path:
        compiler = self._detect_compiler()
        if compiler is None:
            raise RuntimeError("LaTeX compiler is not installed. Install tectonic or pdflatex to export LaTeX CV templates.")

        rendered_source = self.render_template_source(template_source, preview)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp_dir:
            workdir = Path(tmp_dir)
            tex_path = workdir / "cv_draft.tex"
            tex_path.write_text(rendered_source, encoding="utf-8")
            if Path(compiler).stem.lower() == "tectonic":
                command = [compiler, "--outdir", str(workdir), str(tex_path)]
            else:
                command = [
                    compiler,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-no-shell-escape",
                    tex_path.name,
                ]
            result = subprocess.run(
                command,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            compiled_path = workdir / "cv_draft.pdf"
            if result.returncode != 0 or not compiled_path.exists():
                detail = (result.stderr or result.stdout or "unknown LaTeX error").strip()
                raise RuntimeError(f"LaTeX CV template failed to compile: {detail[:800]}")
            output_path.write_bytes(compiled_path.read_bytes())
        return output_path

    def render_template_source(self, template_source: str, preview: dict[str, Any]) -> str:
        edit_section = self._render_edit_section(preview)
        if "{{AI_TARGETED_EDITS}}" in template_source:
            return template_source.replace("{{AI_TARGETED_EDITS}}", edit_section)
        if "\\end{document}" in template_source:
            return template_source.replace("\\end{document}", f"{edit_section}\n\\end{{document}}", 1)
        return f"{template_source}\n{edit_section}"

    @staticmethod
    def _detect_compiler() -> str | None:
        for executable in ("tectonic", "pdflatex"):
            resolved = shutil.which(executable)
            if resolved:
                return resolved
        return None

    def _render_edit_section(self, preview: dict[str, Any]) -> str:
        edits = [edit for edit in preview.get("edits", []) if isinstance(edit, dict)]
        if not edits:
            return ""
        lines = ["\\section{AI Targeted CV Draft}", "\\begin{itemize}"]
        for edit in edits:
            requirement = self._escape_latex(str(edit.get("requirement") or "Requirement"))
            proposed_edit = self._escape_latex(str(edit.get("proposed_edit") or "").strip())
            if proposed_edit:
                lines.append(f"    \\item \\textbf{{{requirement}:}} {proposed_edit}")
        lines.append("\\end{itemize}")
        return "\n".join(lines)

    @staticmethod
    def _escape_latex(value: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        return "".join(replacements.get(char, char) for char in value)
