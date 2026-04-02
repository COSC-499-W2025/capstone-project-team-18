# Project Miner — System Diagrams

---

## 1. System Architecture

Shows the full deployment topology: the desktop application layers, backend layers, persistence, AI/ML services, and external GitHub services.

```mermaid
graph TB
    subgraph Client["Client — Desktop Application"]
        Electron["Electron Shell"]
        ReactUI["React + TypeScript UI\nVite · MUI · Tailwind CSS"]
        Electron <-->|"Electron IPC"| ReactUI
    end

    subgraph Backend["Backend — FastAPI (Python 3.12)"]
        Routers["API Routers\nprojects · resume · portfolio · skills\ninsights · interview · job_readiness\ngithub · user_config · privacy_consent"]
        ServiceLayer["Service Layer\nMiningService · PortfolioService · ResumeService\nSkillsService · InterviewService · JobReadinessService"]
        CoreLayer["Core Layer\nFile Analyzers · Statistic Calculators\nReport Builders · Insight Generators · ML Inference"]
        Routers --> ServiceLayer --> CoreLayer
    end

    subgraph Persistence["Persistence"]
        DB[("SQLite Database\ndata.db\n\nUserConfig · ResumeConfig\nProjectReport · FileReport\nPortfolio · Resume · Insights")]
    end

    subgraph AI_ML["AI / ML (internal to backend)"]
        AzureOAI(["Azure OpenAI\nGPT-4o mini\n\nNarrative generation · Summaries\nInterview · Job readiness"])
        LocalML(["Local HuggingFace Models\nBERTopic · KeyBERT · transformers\n\nREADME themes · keyphrases · tone"])
    end

    subgraph GitHub["GitHub (external)"]
        GHOAuth(["GitHub OAuth 2.0\nUser authentication"])
        GHPages(["GitHub Pages\nPortfolio hosting"])
    end

    ReactUI <-->|"REST / HTTP + JSON"| Routers
    CoreLayer <-->|"SQL via SQLAlchemy"| DB
    CoreLayer -->|"HTTPS API calls"| AzureOAI
    CoreLayer --> LocalML
    ServiceLayer -->|"GitHub API — deploy static site"| GHPages
    Backend <-->|"OAuth 2.0 flow"| GHOAuth
```

---

## 2. DFD Level 0 — Context Diagram

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

## 3. DFD Level 1 — System Processes

Decomposes the system into 9 processes, 5 data stores, and the same external entities from Level 0.

**External Entities:** User · GitHub OAuth · GitHub Pages · Local File System
**Data Stores:** D1 User Config/Resume Config · D2 Project Reports/File Reports · D3 Resumes · D4 Portfolios · D5 Insights

```mermaid
flowchart TB
    %% ── External Entities ──────────────────────────────────────────────
    User(["User"])
    GHOAuth(["GitHub OAuth"])
    GHPages(["GitHub Pages"])
    FS(["Local File System"])

    %% ── Data Stores ─────────────────────────────────────────────────────
    D1[(D1\nUser Config\nResume Config)]
    D2[(D2\nProject Reports\nFile Reports)]
    D3[(D3\nResumes)]
    D4[(D4\nPortfolios)]
    D5[(D5\nProject Insights)]

    %% ── Processes ────────────────────────────────────────────────────────
    P1("P1\nUser Setup &\nAuthentication")
    P2("P2\nProject Upload &\nFile Analysis")
    P3("P3\nProject Report\nAggregation")
    P4("P4\nSkills\nExtraction")
    P5("P5\nInsights\nGeneration")
    P6("P6\nResume\nGeneration")
    P7("P7\nPortfolio\nGeneration")
    P8("P8\nInterview\nGeneration")
    P9("P9\nJob Readiness\nAnalysis")

    %% ── P1: User Setup & Authentication ─────────────────────────────────
    User -->|"consent, profile info,\nGitHub username"| P1
    P1 <-->|"OAuth request / token"| GHOAuth
    P1 -->|"user config,\nOAuth token,\neducation & awards"| D1

    %% ── P2: Project Upload & File Analysis ──────────────────────────────
    User -->|"ZIP archive"| P2
    FS -->|"project source files"| P2
    D1 -->|"user email\n(git blame salt)"| P2
    P2 -->|"FileReports\n(lines, functions, classes,\nlanguage, dates, contribution)"| D2

    %% ── P3: Project Report Aggregation ──────────────────────────────────
    D2 -->|"FileReports"| P3
    P3 -->|"ProjectReport\n(skills, frameworks, dates,\nwork patterns, project weight)"| D2

    %% ── P4: Skills Extraction ────────────────────────────────────────────
    D2 -->|"ProjectReports"| P4
    P4 -->|"weighted skill scores\n(expert / intermediate / exposure)"| D1

    %% ── P5: Insights Generation ──────────────────────────────────────────
    D2 -->|"ProjectReports"| P5
    P5 -->|"ProjectInsights"| D5
    User -->|"dismiss insight"| P5
    D5 -->|"insights"| User

    %% ── P6: Resume Generation ────────────────────────────────────────────
    User -->|"project selection\ncustomizations"| P6
    D2 -->|"ProjectReports"| P6
    D1 -->|"education, awards,\nglobal skills"| P6
    P6 -->|"Resume +\nResumeItems"| D3
    D3 -->|"resume data"| User
    P6 -->|"PDF / LaTeX / DOCX"| User

    %% ── P7: Portfolio Generation ─────────────────────────────────────────
    User -->|"project selection\nnarrative edits\nshowcase toggles"| P7
    D2 -->|"ProjectReports"| P7
    P7 -->|"Portfolio\n(sections, blocks,\nproject cards)"| D4
    D4 -->|"portfolio data\n(with conflict resolution)"| User
    P7 -->|"static HTML/CSS site"| GHPages

    %% ── P8: Interview Generation ─────────────────────────────────────────
    User -->|"interview request"| P8
    D2 -->|"ProjectReports"| P8
    P8 -->|"interview questions\n& model answers"| User

    %% ── P9: Job Readiness Analysis ───────────────────────────────────────
    User -->|"job description"| P9
    D2 -->|"ProjectReports"| P9
    D1 -->|"user skills"| P9
    P9 -->|"readiness report\n& skill gaps"| User
```
