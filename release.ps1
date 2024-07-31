#!/bin/sh
#Requires -Version 7

# This is a polyglot script that runs in both a POSIX compliant shell and PowerShell 7+.
# It assumes the following prerequisites have been met:
# 0. A compatible Python virtual environment is activated
# 1. uv is installed via the standalone installer
# 2. security-constraints is installed via `uv tool install`
# 3. The environment variable SC_GITHUB_TOKEN is set to a valid GitHub token
# 4. Both Node.js and the Pyright npm package are installed
# 5. All of the above executables can be found in PATH
# 6. The current working directory is set to the project root
# The shell commands are separated into blocks by the stages in the software testing life cycle:
# 1. development (dependency management, code generation, linting)
# 2. system integration testing
# 3. user acceptance testing
# 4. production

uv self update &&
uv tool update security-constraints &&
npm update pyright &&
security-constraints --min-severity moderate --output ./constraints.txt &&
uv pip compile --constraints ./constraints.txt --output-file ./requirements.txt ./pyproject.toml &&
uv pip sync ./requirements.txt &&
uv pip install --constraints ./constraints.txt --constraints ./requirements.txt --group all --editable . &&

python -m openapi_spec_validator --errors all ./resources/openapi/openapi.yaml &&
python -m datamodel_code_generator &&

python -m ruff check &&
python -m pylint ./src/ ./tests/ &&
npm exec pyright &&

python -m pytest &&

python -m mprof run --include-children ./src/stackexchange/backup.py --account-id 8 &&
python -m mprof peak &&
python -m mprof clean &&

python -m bumpver update --patch --no-fetch &&

$(exit)
