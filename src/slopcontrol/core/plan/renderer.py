"""Plan renderer – convert ``DesignPlan`` → Markdown, and parse back.

Output filename: ``plan_forge.md`` (the primary artifact).
"""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from .schema import DesignPlan


class PlanRenderer:
    """Render and parse ``plan_forge.md`` files."""

    SEPARATOR = "\n---\n"

    def render(self, plan: DesignPlan) -> str:
        """Return full markdown text for the plan artifact."""
        lines: list[str] = []

        # ── YAML frontmatter ─────────────────────────────────────────
        front = yaml.safe_dump(plan.to_frontmatter(), sort_keys=False)
        lines.append("---")
        lines.append(front.rstrip())
        lines.append("---")

        # ── Requirements ─────────────────────────────────────────────
        if plan.requirements:
            lines.append("")
            lines.append("# Requirements")
            for req in plan.requirements:
                lines.append(f"- {req}")

        # ── Design Decisions ─────────────────────────────────────────
        if plan.decisions:
            lines.append("")
            lines.append("# Design Decisions")
            for i, d in enumerate(plan.decisions, 1):
                title = d.get("title", f"Decision {i}")
                decision = d.get("decision", "")
                rationale = d.get("rationale", "")
                lines.append(f"")
                lines.append(f"## {i}. {title}")
                lines.append(f"- **Decision:** {decision}")
                if rationale:
                    lines.append(f"- **Rationale:** {rationale}")
                for k, v in d.items():
                    if k not in ("title", "decision", "rationale"):
                        lines.append(f"- **{k}:** {v}")

        # ── Implementation Steps ─────────────────────────────────────
        if plan.implementation_steps:
            lines.append("")
            lines.append("# Implementation Steps")
            for i, step in enumerate(plan.implementation_steps, 1):
                desc = step.get("description", "")
                lines.append(f"{i}. {desc}")
                script = step.get("script", "")
                if script:
                    lines.append(f"   - **Script:** `{script}`")
                for k, v in step.items():
                    if k not in ("description", "script"):
                        lines.append(f"   - **{k}:** {v}")

        # ── Verification Log ───────────────────────────────────────
        if plan.verification_log:
            lines.append("")
            lines.append("# Verification Log")
            lines.append("| Version | Check | Result | Notes |")
            lines.append("|---|---|---|---|")
            for entry in plan.verification_log:
                lines.append(
                    f"| {entry.get('version','')} | {entry.get('check','')} |"
                    f" {entry.get('result','')} | {entry.get('notes','')} |"
                )

        # ── Appendices ───────────────────────────────────────────────
        if plan.appendices:
            lines.append("")
            lines.append("# Appendices")
            for i, apx in enumerate(plan.appendices, 1):
                title = apx.get("title", f"Appendix {i}")
                lines.append(f"")
                lines.append(f"## Appendix {chr(64 + i)}: {title}")
                content = apx.get("content", "")
                lines.append(content)

        return "\n".join(lines) + "\n"

    def write(self, plan: DesignPlan, path: Path) -> None:
        """Render and write to disk."""
        path.write_text(self.render(plan), encoding="utf-8")

    # ── Parsing ──────────────────────────────────────────────────

    def parse(self, text: str) -> DesignPlan:
        """Parse a ``plan_forge.md`` string back into ``DesignPlan``."""
        # Extract YAML frontmatter
        fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        if not fm_match:
            raise ValueError("Missing YAML frontmatter in plan_forge.md")

        front = yaml.safe_load(fm_match.group(1))
        body = text[fm_match.end() :]

        plan = DesignPlan.from_frontmatter(front or {})

        # Parse sections by headings
        sections = self._split_sections(body)
        plan.requirements = self._parse_bullets(sections.get("requirements", ""))
        plan.decisions = self._parse_decisions(sections.get("design decisions", ""))
        plan.implementation_steps = self._parse_steps(
            sections.get("implementation steps", "")
        )
        plan.verification_log = self._parse_verification(
            sections.get("verification log", "")
        )
        plan.appendices = self._parse_appendices(sections.get("appendices", ""))

        return plan

    def read(self, path: Path) -> DesignPlan:
        """Read a plan file from disk."""
        return self.parse(path.read_text(encoding="utf-8"))

    # ── Helpers ──────────────────────────────────────────────────

    def _split_sections(self, body: str) -> dict[str, str]:
        """Split markdown body by ``# Heading`` into dict[lower_title, content]."""
        pattern = re.compile(r"^# (.+)$", re.MULTILINE)
        matches = list(pattern.finditer(body))
        sections: dict[str, str] = {}
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            sections[m.group(1).strip().lower()] = body[start:end].strip()
        return sections

    def _parse_bullets(self, text: str) -> list[str]:
        return [line.lstrip("- ").strip() for line in text.splitlines() if line.strip().startswith("-")]

    def _parse_decisions(self, text: str) -> list[dict[str, Any]]:
        decisions: list[dict[str, Any]] = []
        blocks = re.split(r"\n## \d+\. ", text)
        for block in blocks[1:]:
            lines = block.splitlines()
            title = lines[0].strip()
            entry: dict[str, Any] = {"title": title}
            for line in lines[1:]:
                m = re.match(r"- \*\*(.+?)\*\*:\s*(.*)", line)
                if m:
                    entry[m.group(1).lower()] = m.group(2).strip()
            if entry:
                decisions.append(entry)
        return decisions

    def _parse_steps(self, text: str) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        for line in text.splitlines():
            m = re.match(r"(\d+)\.\s*(.+)", line)
            if m:
                steps.append({"description": m.group(2).strip()})
            elif steps and line.strip().startswith("-"):
                kv = re.match(r"- \*\*(.+?)\*\*:\s*`?(.+?)`?\s*$", line)
                if kv:
                    steps[-1][kv.group(1).lower()] = kv.group(2).strip()
        return steps

    def _parse_verification(self, text: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for line in text.splitlines():
            if line.startswith("|") and "version" not in line.lower():
                cols = [c.strip() for c in line.split("|")]
                cols = [c for c in cols if c]
                if len(cols) >= 4:
                    entries.append(
                        {
                            "version": cols[0],
                            "check": cols[1],
                            "result": cols[2],
                            "notes": cols[3],
                        }
                    )
        return entries

    def _parse_appendices(self, text: str) -> list[dict[str, Any]]:
        appendices: list[dict[str, Any]] = []
        blocks = re.split(r"\n## Appendix [A-Z]: ", text)
        for block in blocks[1:]:
            lines = block.splitlines()
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            appendices.append({"title": title, "content": content})
        return appendices


# ── Convenience functions ────────────────────────────────────────

def render_plan(plan: DesignPlan, path: Path) -> None:
    """One-shot render."""
    PlanRenderer().write(plan, path)


def read_plan(path: Path) -> DesignPlan:
    """One-shot read."""
    return PlanRenderer().read(path)
