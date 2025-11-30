from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.resume.resume import Resume


class ResumeRender(ABC):
    @abstractmethod
    def render(self, resume: Resume) -> str: ...


class ResumeLatexRenderer(ResumeRender):
    def render(self, resume: Resume) -> str:
        tex = [
            r"\documentclass{article}",
            r"\usepackage[margin=1in]{geometry}",
            r"\begin{document}",
            r"\section*{Experience}"
        ]

        for item in resume.items:
            tex.append(rf"\subsection*{{{item.title}}}")
            tex.append(rf"\textit{{{item.start_date} -- {item.end_date}}}\\")
            tex.append(r"\begin{itemize}")
            for b in item.bullet_points:
                tex.append(rf"\item {b}")
            tex.append(r"\end{itemize}")

        if resume.skills:
            tex.append(r"\section*{Skills}")
            tex.append(", ".join(resume.skills))

        tex.append(r"\end{document}")
        return "\n".join(tex)


class TextResumeRenderer(ResumeRender):
    def render(self, resume: Resume) -> str:
        to_return = ""

        for item in resume.items:
            to_return += f"{item.title} : {item.start_date} - {item.end_date}\n"
            for bullet in item.bullet_points:
                to_return += f"   - {bullet}\n"
            to_return += "\n"

        return to_return
