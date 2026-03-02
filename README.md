# Project Miner: Milestone 2

Team 18's project miner. This README has been updated with Milestone 2 requirements. This guide will walk you through the set up.

## Setup

This project is built with a API running in a docker container, and a front end built locally.

### Backend

The easiest way to start the back-end for the project is through a Dev Container.

**Prerequisites:**
- Docker
- Dev Container Extension on VSCode

**Steps:**
1. Clone, and open the repo folder in VSCode.
2. Accept the prompt to create a Dev Container or run the command `>Dev Containers: Open Folder in Container...`. Docker will build the container and install all pip packages within the contianer.
3. To download the `.env` file, you will need to log into your UBC Microsoft account. Follow to this link: https://ubcca-my.sharepoint.com/:u:/g/personal/sjsikora_student_ubc_ca/IQCss_DFCoE_TbVqdZxIKyvEATSWrX-LNnfKJ7RXmS6kJhM?e=bkpo6o , then run the command `source .env`
4. Once you are within the container run `cd miner && fastapi dev ./src/interface/api/api.py` to start the API.

Note if you get a `sqlalchemy.exc.OperationalError` it is likely because you are not cd-ed into miner.

Verify the API and container is running by going to http://127.0.0.1:8000/ping in your browser. You should see "pong". To view the Swagger UI docs vist http://127.0.0.1:8000/docs.

### Frontend

While M2 may be run and verified straight from Swagger, we also do have a in-progress front end. While it is not fully fleshed out, it provides an interactive experience and providing here for completeness.

**Prerequisites:**
- npm

**Steps:**
1. Clone the repo and cd into the `ui/` folder.
2. Install the packages with `npm install`.
3. Then, run the webserver with `npm run dev`.

Vite will print `http://localhost:5173` for the web renderer. For the Electron app, use the Electron window that opens when running npm run dev.

If you run into errors, check the `ui/README.md` for more detailed instructions.

## Requirements

The full list of Milestone 2 requirements has been completed

### R21

**Allow incremental information by adding another zipped folder of files for the same portfolio or résumé that incorporates additional information at a later point in time**

To showcase this, if you upload the early project and create a resume and portfolio, upload the later project, then call the portfolio and resume refresh endpoints, you will see the updated changes.

### R22

**Recognize duplicate files and maintains only one in the system**

Duplicate files are recongnized by file path, and only one file (or internally called FileReports) are maintained.

### R23

**Allow users to choose which information is represented (e.g., re-ranking of projects, corrections to chronology, attributes for project comparison, skills to highlight, projects selected for showcase)**

This use case can be achieved through editing the portfolio or resume.

### R24

**Incorporate a key role of the user in a given project**

A user will be given roles in a project based on their commit habits. For example, an output may be "The user is a Contributor who demonstrates a bursty work pattern, primarily focusing on documentation and feature development, with a significant number of commits in a short time frame."

### R25

**Incorporate evidence of success (e.g., metrics, feedback, evaluation) for a given project**

Evidence of success is included in project summaries by naming the specific features each project has. For example, an output may be "EarthLingo aims to enhance phonics education through pronunciation feedback and speech recognition using a tech stack that includes React, Next.js, TypeScript, and Speech Recognition." or "The TouristHelperApp aims to facilitate event management and trip planning by enabling users to add events, search for events, create trips, and generate itineraries. "

### R26

**Allow user to associate a portfolio image for a given project to use as the thumbnail**

### R27

**Customize and save information about a portfolio showcase project**

The endpoint `/projects/{project_name}/showcase/customization` allows users to edit and save information about their portoflio showcase project.

### R28

**Customize and save the wording of a project used for a résumé item**

The endpoint `POST /resume/{resume_id}/edit/bullet_point` can be used to edit the wording of a resume project.

### R29

**Display textual information about a project as a portfolio showcase**

The textual information portfolio showcase item can be retrieve with the endpoint ``. Users will select their portoflio showcase, and that information will be displayed

### R30

**Display textual information about a project as a résumé item**

Here is an example of a resume item. It contains textual information:
```
COSC310Group : January, 2025 - April, 2025
Frameworks: tkinter, pytest, typing
   - Project was coded using the Python language
   - Utilized skills: CI/CD, Web Development, Testing
   - Collaborated in a team of 7 contributors
   - Authored 59.16% of commits
   - Accounted for 63.5% of total contribution in the final deliverable
   - During the project, I split my contributions between following acitivity types: 66% on code, 34% on test
   - The user is a key contributor to the project, focusing primarily on bug fixes and feature enhancements, with a strong emphasis on refactoring and maintaining documentation.
   - Work pattern: bursty
   - Primary contribution focus: fix (35%); Secondary: feat (25%)
```

### R31

**Use a FastAPI to faciliate the communication between the backend and the frontend**

Achieved. We use FastAPI for our API needs.

### R33/R34

Google Drive Link to the Zipped Folder: https://drive.google.com/file/d/1M0gzxZIEF1atHYQo4MammYUo7qcb4Fpz/view?usp=sharing

### R35

**Your API endpoints must be tested as if they are being called over HTTP but without running a real server, ensuring the correct status code and expected data.**

Endpoints are tested over HTTP.

### R36

**Your system must have clear documentation for all of the API endpoints**

See this README, the Swagger docs, and the code docstring.
