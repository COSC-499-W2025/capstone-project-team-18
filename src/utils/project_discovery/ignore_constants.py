# When we are analyzing a folder to see if it is a project, if
# we see any of these files or directorys, we instantly know it
# is a project folder

INSTANT_SUCCESS_FILES_AND_DIR = [
    # Files that instantly qualify a directory as a project
    "README.md",
    "README.txt",
    "package.json",
    ".gitignore",
    "requirements.txt",
    ".env",
    "yarn.lock",
    "package-lock.json",
    "yarn.lock",
    "vite.config.js",
    "vite.config.ts",

    # Directories that instantly qualify a directory as a project
    ".git",
    "src",
    "app",
    ".github",
    ".vscode",
    ".venv",
    "venv"
]

# Junk that should totally be disregarded. They should be neither
# used in project discovery nor be analyzed.

JUNK_FILES = [
    ".DS_Store",
    "thumbs.db",
]

# Ignore extensions, files, or directorys that might be really useful
# in determining what is a project, but should not be analyzed
IGNORE_EXTENSIONS = [
    ".jar",
    ".sql",
    ".db",
    ".sqlite",
    ".sqlite3",
]

IGNORE_FILES = JUNK_FILES + [
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "settings.py",
    "urls.py",
]

IGNORE_DIRS = [
    ".devcontainer",
    ".github",
    ".vscode",
    ".git",
    ".pytest_cache",

    # Virtual environment directories
    ".venv",
    "venv",
    "env",
    "virtualenv",
    "site-packages",
    "node_modules",
    "newenv",
    "myenv",

    # Build/distribution directories
    "target",
    "build",
    "dist",
    "__pycache__",
    "migrations",

    # Python library directories
    "lib",
    "lib64",
    "bin",
    "include",
    "share"
]
