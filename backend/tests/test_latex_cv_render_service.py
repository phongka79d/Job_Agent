import pytest
from types import SimpleNamespace

from app.services.latex_cv_render_service import LatexCvRenderService


def test_render_template_source_replaces_placeholder_and_escapes_edit_text() -> None:
    template = "\\documentclass{article}\\begin{document}{{AI_TARGETED_EDITS}}\\end{document}"
    preview = {
        "edits": [
            {
                "requirement": "Python & SQL",
                "proposed_edit": "Emphasize 80% faster ETL with C_1 pipeline.",
            }
        ]
    }

    rendered = LatexCvRenderService().render_template_source(template, preview)

    assert "{{AI_TARGETED_EDITS}}" not in rendered
    assert "\\section{AI Targeted CV Draft}" in rendered
    assert "Python \\& SQL" in rendered
    assert "80\\% faster ETL with C\\_1 pipeline" in rendered


def test_write_pdf_fails_clearly_when_latex_compiler_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="LaTeX compiler is not installed"):
        LatexCvRenderService().write_pdf(
            tmp_path / "draft.pdf",
            template_source="\\documentclass{article}\\begin{document}\\end{document}",
            preview={"edits": []},
        )


def test_write_pdf_uses_tectonic_arguments_for_resolved_executable_path(
    tmp_path,
    monkeypatch,
) -> None:
    compiler_path = str(tmp_path / "tectonic.exe")
    monkeypatch.setattr(
        "shutil.which",
        lambda name: compiler_path if name == "tectonic" else None,
    )
    commands: list[list[str]] = []

    def fake_run(command, *, cwd, **kwargs):
        commands.append(command)
        (cwd / "cv_draft.pdf").write_bytes(b"%PDF-template")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    output_path = LatexCvRenderService().write_pdf(
        tmp_path / "draft.pdf",
        template_source="\\documentclass{article}\\begin{document}\\end{document}",
        preview={"edits": []},
    )

    assert commands[0][:3] == [compiler_path, "--outdir", commands[0][2]]
    assert output_path.read_bytes() == b"%PDF-template"
