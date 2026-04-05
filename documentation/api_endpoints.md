# API Endpoint Reference

This document describes every HTTP endpoint exposed by the Capstone Project backend.
The backend is a **FastAPI** application that runs on `http://127.0.0.1:8000` in development.
Interactive Swagger UI is available at `http://127.0.0.1:8000/docs`.

---

## Table of Contents

- [Overview](#overview)
  - [Error Response Format](#error-response-format)
  - [Authentication](#authentication)
  - [ML Consent Gate](#ml-consent-gate)
- [Health Check](#health-check)
- [Projects](#projects)
- [Resume](#resume)
- [Portfolio](#portfolio)
- [Skills](#skills)
- [User Config](#user-config)
- [Job Readiness](#job-readiness)
- [Insights](#insights)
- [Interview](#interview)
- [GitHub OAuth](#github-oauth)

---

## Overview

### Error Response Format

All domain-level errors return a JSON body in the following shape:

```json
{
  "error_code": "PROJECT_NOT_FOUND",
  "message": "No project report named my-project"
}
```

Generic unhandled exceptions return:

```json
{
  "message": "An internal error occurred",
  "details": "..."
}
```

| `error_code` | HTTP Status | When it occurs |
|---|---|---|
| `PROJECT_NOT_FOUND` | 404 | A project name does not exist in the database |
| `RESUME_NOT_FOUND` | 404 | A resume ID does not exist |
| `USER_CONFIG_NOT_FOUND` | 404 | No user configuration has been created yet |
| `ID_NOT_FOUND` | 404 | A generic key lookup failed (e.g., portfolio) |
| `BAD_OAUTH_STATE` | 404 | Unknown GitHub OAuth state |
| `EXPIRED_OAUTH_STATE` | 410 | GitHub OAuth state older than 600 seconds |
| `AI_SERVICE_UNAVAILABLE` | 503 | ML consent not granted, or Azure OpenAI unreachable |
| `DATABASE_OPERATION_FAILED` | 500 | A database write/read failed unexpectedly |

### Authentication / Security

The backend and frontend of the system are meant to run locally in parallel on
the user's computer. This means, there is no authentication required to the API
as the only requests that can arrive to the API come from the user themselves.

### ML Consent Gate

Endpoints that call Azure OpenAI (job-readiness analysis, mock interview, and
ML-based project insights) check whether the user has granted machine-learning
consent (`ml_consent = true` in the user configuration). Requests without consent
receive a `503 AI_SERVICE_UNAVAILABLE` response.

---

## Health Check

### `GET /ping`

Liveness probe. Returns a literal string `"pong"`.

**Response**

```
200 OK
"pong"
```

No error cases.

---

## Projects

All endpoints are prefixed with `/projects`.

---

### `POST /projects/upload`

Upload and analyze a compressed project archive.

The archive is extracted, its source code is mined, and the resulting statistics
are stored as a `ProjectReportModel`. The most recent user configuration (email,
GitHub username, consent) is automatically applied during analysis.

**Supported archive formats:** `.tar.gz`, `.gz`, `.7z`, `.zip`

**Request**

| Location | Field | Type | Required | Description |
|---|---|---|---|---|
| Form | `file` | `UploadFile` | Yes | The compressed project archive |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `UploadProjectResponse` | Archive was successfully analyzed and saved |
| `400` | `{ "detail": "..." }` | File extension is not a supported archive format |
| `422` | `{ "detail": "..." }` | Archive content is malformed or invalid |
| `500 DATABASE_OPERATION_FAILED` | Error object | Unexpected processing failure |

**`UploadProjectResponse`**

```json
{
  "message": "Project uploaded and analyzed successfully"
}
```

---

### `GET /projects/`

List all project reports, ordered by `representation_rank` (ascending, nulls last),
then by `created_at`.

**Request** — No parameters.

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ProjectListResponse` | Success |
| `500 DATABASE_OPERATION_FAILED` | Error object | Unexpected database failure |

**`ProjectListResponse`**

```json
{
  "projects": [ /* ProjectReportResponse[] */ ],
  "count": 3
}
```

**`ProjectReportResponse`**

```json
{
  "project_name": "my-project",
  "user_config_used": 1,
  "image_data": "<base64-encoded string or null>",
  "created_at": "2024-01-15T10:00:00Z",
  "statistic": { /* mined statistics dict */ },
  "last_updated": "2024-01-15T10:05:00Z"
}
```

> `image_data` is base64-encoded when present. Pass the string directly into an
> HTML `<img src="data:image/...;base64,...">` tag.

---

### `GET /projects/{project_name}`

Retrieve the full report for a single project.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `project_name` | `string` | Exact name of the project (case-sensitive) |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ProjectReportResponse` | Success |
| `404 PROJECT_NOT_FOUND` | Error object | No project with that name exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Unexpected database failure |

---

### `POST /projects/{project_name}/image`

Attach a thumbnail image to a project. The uploaded file must have a `Content-Type`
header starting with `image/` (e.g. `image/png`, `image/jpeg`).

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `project_name` | `string` | Exact name of the project |

**Request**

| Location | Field | Type | Required | Description |
|---|---|---|---|---|
| Form | `file` | `UploadFile` | Yes | Image file (must be `image/*` content-type) |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `{ "message": "Image successfully assigned to project '...'." }` | Success |
| `400` | `{ "detail": "..." }` | File is not an image |
| `404 PROJECT_NOT_FOUND` | Error object | Project does not exist |
| `500 DATABASE_OPERATION_FAILED` | Error object | Save failed; changes were rolled back |

---

### `DELETE /projects/{project_name}/image`

Remove the thumbnail image from a project.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `project_name` | `string` | Exact name of the project |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `{ "message": "Image successfully removed from project '...'." }` | Success |
| `404 PROJECT_NOT_FOUND` | Error object | Project does not exist |
| `500 DATABASE_OPERATION_FAILED` | Error object | Removal failed; changes were rolled back |

---

## Resume

All endpoints are prefixed with `/resume`.

---

### `GET /resume`

List all saved resumes. Returns a lightweight summary for each — no resume items
or full content are included.

**Request** — No parameters.

**Response — `ResumeListResponse`**

```json
{
  "resumes": [
    {
      "id": 1,
      "title": "Software Engineer Resume",
      "email": "dev@example.com",
      "github": "devuser",
      "created_at": "2024-01-15T10:00:00Z",
      "last_updated": "2024-01-15T10:05:00Z",
      "item_count": 3,
      "project_names": ["proj-a", "proj-b", "proj-c"]
    }
  ],
  "count": 1
}
```

---

### `GET /resume/{resume_id}`

Retrieve a full resume by ID, including all items, skills, education, and awards.

If no categorized skills are stored on the resume, they are computed on the fly
from the user's project reports (expert ≥ 0.7 weight, intermediate ≥ 0.4, exposure < 0.4).

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Success |
| `404 RESUME_NOT_FOUND` | Error object | No resume with that ID exists |

**`ResumeResponse`**

```json
{
  "id": 1,
  "title": "Software Engineer Resume",
  "name": "Jane Doe",
  "location": "Vancouver, BC",
  "email": "jane@example.com",
  "github": "janedoe",
  "linkedin": "linkedin.com/in/janedoe",
  "skills": ["Python", "React", "Docker"],
  "skills_by_expertise": {
    "expert": ["Python"],
    "intermediate": ["React"],
    "exposure": ["Docker"]
  },
  "education": [
    { "title": "B.Sc. Computer Science, UBC", "start": "2019", "end": "2023" }
  ],
  "awards": [
    { "title": "Dean's List", "start": "2022", "end": null }
  ],
  "items": [ /* ResumeItemResponse[] */ ],
  "created_at": "2024-01-15T10:00:00Z",
  "last_updated": "2024-01-15T10:05:00Z"
}
```

**`ResumeItemResponse`**

```json
{
  "id": 5,
  "resume_id": 1,
  "project_name": "proj-a",
  "title": "Full-Stack Web Application",
  "frameworks": ["React", "FastAPI"],
  "bullet_points": [
    "Designed and implemented a REST API with FastAPI.",
    "Built a responsive frontend using React."
  ],
  "start_date": "2023-06-01",
  "end_date": "2023-12-01"
}
```

---

### `POST /resume/generate`

Generate a new resume from one or more project reports. Education and awards are
pulled from the user's `ResumeConfigModel` when a `user_config_id` is provided.
The generated resume is persisted and its full representation is returned.

**Request Body — `GenerateResumeRequest`**

```json
{
  "project_names": ["proj-a", "proj-b"],
  "user_config_id": 1,
  "title": "Software Engineer Resume"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `project_names` | `string[]` | Yes | Non-empty list of project names to include |
| `user_config_id` | `integer` | No | ID of the UserConfig to source education/awards from |
| `title` | `string` | No | Optional display title for the resume |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Resume generated and saved successfully |
| `400` | `{ "detail": "..." }` | `project_names` is empty |
| `404 PROJECT_NOT_FOUND` | Error object | A named project does not exist |
| `404 USER_CONFIG_NOT_FOUND` | Error object | The given `user_config_id` does not exist |
| `500 DATABASE_OPERATION_FAILED` | Error object | Generation or save failed; rolled back |

---

### `POST /resume/{resume_id}/refresh`

Re-generates a resume from its original source projects using the latest project
data, then overwrites the stored resume while preserving its ID.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Primary key of the resume record |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Resume refreshed and saved successfully |
| `400` | `{ "detail": "..." }` | The resume has no project items to refresh from |
| `404 RESUME_NOT_FOUND` | Error object | No resume exists with the given ID |
| `404 PROJECT_NOT_FOUND` | Error object | A source project no longer exists in the database |
| `500` | `{ "detail": "..." }` | Resume generation or persistence failed |

---

### `POST /resume/{resume_id}/edit/metadata`

Update the top-level metadata fields of an existing resume. Only provided
(non-null) fields are written; omitted fields are left unchanged.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `EditResumeMetadataRequest`** (all fields optional)

```json
{
  "title": "Updated Resume Title",
  "name": "Jane Doe",
  "location": "Vancouver, BC",
  "email": "jane@example.com",
  "github_username": "janedoe",
  "linkedin": "linkedin.com/in/janedoe"
}
```

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Update successful |
| `404` | `{ "detail": "..." }` | No resume with that ID exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Edit failed; changes were rolled back |

---

### `POST /resume/{resume_id}/edit/skills`

Replace the categorized skill lists for a resume. The flat `skills` list is
automatically rebuilt as the concatenation of `expert + intermediate + exposure`.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `EditSkillsRequest`**

```json
{
  "expert": ["Python", "FastAPI"],
  "intermediate": ["React", "Docker"],
  "exposure": ["Kubernetes"]
}
```

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Skills updated successfully |
| `404` | `{ "detail": "..." }` | No resume with that ID exists |
| `500` | `{ "detail": "..." }` | Edit failed; changes were rolled back |

---

### `POST /resume/{resume_id}/edit/education`

Replace the entire education list for a resume.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `EditEducationRequest`**

```json
{
  "education": [
    { "title": "B.Sc. Computer Science, UBC", "start": "2019", "end": "2023" },
    { "title": "Coursera Machine Learning Specialization", "start": "2023", "end": null }
  ]
}
```

Each `EducationEntry` has:
- `title` (string, required)
- `start` (string, optional) — free-form date label, e.g. `"Sep 2019"`
- `end` (string, optional) — e.g. `"Apr 2023"` or `"Present"`

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Education list replaced successfully |
| `404` | `{ "detail": "..." }` | No resume with that ID exists |
| `500` | `{ "detail": "..." }` | Edit failed; changes were rolled back |

---

### `POST /resume/{resume_id}/edit/awards`

Replace the entire awards list for a resume.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `EditAwardsRequest`**

```json
{
  "awards": [
    { "title": "Dean's List", "start": "2022", "end": null },
    { "title": "Hackathon 1st Place", "start": "2023", "end": "2023" }
  ]
}
```

Each `AwardEntry` has the same shape as `EducationEntry`: `title`, `start`, `end`.

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Awards list replaced successfully |
| `404` | `{ "detail": "..." }` | No resume with that ID exists |
| `500` | `{ "detail": "..." }` | Edit failed; changes were rolled back |

---

### `POST /resume/{resume_id}/edit/bullet_point`

Edit or append a bullet point within a specific resume item.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `EditBulletPointRequest`**

```json
{
  "resume_id": 1,
  "item_index": 0,
  "new_content": "Reduced API response time by 30% through query optimization.",
  "append": false,
  "bullet_point_index": 2
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `resume_id` | `integer` | Yes | Must match the path parameter |
| `item_index` | `integer` | Yes | Zero-based index of the resume item to edit |
| `new_content` | `string` | Yes | Replacement or new bullet point text |
| `append` | `boolean` | Yes | If `true`, appends as a new bullet; if `false`, overwrites |
| `bullet_point_index` | `integer` | When `append=false` | Zero-based index of the bullet to overwrite |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Bullet point updated successfully |
| `400` | `{ "detail": "..." }` | `item_index` out of bounds, or `bullet_point_index` missing/out of bounds |
| `404 RESUME_NOT_FOUND` | Error object | No resume with that ID exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Edit failed; changes were rolled back |

---

### `POST /resume/{resume_id}/edit/bullet_point/delete`

Delete a bullet point from a specific resume item.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `DeleteBulletPointRequest`**

```json
{
  "item_index": 0,
  "bullet_point_index": 2
}
```

| Field | Type | Description |
|---|---|---|
| `item_index` | `integer` | Zero-based index of the resume item |
| `bullet_point_index` | `integer` | Zero-based index of the bullet point to delete |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Bullet point deleted successfully |
| `400` | `{ "detail": "..." }` | Either index is out of bounds |
| `404 RESUME_NOT_FOUND` | Error object | No resume with that ID exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Delete failed; changes were rolled back |

---

### `POST /resume/{resume_id}/edit/resume_item`

Update the title and date range of a specific resume item.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `EditResumeItemMetadataRequest`**

```json
{
  "resume_id": 1,
  "item_index": 0,
  "start_date": "2023-06-01",
  "end_date": "2023-12-31",
  "title": "Updated Project Title"
}
```

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Must match the path parameter |
| `item_index` | `integer` | Zero-based index of the resume item to edit |
| `start_date` | `date` (`YYYY-MM-DD`) | New start date |
| `end_date` | `date` (`YYYY-MM-DD`) | New end date |
| `title` | `string` | New display title |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Item updated successfully |
| `400` | `{ "detail": "..." }` | `item_index` is out of bounds |
| `404 RESUME_NOT_FOUND` | Error object | No resume with that ID exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Edit failed; changes were rolled back |

---

### `POST /resume/{resume_id}/edit/frameworks`

Replace the frameworks list for a specific resume item.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Request Body — `EditFrameworksRequest`**

```json
{
  "item_index": 0,
  "frameworks": ["React", "FastAPI", "PostgreSQL"]
}
```

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ResumeResponse` | Frameworks updated successfully |
| `400` | `{ "detail": "..." }` | `item_index` is out of bounds |
| `404 RESUME_NOT_FOUND` | Error object | No resume with that ID exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Edit failed; changes were rolled back |

---

### `GET /resume/{resume_id}/export/pdf`

Export a resume as a PDF. Requires `pdflatex` to be installed on the server.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `application/pdf` binary | Success — file download with `Content-Disposition` header |
| `404` | `{ "detail": "..." }` | No resume with that ID exists |
| `500` | `{ "detail": "..." }` | PDF rendering failed (e.g. `pdflatex` not installed) |

---

### `GET /resume/{resume_id}/export/docx`

Export a resume as a Word (`.docx`) document.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` binary | Success |
| `404` | `{ "detail": "..." }` | No resume with that ID exists |
| `500` | `{ "detail": "..." }` | Word export failed |

---

### `DELETE /resume/{resume_id}`

Delete a resume and all its associated items.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `resume_id` | `integer` | Database primary key of the resume |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `{ "message": "Resume deleted." }` | Deleted successfully |
| `404 RESUME_NOT_FOUND` | Error object | No resume with that ID exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Deletion failed; changes were rolled back |

---

## Portfolio

All endpoints are prefixed with `/portfolio`.

A portfolio is composed of three parts:
- **Part A** — Narrative sections with editable content blocks (biography, skills summary, etc.)
- **Part B** — Project cards flagged as showcase (`is_showcase = true`)
- **Part C** — All project cards with full metadata (the gallery)

---

### `GET /portfolio`

List all portfolios. Returns a lightweight summary for each — no sections or blocks
are included.

**Request** — No parameters.

**Response**

```json
{
  "portfolios": [
    {
      "id": 1,
      "title": "My Portfolio",
      "creation_time": "2024-01-15T10:00:00Z",
      "last_updated_at": "2024-01-15T11:00:00Z"
    }
  ]
}
```

---

### `GET /portfolio/{portfolio_id}`

Retrieve the full portfolio including all three parts.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |

**Response** — The full portfolio domain object (sections, blocks, and cards).

---

### `DELETE /portfolio/{portfolio_id}`

Permanently delete a portfolio and all its sections, blocks, and project cards.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |

**Responses**

| Status | Body | When |
|---|---|---|
| `204 No Content` | _(empty)_ | Deleted successfully |
| `404` | `{ "detail": "..." }` | No portfolio with that ID exists |

---

### `POST /portfolio/generate`

Generate a brand-new portfolio from a list of project names. Populates all three
parts: narrative sections (Part A), showcase project cards (Part B), and the full
gallery (Part C). The result is persisted and returned.

**Request Body — `PortfolioRequest`**

```json
{
  "project_names": ["proj-a", "proj-b", "proj-c"],
  "portfolio_title": "Jane's Developer Portfolio"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `project_names` | `string[]` | Yes | Projects to include |
| `portfolio_title` | `string` | No | Display title for the portfolio |

**Response** — The generated portfolio object.

---

### `POST /portfolio/{portfolio_id}/refresh`

Regenerate all auto-populated content (Part A narrative sections and Part C card
data) using the latest project statistics. User overrides and `is_showcase` flags
are preserved.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |

**Response** — The updated portfolio object.

---

### `POST /portfolio/{portfolio_id}/sections/{section_id}/block/{block_tag}/edit`

Apply a partial update to a specific content block within a portfolio section.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |
| `section_id` | `string` | Tag identifier of the section |
| `block_tag` | `string` | Tag identifier of the block to edit |

**Request Body**

Arbitrary key/value pairs. The accepted keys depend on the block's content type.

```json
{
  "content": "Updated biography text.",
  "visible": true
}
```

**Response** — The updated block object.

---

### `GET /portfolio/{portfolio_id}/conflicts`

Return all blocks that are currently in a conflict state. A block is in conflict
when the system has generated new content that differs from a version the user
previously saved, and the user has not yet resolved the discrepancy.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |

**Response** — A list of conflicting block objects.

---

### `POST /portfolio/{portfolio_id}/edit`

Update portfolio-level metadata (title and/or project selection). This does **not**
regenerate content — use `/refresh` to regenerate.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |

**Request Body — `EditPortfolioRequest`** (all fields optional)

```json
{
  "title": "Updated Portfolio Title",
  "project_ids_include": ["proj-a", "proj-c"]
}
```

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | Updated portfolio object | Success |
| `404` | `{ "detail": "..." }` | Portfolio not found |
| `422` | `{ "detail": "..." }` | Invalid value (e.g. unknown project name) |

---

### `GET /portfolio/{portfolio_id}/cards`

Return all project cards for a portfolio (Part C gallery). Showcase cards
(`is_showcase = true`) are listed first. Supports optional comma-separated
filter parameters.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |

**Query Parameters** (all optional, comma-separated values)

| Field | Example | Description |
|---|---|---|
| `themes` | `web,ml` | Filter to cards matching any of these themes |
| `tones` | `professional` | Filter by tone |
| `tags` | `python,api` | Filter by tags |
| `skills` | `React` | Filter by skills |

**Response**

```json
{
  "portfolio_id": 1,
  "cards": [ /* project card objects */ ],
  "count": 5
}
```

---

### `PATCH /portfolio/{portfolio_id}/cards/{project_name}`

Edit user-override fields on a project card. Only provided (non-null) fields are
updated.

> **Note:** Directly updating `skills`, `themes`, and `tones` via this endpoint
> will be overwritten the next time the portfolio is refreshed. Use these fields
> for temporary manual adjustments only.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |
| `project_name` | `string` | Project name identifying the card |

**Request Body — `EditCardRequest`** (all fields optional)

```json
{
  "title_override": "Custom Card Title",
  "summary_override": "A custom summary for this project.",
  "tags_override": ["api", "python"],
  "skills": ["FastAPI", "SQLModel"],
  "themes": ["backend", "data"],
  "tones": "professional",
  "frameworks": ["FastAPI", "PostgreSQL"]
}
```

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | Updated card object | Success |
| `404` | `{ "detail": "..." }` | Card not found |

---

### `POST /portfolio/{portfolio_id}/cards/{project_name}/showcase`

Set or clear the showcase flag on a project card. Showcase cards are highlighted
and float to the top of the gallery. This flag is preserved across portfolio
refreshes.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |
| `project_name` | `string` | Project name identifying the card |

**Request Body — `ShowcaseToggleRequest`**

```json
{
  "is_showcase": true
}
```

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | Updated card object | Success |
| `404` | `{ "detail": "..." }` | Card not found |

---

### `GET /portfolio/{portfolio_id}/export`

Export a portfolio as a static website and optionally deploy it to GitHub Pages.

- **If a GitHub access token is stored:** The static site is deployed to the user's
  `portfolio` GitHub Pages repository and the live URL is returned.
- **If no GitHub token:** A `.zip` archive of the static site is returned as a
  file download.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `portfolio_id` | `integer` | Database primary key of the portfolio |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `{ "pages_url": "https://..." }` | GitHub token present — deployed to Pages |
| `200` | `application/zip` binary | No GitHub token — ZIP file download |
| `404 ID_NOT_FOUND` | Error object | Portfolio not found |
| `404 USER_CONFIG_NOT_FOUND` | Error object | No user configuration created yet |

---

## Skills

All endpoints are prefixed with `/skills`.

---

### `GET /skills`

Aggregate and return all skills detected across every project report. Skills are
weighted by their relative contribution across projects.

**Request** — No parameters.

**Response**

```json
{
  "skills": [
    { "name": "Python", "weight": 0.85 },
    { "name": "React", "weight": 0.62 },
    { "name": "Docker", "weight": 0.41 }
  ]
}
```

Each entry is a `WeightedUserSkills` object with `name` (string) and `weight` (float).

---

## User Config

All endpoints are prefixed with `/user-config`.

User configuration stores the user's identity (name, email, GitHub username),
consent flags, and resume defaults (education, awards, skills).

---

### `GET /user-config`

Retrieve the current (most recent) user configuration record.

**Request** — No parameters.

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `UserConfigResponse` | Success |
| `404 USER_CONFIG_NOT_FOUND` | Error object | No configuration created yet |

**`UserConfigResponse`**

```json
{
  "id": 1,
  "consent": true,
  "ml_consent": false,
  "name": "Jane Doe",
  "user_email": "jane@example.com",
  "github": "janedoe",
  "github_connected": true,
  "resume_config": {
    "id": 1,
    "education": ["B.Sc. Computer Science, UBC, 2019-2023"],
    "awards": ["Dean's List 2022"],
    "skills": ["Python", "React"]
  }
}
```

`github_connected` is `true` when a GitHub OAuth access token is stored.

---

### `PUT /user-config`

Create or update the user configuration. If a `resume_config` object is provided,
the nested `ResumeConfigModel` (education, awards, skills) is created or updated.

**Request Body — `UserConfigRequest`**

```json
{
  "consent": true,
  "ml_consent": false,
  "name": "Jane Doe",
  "user_email": "jane@example.com",
  "github": "janedoe",
  "resume_config": {
    "education": ["B.Sc. Computer Science, UBC, 2019-2023"],
    "awards": ["Dean's List 2022"],
    "skills": ["Python", "React"]
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `consent` | `boolean` | Yes | Data usage consent flag |
| `ml_consent` | `boolean` | No (default `false`) | Enables AI-powered features |
| `name` | `string` | No | Full display name |
| `user_email` | `string` | Yes | User's email address |
| `github` | `string` | No | GitHub username |
| `resume_config.education` | `string[]` | No | Education entries (free-form strings) |
| `resume_config.awards` | `string[]` | No | Award entries (free-form strings) |
| `resume_config.skills` | `string[]` | No | Manual skill list |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `UserConfigResponse` | Created or updated successfully |
| `500 DATABASE_OPERATION_FAILED` | Error object | Save failed; changes were rolled back |

---

## Job Readiness

All endpoints are prefixed with `/job-readiness`.

> **ML Consent Required.** All endpoints in this section require `ml_consent = true`
> in the user configuration. Requests without consent return `503 AI_SERVICE_UNAVAILABLE`.

---

### `POST /job-readiness/analyze`

Analyze how well a candidate's profile matches a job description. Builds a
candidate profile from optional resume and project evidence, then calls Azure
OpenAI (GPT-4o mini) to score fit, list ranked strengths and weaknesses, and
generate prioritized improvement suggestions.

**Request Body — `JobReadinessRequest`**

```json
{
  "job_description": "We are looking for a backend engineer...",
  "resume_id": 1,
  "project_names": ["proj-a", "proj-b"],
  "user_profile": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `job_description` | `string` (min 1 non-whitespace char) | Yes | Target role description |
| `resume_id` | `integer` | No | Resume record to include as evidence |
| `project_names` | `string[]` | No | Project names to include as evidence |
| `user_profile` | `JobReadinessUserProfileInput` | No | Manually supplied profile data (see below) |

**`JobReadinessUserProfileInput`** (all fields optional)

```json
{
  "resume_text": "Full text of a resume...",
  "project_summaries": ["Built a REST API..."],
  "tags": ["backend", "api"],
  "extracted_skills": ["Python", "FastAPI"],
  "repository_history_summary": ["Committed daily for 6 months."],
  "repository_file_evidence": [{ "file": "main.py", "summary": "..." }],
  "collaboration_signals": ["Opened 15 pull requests."]
}
```

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `JobReadinessResult` | Analysis completed successfully |
| `400` | `{ "detail": "..." }` | Insufficient evidence to run analysis |
| `404` | `{ "detail": "..." }` | A requested project or resource was not found |
| `503 AI_SERVICE_UNAVAILABLE` | Error object | ML consent not granted, or Azure OpenAI unreachable |

**`JobReadinessResult`**

```json
{
  "fit_score": 78,
  "summary": "You are a strong candidate for this backend role...",
  "strengths": [
    { "item": "Python expertise", "reason": "...", "rank": 1 }
  ],
  "weaknesses": [
    { "item": "Limited cloud deployment experience", "reason": "...", "rank": 1 }
  ],
  "suggestions": [
    {
      "item": "Complete an AWS certification",
      "reason": "...",
      "priority": "high",
      "action_type": "course",
      "resource_name": "AWS Cloud Practitioner",
      "resource_type": "certification",
      "resource_hint": "Available on AWS Training"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `fit_score` | `integer` (0–100) | Overall job fit score |
| `summary` | `string` | Brief narrative summary |
| `strengths` | `RankedFinding[]` | Ranked list of candidate strengths |
| `weaknesses` | `RankedFinding[]` | Ranked list of gaps |
| `suggestions` | `PrioritizedSuggestion[]` | Actionable improvement steps |

---

## Insights

Insight endpoints share the `/projects` prefix (same as the projects router).

> **ML Consent Optional.** Non-ML insights (activity, ownership, skills) are always
> generated. ML-based insights additionally require `ml_consent = true`. When ML
> consent is absent, only non-ML insights are returned and results are not cached.

---

### `GET /projects/{project_name}/insights`

Return a list of resume-writing insight prompts for a project. On the first call
(or when ML consent is not granted), insights are generated from the project's
mined statistics and cached. Subsequent calls with ML consent return the cached
copy. Dismissed insights are always filtered out.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `project_name` | `string` | URL-encoded project name |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `ProjectInsightsResponse` | Success |
| `404 PROJECT_NOT_FOUND` | Error object | Project does not exist |
| `500` | `{ "detail": "..." }` | Insight generation failed unexpectedly |

**`ProjectInsightsResponse`**

```json
{
  "project_name": "my-project",
  "insights": [
    { "message": "You made 142 commits over 6 months — highlight your sustained contribution." },
    { "message": "You were the sole contributor — emphasize your end-to-end ownership." }
  ]
}
```

---

### `POST /projects/{project_name}/insights/dismiss`

Permanently dismiss an insight message for a project. Dismissed messages are
excluded from all future calls to `GET /projects/{project_name}/insights`.

**Path Parameters**

| Field | Type | Description |
|---|---|---|
| `project_name` | `string` | URL-encoded project name |

**Request Body — `DismissInsightRequest`**

```json
{
  "message": "You made 142 commits over 6 months — highlight your sustained contribution."
}
```

The `message` value must exactly match the insight text to suppress.

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `{ "dismissed": true }` | Insight dismissed successfully |
| `404 PROJECT_NOT_FOUND` | Error object | Project does not exist |

---

## Interview

All endpoints are prefixed with `/interview`.

> **ML Consent Required.** All endpoints in this section require `ml_consent = true`
> in the user configuration. Requests without consent return `503 AI_SERVICE_UNAVAILABLE`.

The interview feature is **stateless** — the client is responsible for tracking
conversation state (current question, covered dimensions, etc.) and sending it back
with each request.

---

### `POST /interview/start`

Initialize a mock interview session and generate the first tailored question.
Builds interview context from the job description and optional candidate evidence,
then calls Azure OpenAI to create a relevant opening question.

**Request Body — `InterviewStartRequest`**

```json
{
  "job_description": "We are looking for a backend engineer...",
  "resume_id": 1,
  "project_names": ["proj-a"],
  "user_profile": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `job_description` | `string` (min 1 non-whitespace char) | Yes | Target role description |
| `resume_id` | `integer` | No | Resume to include as context |
| `project_names` | `string[]` | No | Projects to bias question generation toward |
| `user_profile` | `JobReadinessUserProfileInput` | No | Manually supplied profile data |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `InterviewStartResult` | First question generated |
| `400` | `{ "detail": "..." }` | Insufficient evidence to build context |
| `404` | `{ "detail": "..." }` | A requested project or resource was not found |
| `503 AI_SERVICE_UNAVAILABLE` | Error object | ML consent not granted, or Azure OpenAI unreachable |

**`InterviewStartResult`**

```json
{
  "question": "Can you walk me through a project where you had to design a scalable API?",
  "question_category": "project_based",
  "interviewer_focus": "System design and scalability",
  "fit_dimension": "technical_skills",
  "project_name": "proj-a",
  "next_action": "advance_dimension"
}
```

| Field | Type | Description |
|---|---|---|
| `question` | `string` | The generated interview question |
| `question_category` | `"project_based"` \| `"role_specific"` \| `"skill_gap"` | Type of question |
| `interviewer_focus` | `string` | What the interviewer is probing |
| `fit_dimension` | `string` | Job-fit dimension being assessed |
| `project_name` | `string` \| `null` | Project the question is anchored to |
| `next_action` | `"retry_same_question"` \| `"advance_dimension"` \| `"probe_gap"` | Client hint for session flow |

---

### `POST /interview/answer`

Submit an answer to the current interview question. Evaluates the response for
relevance and depth, generates coaching feedback, and returns the next question.

The client must include the full context from the previous `start` or `answer` call.

**Request Body — `InterviewAnswerRequest`**

```json
{
  "job_description": "We are looking for a backend engineer...",
  "resume_id": 1,
  "project_names": ["proj-a"],
  "user_profile": null,
  "current_question": "Can you walk me through a project where you designed a scalable API?",
  "user_answer": "In my proj-a project, I built a REST API using FastAPI...",
  "current_project_name": "proj-a",
  "current_fit_dimension": "technical_skills",
  "covered_dimensions": [],
  "retry_same_question": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `job_description` | `string` | Yes | Same as `start` |
| `resume_id` | `integer` | No | Same as `start` |
| `project_names` | `string[]` | No | Same as `start` |
| `user_profile` | `JobReadinessUserProfileInput` | No | Same as `start` |
| `current_question` | `string` (min 1 non-whitespace char) | Yes | The question being answered |
| `user_answer` | `string` (min 1 non-whitespace char) | Yes | The user's free-text response |
| `current_project_name` | `string` | No | Project the current question is anchored to |
| `current_fit_dimension` | `string` | No | Dimension being assessed for this question |
| `covered_dimensions` | `string[]` | No | History of dimensions already covered |
| `retry_same_question` | `boolean` | No (default `false`) | Set `true` when retrying after feedback |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `InterviewAnswerResult` | Answer evaluated and next question generated |
| `400` | `{ "detail": "..." }` | Insufficient evidence |
| `404` | `{ "detail": "..." }` | A requested resource was not found |
| `503 AI_SERVICE_UNAVAILABLE` | Error object | ML consent not granted, or Azure OpenAI unreachable |

**`InterviewAnswerResult`**

```json
{
  "answer_acceptable": true,
  "feedback": {
    "strengths": "You clearly explained the architecture and your specific contributions.",
    "improvements": "Consider quantifying the performance improvement you achieved.",
    "example_answer": "In my proj-a project, I designed a REST API using FastAPI that reduced response time by 35%..."
  },
  "next_question": "How did you handle authentication in that API?",
  "next_question_category": "role_specific",
  "fit_dimension": "technical_skills",
  "project_name": "proj-a",
  "next_action": "advance_dimension"
}
```

| Field | Type | Description |
|---|---|---|
| `answer_acceptable` | `boolean` | Whether the answer sufficiently addressed the question |
| `feedback.strengths` | `string` | What the answer did well |
| `feedback.improvements` | `string` | What could be improved |
| `feedback.example_answer` | `string` | A model response for reference |
| `next_question` | `string` | The next interview question |
| `next_question_category` | `string` | Category of the next question |
| `fit_dimension` | `string` | Dimension the next question addresses |
| `project_name` | `string` \| `null` | Project anchor for the next question |
| `next_action` | `string` | Client hint: `retry_same_question`, `advance_dimension`, or `probe_gap` |

---

## GitHub OAuth

All endpoints are prefixed with `/github`.

The OAuth flow follows a polling pattern optimized for the Electron app:

1. Frontend calls `GET /github/login` to get a state token and authorization URL.
2. Frontend opens the URL in the OS browser.
3. Frontend polls `GET /github/oauth-status?state=...` every ~2 seconds.
4. GitHub redirects the browser to `GET /github/callback` after the user acts.
5. The callback stores the access token and updates the state to `"success"` or `"denied"`.
6. The next poll detects the status change and the frontend updates its UI.

---

### `GET /github/login`

Generate an OAuth state token and the GitHub authorization URL. The frontend
opens the URL in the OS browser to begin the authorization flow.

**Requires** `GITHUB_CLIENT_ID` and `GITHUB_REDIRECT_URI` to be set in the
server environment (`.env`).

**Request** — No parameters.

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | OAuth initiation object | Success |
| `500` | `{ "detail": "..." }` | Missing environment variables |

**Response body**

```json
{
  "state": "abc123...",
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...&state=abc123...",
  "callback_scheme": "capstone"
}
```

The `state` value must be passed to all subsequent OAuth calls.

---

### `GET /github/oauth-status`

Poll the server to check whether an OAuth flow has completed. Call this every
~2 seconds after opening the authorization URL. The state expires after 600 seconds.

**Query Parameters**

| Field | Type | Required | Description |
|---|---|---|---|
| `state` | `string` | Yes | OAuth state returned by `GET /github/login` |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | Status object | State is known and not expired |
| `404 BAD_OAUTH_STATE` | Error object | Unknown state value |
| `410 EXPIRED_OAUTH_STATE` | Error object | State older than 600 seconds |

**Response body**

```json
{
  "state": "abc123...",
  "status": "pending",
  "detail": null
}
```

| `status` | Meaning |
|---|---|
| `"pending"` | User has not yet acted in the browser |
| `"success"` | Access token obtained and stored |
| `"denied"` | User declined to grant access |
| `"error"` | An unexpected error occurred |

---

### `GET /github/callback`

Called by GitHub after the user grants or denies access. This endpoint is opened
by the browser (not the frontend app), so it returns an HTML page rather than JSON.
The token exchange and database update happen here, and the OAuth state is updated
so the polling endpoint reflects the outcome.

**Query Parameters**

| Field | Type | Required | Description |
|---|---|---|---|
| `state` | `string` | Yes | OAuth state from the original login request |
| `code` | `string` | No | Authorization code from GitHub (present on success) |
| `error` | `string` | No | Error string from GitHub (present when access is denied) |

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `HTMLResponse` | Browser popup page (success, denied, or error heading) |
| `404 BAD_OAUTH_STATE` | Error object (JSON) | Unknown state value |
| `410 EXPIRED_OAUTH_STATE` | Error object (JSON) | State has expired |

The HTML response prompts the user to close the browser tab and return to the app.

---

### `PUT /github/revoke_access_token`

Clear the stored GitHub access token from the user configuration. After calling
this endpoint, the frontend should also redirect the user to
`https://github.com/settings/applications` to revoke the OAuth app on GitHub's side.

**Request** — No parameters.

**Responses**

| Status | Body | When |
|---|---|---|
| `200` | `{ "message": "Access token revoked" }` | Token cleared successfully |
| `404 USER_CONFIG_NOT_FOUND` | Error object | No user configuration exists |
| `500 DATABASE_OPERATION_FAILED` | Error object | Token was not successfully cleared |
