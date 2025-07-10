# 🧩 SBKube

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sbkube)]()
[![Repo](https://img.shields.io/badge/GitHub-kube--app--manaer-blue?logo=github)](https://github.com/ScriptonBasestar/kube-app-manaer)

**SBKube**는 `YAML`, `Helm`, `Git` 리소스를 로컬에서 정의하고 `k3s` 등 Kubernetes 환경에 일관되게 배포할 수 있는 CLI 도구입니다.

> k3s용 헬름+yaml+git 배포 자동화 CLI 도구

---

## 🚀 빠른 시작

```bash
# 설치
pip install sbkube

# 기본 워크플로우
sbkube prepare --base-dir . --app-dir config
sbkube build --base-dir . --app-dir config  
sbkube template --base-dir . --app-dir config --output-dir rendered/
sbkube deploy --base-dir . --app-dir config --namespace <namespace>
```

## 📚 문서

전체 문서는 **[docs/INDEX.md](docs/INDEX.md)**에서 확인하세요.

- 📖 [시작하기](docs/01-getting-started/) - 설치 및 빠른 시작
- ⚙️ [기능 가이드](docs/02-features/) - 명령어 및 기능 설명  
- 🔧 [설정 가이드](docs/03-configuration/) - 설정 파일 작성법
- 👨‍💻 [개발자 가이드](docs/04-development/) - 개발 환경 구성
- 📖 [사용 예제](docs/06-examples/) - 다양한 배포 시나리오

## 🔮 활용 목적

`SBKube`는 [ScriptonBasestar](https://github.com/ScriptonBasestar)가 운영하는 **웹호스팅 / 서버호스팅 기반 DevOps 인프라**에서 실무적으로 활용되며, 다음과 같은 용도로 발전될 예정입니다:

- 내부 SaaS 플랫폼의 Helm 기반 배포 자동화
- 사용자 정의 YAML 템플릿과 Git 소스 통합 배포
- 오픈소스 DevOps 도구 및 라이브러리의 테스트 베드
- 향후 여러 배포 도구(`sbkube`, `sbproxy`, `sbrelease` 등)의 공통 기반

## ⚙️ 주요 기능

### 다단계 워크플로우
```
prepare → build → template → deploy
```

### 지원 애플리케이션 타입
- **pull-helm** / **pull-helm-oci** / **pull-git** - 소스 준비
- **copy-app** - 로컬 파일 복사  
- **install-helm** / **install-yaml** / **install-action** - 배포 방법

### 설정 기반 관리
- **config.yaml** - 애플리케이션 정의 및 배포 스펙
- **sources.yaml** - 외부 소스 정의 (Helm repos, Git repos)
- **values/** - Helm 값 파일 디렉토리

## 💬 지원

- 📋 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)
- 📧 문의: archmagece@users.noreply.github.com

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

*🇰🇷 한국 k3s 환경에 특화된 Kubernetes 배포 자동화 도구*