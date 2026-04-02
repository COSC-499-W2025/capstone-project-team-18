# Project Miner -- System Diagrams

---

## 1. System Architecture

Shows the full deployment topology: the desktop application layers, backend layers, persistence, AI/ML services, and external GitHub services.

```mermaid
graph TB
    subgraph Client["Client -- Desktop Application"]
        Electron["Electron Shell"]
        ReactUI["React + TypeScript UI\nVite / MUI / Tailwind CSS"]
        Electron <-->|"Electron IPC"| ReactUI
    end

    subgraph Backend["Backend -- FastAPI (Python 3.12)"]
        Routers["API Routers\nprojects / resume / portfolio / skills\ninsights / interview / job_readiness\ngithub / user_config / privacy_consent"]
        ServiceLayer["Service Layer\nMiningService / PortfolioService / ResumeService\nSkillsService / InterviewService / JobReadinessService"]

        subgraph CoreLayer["Core Layer"]
            Analyzers["File Analyzers\nPython / JS / TS / Java / C\nHTML / CSS / PHP"]
            Stats["Statistic Calculators\nProjectDates / CodingLanguageRatio\nGitAuthorship / ProjectSkills\nCommitPatterns / ProjectWeight"]
            Reports["Report Builders\nFileReport / ProjectReport\nResumeItem / PortfolioCard"]
            ML["ML Inference\nAzure OpenAI (narratives, summaries)\nBERTopic / KeyBERT (README analysis)"]
        end

        Routers --> ServiceLayer
        ServiceLayer --> Analyzers
        ServiceLayer --> Stats
        ServiceLayer --> Reports
        ServiceLayer --> ML
        Analyzers --> Stats --> Reports
    end

    subgraph Persistence["Persistence"]
        DB[("SQLite Database\ndata.db\n\nUserConfig / ResumeConfig\nProjectReport / FileReport\nPortfolio / Resume / Insights")]
    end

    GitHub(["GitHub"])

    ReactUI <-->|"REST / HTTP + JSON"| Routers
    Reports <-->|"SQL via SQLAlchemy"| DB
    Backend <-->|"GitHub API"| GitHub
```

---

## 2. DFD Level 0 -- Context Diagram

Shows the system as a single process with all external entities and top-level data flows across the system boundary.

```mermaid
flowchart LR
    User(["User"])
    GHOAuth(["GitHub OAuth"])
    GHPages(["GitHub Pages"])
    FS(["Local File System"])

    System["0\nProject Miner\nSystem"]

    User -->|"project archive ZIP\nuser profile & config\nproject selections\ncustomizations & edits"| System
    System -->|"project & file reports\nresume PDF/LaTeX/DOCX\nportfolio\ninsights & interview questions\njob readiness report"| User

    FS -->|"project source files\n(via upload)"| System

    System <-->|"OAuth authorization request\n/ access token"| GHOAuth

    System -->|"static portfolio site"| GHPages
```

---

## 3. DFD Level 1 -- System Processes

Decomposes the system into 4 core processes, 4 data stores, and the same external entities from Level 0.

**External Entities:** User / GitHub OAuth / GitHub Pages / Local File System
**Data Stores:** D1 User Config/Resume Config / D2 Project Reports/File Reports / D3 Resumes / D4 Portfolios

```mermaid
flowchart TB
    %% External Entities
    User(["User"])
    GHOAuth(["GitHub OAuth"])
    GHPages(["GitHub Pages"])
    FS(["Local File System"])

    %% Data Stores
    D1[(D1\nUser Config\nResume Config)]
    D2[(D2\nProject Reports\nFile Reports)]
    D3[(D3\nResumes)]
    D4[(D4\nPortfolios)]

    %% Processes
    P1("P1\nProject Upload &\nFile Analysis")
    P2("P2\nProject Report\nAggregation")
    P3("P3\nResume\nGeneration")
    P4("P4\nPortfolio\nGeneration")

    %% P1: Project Upload & File Analysis
    User -->|"ZIP archive\nuser config & profile"| P1
    FS -->|"project source files"| P1
    P1 <-->|"OAuth request / token"| GHOAuth
    P1 -->|"user config, OAuth token\neducation & awards"| D1
    D1 -->|"user email\n(git blame salt)"| P1
    P1 -->|"FileReports\n(lines, functions, classes,\nlanguage, dates, contribution)"| D2

    %% P2: Project Report Aggregation
    D2 -->|"FileReports"| P2
    P2 -->|"ProjectReport\n(skills, frameworks, dates,\nwork patterns, project weight)"| D2
    D2 -->|"project & file reports"| User

    %% P3: Resume Generation
    User -->|"project selection\ncustomizations"| P3
    D2 -->|"ProjectReports"| P3
    D1 -->|"education, awards,\nglobal skills"| P3
    P3 -->|"Resume + ResumeItems"| D3
    D3 -->|"resume data"| User
    P3 -->|"PDF / LaTeX / DOCX"| User

    %% P4: Portfolio Generation
    User -->|"project selection\nnarrative edits\nshowcase toggles"| P4
    D2 -->|"ProjectReports"| P4
    P4 -->|"Portfolio\n(sections, blocks,\nproject cards)"| D4
    D4 -->|"portfolio data\n(with conflict resolution)"| User
    P4 -->|"static HTML/CSS site"| GHPages
```
