PRAGMA foreign_keys = ON; -- Turn on FK constraints

CREATE TABLE IF NOT EXISTS user_config (
    id INT PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    github TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE IF NOT EXISTS project_report (
    project_name TEXT PRIMARY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    FOREIGN KEY (user_config_used) REFERENCES user_config(id), -- Idea being that a warning is shown if a user config has since been updated
    statistic JSON NOT NULL,
)

CREATE TABLE IF NOT EXISTS file_report (
    id int PRIMARY KEY AUTOINCREMENT,
    FOREIGN KEY (project_name) REFERENCES project_reports(project_name) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT, -- This is realitive to the top level folder of the project
    is_info_file BOOLEAN,
    file_hash BLOB,
    statistic JSON NOT NULL
)

CREATE TABLE IF NOT EXISTS resume_item (
    id INT PRIMARY KEY AUTOINCREMENT,
    FOREIGN KEY (project_name) REFERENCES project_reports(project_name) ON DELETE SET NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    content JSON NOT NULL,
)

CREATE TABLE IF NOT EXISTS resume (
    id INT PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    email TEXT, -- We store
    report JSON NOT NULL
);
