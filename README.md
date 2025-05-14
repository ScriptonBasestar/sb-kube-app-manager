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


## TEST

pytest tests/test_prepare.py -v
