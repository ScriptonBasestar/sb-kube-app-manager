# kube-app-manager

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
