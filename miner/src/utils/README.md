# Utils Folder

## Purpose

The `utils/` folder contains **small, stateless helper functions for generic data processing**. These functions are intentionally simple, reusable, and **not tied to any specific domain or feature**.

If a function is closely coupled to core logic (such as machine learning, analysis, resume parsing, or statistics), it **does not belong in `utils/`** and should live in the appropriate `core/`, `interface`, or `services/` submodule instead.
