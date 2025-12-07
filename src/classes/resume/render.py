from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.resume.resume import Resume, ResumeItem


class ResumeRender(ABC):
    @abstractmethod
    def render(self, resume: Resume) -> str: ...


class TextResumeRenderer(ResumeRender):
    def render(self, resume: Resume) -> str:
        to_return = ""
        to_return += f"Email: {resume.email}\n\n" if resume.email else ""
        to_return += f"Core skills {", ".join(resume.skills)}\n\n" if resume.skills else ""

        for item in resume.items:
            to_return += f"{item.title} : {item.start_date.strftime("%B, %Y")} - {item.end_date.strftime("%B, %Y")}\n"

            if len(item.frameworks) != 0:
                to_return += f"Frameworks: {", ".join(skill.skill_name for skill in item.frameworks)}\n"

            for bullet in item.bullet_points:
                to_return += f"   - {bullet}\n"
            if item is not resume.items[-1]:
                to_return += "\n"
            to_return += "\n"

        return to_return


LATEX_SPECIAL_CHARS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}


def latex_escape(text: str) -> str:
    return "".join(LATEX_SPECIAL_CHARS.get(c, c) for c in text)


# --- Renderer ---
class ResumeLatexRenderer(ResumeRender):
    """
    Generates a stable LaTeX resume using the Jake Gutierrez template.
    """

    prefix = r"""
\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\input{glyphtounicode}

% Formatting
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Clean margins
\usepackage[margin=0.7in]{geometry}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Section formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

% --- Custom Commands ---
\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
"""

    def render(self, resume: Resume) -> str:
        tex = [self.prefix, r"\begin{document}"]

        # Header
        tex.extend([
            r"\begin{center}",
            rf"\textbf{{\Huge \scshape Your Name}}\\[2pt]",
            r"\end{center}",
            "",
        ])

        # Projects
        tex.append(r"\section{Projects}")
        tex.append(r"\resumeSubHeadingListStart")

        for item in resume.items:
            title = latex_escape(item.title)
            date = f"{item.start_date.strftime("%B, %Y")} -- {item.end_date.strftime("%B, %Y")}"

            # Only include frameworks if there is at least one
            if len(item.frameworks) > 0:
                frameworks = ", ".join(
                    [latex_escape(f.skill_name) for f in item.frameworks])
                title_tex = rf"\textbf{{{title}}} $|$ \emph{{{frameworks}}}"
            else:
                title_tex = rf"\textbf{{{title}}}"

            tex.append(
                rf"\resumeProjectHeading"
                rf"{{{title_tex}}}"
                rf"{{{date}}}"
            )

            tex.append(r"\resumeItemListStart")
            for b in item.bullet_points:
                tex.append(rf"\resumeItem{{{latex_escape(b)}}}")
            tex.append(r"\resumeItemListEnd")

        tex.append(r"\resumeSubHeadingListEnd")
        tex.append("")

        # Skills
        if resume.skills:
            skills = ", ".join(latex_escape(s) for s in resume.skills)
            tex.append(r"\section{Technical Skills}")
            tex.append(r"\begin{itemize}[leftmargin=0.15in, label={}]")
            tex.append(rf"  \item {{{skills}}}")
            tex.append(r"\end{itemize}")

        tex.append(r"\end{document}")

        return "\n".join(tex)
