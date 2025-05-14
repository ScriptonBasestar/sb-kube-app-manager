# sbkube

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)]()
[![Repo](https://img.shields.io/badge/GitHub-kube--app--manaer-blue?logo=github)](https://github.com/ScriptonBasestar/kube-app-manaer)

`sbkube`는 로컬 YAML, Helm, Git 리소스를 기반으로 k3s 클러스터에 손쉽게 배포 가능한 CLI 도구입니다.


K3s 환경에서 Helm/YAML 앱을 통합적으로 배포 관리합니다.


```
uv venv
source .venv/bin/activate
uv pip install -e .

sbkube prepare
sbkube build
sbkube template
sbkube deploy
```


## CMD

sbkube prepare --apps config.yaml --sources sources.yaml
sbkube build --apps config.yaml

python -m sbkube.cli

### prepare
python -m sbkube.cli prepare --apps samples/k3scode/config-browserless.yaml --sources samples/k3scode/sources.yaml
python -m sbkube.cli prepare --apps samples/k3scode/config-browserless --sources samples/k3scode/sources
python -m sbkube.cli prepare --apps samples/k3scode/config-memory --sources samples/k3scode/sources
sbkube prepare --apps samples/k3scode/config --sources samples/k3scode/sources

### build
python -m sbkube.cli build --apps samples/k3scode/config-memory
sbkube build --apps samples/k3scode/config-memory

### template
python -m sbkube.cli template --apps samples/k3scode/config-memory
sbkube template --apps samples/k3scode/config-memory

## TEST

### prepare
pytest tests/test_prepare.py -v

### build
pytest tests/test_build.py -v

overrides/가 적용된 파일이 정상 복사되었는지 검사
removes:로 지정한 파일이 실제 삭제되었는지 확인
pull-git, copy-app 항목에 대한 테스트 분리