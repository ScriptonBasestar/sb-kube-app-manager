# Deploy

## Pypi Deploy
```bash
uv build
# uv publish
uv run -m twine upload dist/*
```

## Venv Deploy
```
uv build
uv pip install -e .
```

## Local System Deploy
```
uv build
which 
pip install -e .
```