# Deploy

## Pypi Deploy
```bash
rm -rf dist
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
pip install -e .
uv pip install --force-reinstall --no-deps --upgrade .

```