# Deploy

## Pypi Deploy
```bash
uv build
# uv publish
uv run -m twine upload dist/*
```

## Local Deploy
```
uv build
uv pip install -e .
```
