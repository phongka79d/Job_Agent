"""Deterministic CV structure extraction from text-based PDFs."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re


POOR_STRUCTURE_RECOMMENDATION = (
    "The current PDF structure is not reliable enough for structure-preserving edits. "
    "I recommend converting it into a cleaner CV template before editing."
)

KNOWN_HEADINGS = {
    "summary",
    "profile",
    "experience",
    "work experience",
    "projects",
    "education",
    "skills",
    "certifications",
    "certificates",
    "awards",
}


@dataclass(frozen=True)
class CvSection:
    heading: str
    content: str
    bullets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CvStructureResult:
    status: str
    confidence: float
    sections: list[CvSection]
    warnings: list[str]
    recommendation: str | None = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "status": self.status,
                "confidence": self.confidence,
                "sections": [
                    {
                        "heading": section.heading,
                        "content": section.content,
                        "bullets": section.bullets,
                    }
                    for section in self.sections
                ],
                "warnings": self.warnings,
                "recommendation": self.recommendation,
            },
            separators=(",", ":"),
        )


class CvStructureExtractionService:
    def analyze(self, text: str) -> CvStructureResult:
        normalized = (text or "").replace("\r\n", "\n").strip()
        if not normalized:
            return CvStructureResult(
                status="unreliable",
                confidence=0.0,
                sections=[],
                warnings=["No extracted text available."],
                recommendation=POOR_STRUCTURE_RECOMMENDATION,
            )

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        sections = self._split_sections(lines)
        bullet_count = sum(len(section.bullets) for section in sections)
        heading_count = len(sections)
        table_noise = sum(1 for line in lines if "|" in line or "\t" in line)

        score = 0.0
        warnings: list[str] = []
        if heading_count >= 4:
            score += 0.45
        elif heading_count >= 2:
            score += 0.25
        else:
            warnings.append("Few recognizable CV headings were detected.")

        if bullet_count >= 3:
            score += 0.25
        elif bullet_count >= 1:
            score += 0.1
        else:
            warnings.append("Few bullet groups were detected.")

        if len(lines) >= 8:
            score += 0.2
        elif len(lines) >= 3:
            score += 0.1

        if table_noise >= max(2, len(lines) // 4):
            score -= 0.35
            warnings.append("Table-like text extraction noise was detected.")

        confidence = max(0.0, min(1.0, round(score, 2)))
        if confidence >= 0.75:
            status = "reliable"
            recommendation = None
        elif confidence >= 0.25:
            status = "partial"
            recommendation = None
        else:
            status = "unreliable"
            recommendation = POOR_STRUCTURE_RECOMMENDATION

        return CvStructureResult(
            status=status,
            confidence=confidence,
            sections=sections,
            warnings=warnings,
            recommendation=recommendation,
        )

    def _split_sections(self, lines: list[str]) -> list[CvSection]:
        sections: list[CvSection] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        for line in lines:
            if self._is_heading(line):
                if current_heading is not None:
                    sections.append(self._section(current_heading, current_lines))
                current_heading = self._clean_heading(line)
                current_lines = []
                continue
            if current_heading is not None:
                current_lines.append(line)

        if current_heading is not None:
            sections.append(self._section(current_heading, current_lines))
        return sections

    def _is_heading(self, line: str) -> bool:
        cleaned = self._clean_heading(line).casefold()
        if cleaned in KNOWN_HEADINGS:
            return True
        return bool(re.fullmatch(r"[A-Z][A-Za-z ]{2,32}", line)) and len(line.split()) <= 4

    def _clean_heading(self, line: str) -> str:
        return re.sub(r"[:\-]+$", "", line.strip())

    def _section(self, heading: str, lines: list[str]) -> CvSection:
        bullets = [
            line.lstrip("-*• ").strip()
            for line in lines
            if line.startswith(("-", "*", "•"))
        ]
        return CvSection(
            heading=heading,
            content="\n".join(lines).strip(),
            bullets=[bullet for bullet in bullets if bullet],
        )
