# 수동테스트

## Prepare kind kube

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind


kind create cluster --name sbkube-test
# kind-sbkube-test 이게 생성됨
kubectl config get-contexts
kubectl config current-context
kubectl config use-context kind-sbkube-test

# kind create cluster --name sbkube-test --kubeconfig ~/.kube/test-kubeconfig
```

## CMD

sbkube prepare --apps config.yaml --sources sources.yaml
sbkube build --apps config.yaml

python -m sbkube.cli

### prepare
```bash
uv run -m sbkube.cli prepare --base-dir samples/k3scode --app-dir memory
uv run -m sbkube.cli prepare --base-dir samples/k3scode --app-dir rdb

python -m sbkube.cli prepare \
  --base-dir ./samples/k3scode \
  --apps config-memory.yml

sbkube prepare --base-dir . --app-dir memory
sbkube prepare --app-dir memory
```

### build
```bash
uv run -m sbkube.cli build --base-dir samples/k3scode --app-dir memory
uv run -m sbkube.cli build --base-dir samples/k3scode --app-dir rdb
```

### template
```bash
uv run -m sbkube.cli template --base-dir samples/k3scode --app-dir memory --output-dir rendered/
uv run -m sbkube.cli template --base-dir samples/k3scode --app-dir rdb --output-dir rendered/
```

### deploy
```bash
uv run -m sbkube.cli deploy --base-dir samples/k3scode --app-dir memory --namespace data-memory
uv run -m sbkube.cli deploy --base-dir samples/k3scode --app-dir rdb --namespace data-rdb
```

### upgrade
TODO

### delete
TODO

### validate

#### sources.yaml 검증
sbkube validate sources.yaml

#### config.yaml 검증
sbkube validate a000_infra/config.yaml

#### 스키마 명시
sbkube validate somefile.yaml --schema schemas/custom.schema.json

## Unit TEST

### prepare
pytest tests/test_prepare.py -v

### build
pytest tests/test_build.py -v

overrides/가 적용된 파일이 정상 복사되었는지 검사
removes:로 지정한 파일이 실제 삭제되었는지 확인
pull-git, copy-app 항목에 대한 테스트 분리o

### template
pytest tests/test_template.py -v

### deploy

pytest tests/test_deploy.py -v

----------
--namespace, --include-crds, --kube-version 등 Helm 추가 인자 지원

--stdout 옵션으로 제어

--dry-run, --debug 연동


--dry-run, --wait, --timeout 지원

Helm 로그와 stdout을 파일로 저장 옵션

kubectl apply -f 방식도 선택 가능하게 (--method=kubectl|helm)


test_deploy.py 혹은 sbkube init
