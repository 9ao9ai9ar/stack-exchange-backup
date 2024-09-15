#!/usr/bin/env sh

# export SC_GITHUB_TOKEN=...
uv self update &&
security-constraints --min-severity moderate --output ./requirements/constraints.txt &&
uv pip compile \
    --constraint ./requirements/constraints.txt \
    --output-file ./requirements/prod.txt \
    ./pyproject.toml &&
uv pip compile \
    --extra dev \
    --constraint ./requirements/prod.txt \
    --constraint ./requirements/constraints.txt \
    --output-file ./requirements/dev.txt \
    ./pyproject.toml &&
uv pip sync ./requirements/dev.txt &&
uv pip install --editable . &&
python -m openapi_spec_validator --errors all ./resources/openapi/openapi.yaml &&
python -m datamodel_code_generator &&
python -m ruff check &&
python -m pylint ./src/ ./tests/ &&
npm update pyright &&
pyright &&
python -m pytest -vvr A --no-summary ./tests/ &&
python -m bumpver update --patch --no-fetch &&
:
