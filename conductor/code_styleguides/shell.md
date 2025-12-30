# Shell Scripting Style Guide

## Naming Conventions
-   **Variables**: Upper case for exported variables/constants (e.g., `export API_KEY`), lower case for local variables (e.g., `local file_path`).
-   **Functions**: Lower case with underscores (e.g., `process_file()`).

## Formatting
-   **Indentation**: Use 2 or 4 spaces. Do not use tabs.
-   **Line Length**: Keep lines under 80 characters where possible.
-   **Shebang**: Always include a shebang (e.g., `#!/bin/bash`).

## Best Practices
-   **Quoting**: Quote variables to prevent word splitting (e.g., `"$my_var"`).
-   **Error Handling**: Use `set -e` (exit on error) and `set -u` (nounset) for robustness.
-   **Comments**: Comment complex logic.
-   **Portability**: Prefer POSIX-compliant syntax when possible.
