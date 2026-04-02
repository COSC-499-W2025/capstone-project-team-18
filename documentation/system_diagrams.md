# Project Miner — System Diagrams

---

## 1. System Architecture

Shows the full deployment topology: the desktop application layers, backend layers, persistence, AI/ML services, and external GitHub services.

```mermaid
graph TB
    %% Style Definitions
    classDef client fill:#e0f7fa,stroke:#006064,stroke-width:2px,color:#000;
    classDef backend fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000;
    classDef coreproc fill:#c8e6c9,stroke:#388e3c,stroke-width:2px,color:#000;
    classDef ai fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000;
    classDef external fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000;
    classDef db fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#000;

    subgraph Client["Client — Desktop Application"]
        Electron["Electron Shell"]:::client
        ReactUI["React + TypeScript UI\nVite · MUI · Tailwind CSS"]:::client
        Electron <-->|"Electron IPC"| ReactUI
    end

    subgraph AI_ML["AI / ML (internal to backend)"]
        CombinedAI(["AI Services\n\nAzure OpenAI (GPT-4o mini)\nLocal HuggingFace Models"]):::ai
    end

    subgraph Backend["Backend — FastAPI (Python 3.12)"]
        Routers["API Routers"]:::backend

        subgraph ServiceLayer["Service Layer"]
            MiningService["Mining"]:::backend
            PortfolioService["Portfolio"]:::backend
            ResumeService["Resume"]:::backend
            SkillsService["Skills"]:::backend
            InterviewService["Interview"]:::backend
            JobReadinessService["Job Readiness"]:::backend
        end

        subgraph CoreLayer["Core Layer"]
            P1("P1\nProject Upload &\nFile Analysis"):::coreproc
            P2("P2\nProject Report\nAggregation"):::coreproc
            P3("P3\nResume\nGeneration"):::coreproc
            P4("P4\nPortfolio\nGeneration"):::coreproc
            P1 ---> P2
            P2 ---> P3
            P2 ---> P4
        end

        Routers ---> MiningService
        Routers ---> PortfolioService
        Routers ---> ResumeService
        Routers ---> SkillsService
        Routers ---> InterviewService
        Routers ---> JobReadinessService

        MiningService ---> P1
        ResumeService ---> P3
        PortfolioService ---> P4
        SkillsService ---> P2
        InterviewService ---> P2
        JobReadinessService ---> P2
    end

    subgraph GitHub["GitHub (external)"]
        GHOAuth(["GitHub OAuth 2.0\nUser authentication"]):::external
        GHPages(["GitHub Pages\nPortfolio hosting"]):::external
    end

    subgraph Persistence["Persistence"]
        DB[("SQLite Database\ndata.db\n\nUserConfig · ResumeConfig\nProjectReport · FileReport\nPortfolio · Resume · Insights")]:::db
    end

    %% Main flow connections
    ReactUI <--->|"REST / HTTP + JSON"| Routers

    %% AI connections
    CoreLayer --->|"HTTPS API calls & Local Inference"| CombinedAI

    %% Database connections
    CoreLayer <--->|"SQL via SQLAlchemy"| DB

    %% GitHub connections
    PortfolioService --->|"GitHub API — deploy static site"| GHPages
    Backend <--->|"OAuth 2.0 flow"| GHOAuth

    %% Layout hints to force vertical stacking (AI -> GitHub -> DB)
    CombinedAI ~~~ GHOAuth
    GHOAuth ~~~ DB
    GHPages ~~~ DB
```

---

## 3. DFD Level 1 — System Processes

Decomposes the system into 4 core processes, 4 data stores, and the same external entities from Level 0.

**External Entities:** User / GitHub OAuth / GitHub Pages / Local File System
**Data Stores:** D1 User Config/Resume Config / D2 Project Reports/File Reports / D3 Resumes / D4 Portfolios

```mermaid
flowchart TB
    %% Style Definitions
    classDef entity fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000;
    classDef process fill:#c8e6c9,stroke:#388e3c,stroke-width:2px,color:#000;
    classDef datastore fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#000;

    %% External Entities
    User(["User"]):::entity
    GHOAuth(["GitHub OAuth"]):::entity
    GHPages(["GitHub Pages"]):::entity
    FS(["Local File System"]):::entity

    %% Data Stores
    D1[("D1\nUser Config\nResume Config")]:::datastore
    D2[("D2\nProject Reports\nFile Reports")]:::datastore
    D3[("D3\nResumes")]:::datastore
    D4[("D4\nPortfolios")]:::datastore

    %% Processes
    P1("P1\nProject Upload &\nFile Analysis"):::process
    P2("P2\nProject Report\nAggregation"):::process
    P3("P3\nResume\nGeneration"):::process
    P4("P4\nPortfolio\nGeneration"):::process

    %% P1: Project Upload & File Analysis
    User --->|"ZIP archive\nuser config & profile"| P1
    FS --->|"project source files"| P1
    P1 <--->|"OAuth request / token"| GHOAuth
    P1 --->|"user config, OAuth token\neducation & awards"| D1
    D1 --->|"user email"| P1
    P1 ---->|"FileReports"| D2

    %% P2: Project Report Aggregation
    D2 --->|"FileReports"| P2
    P2 ---->|"ProjectReport\n(skills, frameworks, dates,\nwork patterns, project weight)"| D2
    D2 ---->|"project & file reports"| User

    %% P3: Resume Generation
    User --->|"project selection\ncustomizations"| P3
    D2 --->|"ProjectReports"| P3
    D1 --->|"education, awards,\nglobal skills"| P3
    P3 --->|"Resume + ResumeItems"| D3
    D3 --->|"resume data"| User
    P3 --->|"PDF / LaTeX / DOCX"| User

    %% P4: Portfolio Generation
    User --->|"project selection\nnarrative edits\nshowcase toggles"| P4
    D2 --->|"ProjectReports"| P4
    P4 --->|"Portfolio\n(sections, blocks,\nproject cards)"| D4
    D4 --->|"portfolio data\n(with conflict resolution)"| User
    P4 --->|"static HTML/CSS site"| GHPages
```
