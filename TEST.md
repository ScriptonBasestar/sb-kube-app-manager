# 수동테스트

## Prepare kind kube

```
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind


kind create cluster --name sbkube-test
kubectl config get-contexts

kind create cluster --name sbkube-test --kubeconfig ~/.kube/test-kubeconfig
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

python -m sbkube.cli prepare \
  --base-dir ./samples/k3scode \
  --apps config-memory.yml

### build
python -m sbkube.cli build --apps samples/k3scode/config-memory
sbkube build --apps samples/k3scode/config-memory

python -m sbkube.cli build \
  --base-dir ./samples/k3scode \
  --apps config-memory.yml

### template
python -m sbkube.cli template --apps samples/k3scode/config-memory --output-dir rendered/

base-dir지정안해서 오류나는거확인
python -m sbkube.cli template --apps samples/k3scode/config-memory --output-dir rendered/

sbkube template \
  --apps samples/k3scode/config-memory \
  --base-dir ./samples/k3scode \
  --output-dir rendered

python -m sbkube.cli template \
  --apps config-memory \
  --base-dir ./samples/k3scode

### deploy
python -m sbkube.cli deploy --apps samples/k3scode/config-memory --namespace devops
sbkube deploy --apps samples/k3scode/config-memory --namespace devops

python -m sbkube.cli deploy \
  --apps config-memory \
  --base-dir ./samples/k3scode

### upgrade

python -m sbkube.cli upgrade \
  --apps config-memory \
  --base-dir ./samples/k3scode

### delete

python -m sbkube.cli delete \
  --apps config-memory \
  --base-dir ./samples/k3scode

### validate

python -m sbkube.cli validate \
  samples/k3scode/sources.yml

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