# Contributing

Thanks for taking the time to contribute.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e '.[dev]'
```

## Run Tests

```bash
pytest -q
```

## Lint

```bash
ruff check .
```
