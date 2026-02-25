---
type: Module Overview
audience: Developer
topics: [module, structure, organization]
llm_priority: medium
last_updated: 2026-02-25
---

# SBKube 모듈 개요

> 상세 아키텍처는 [ARCHITECTURE.md](ARCHITECTURE.md)를 참조하세요.

## 기본 정보

- **이름**: sbkube
- **버전**: v0.11.0
- **타입**: Python CLI Application (Monolithic)
- **역할**: Kubernetes 배포 자동화 CLI 도구 (k3s 최적화)
- **런타임**: Python 3.14+

## 모듈 경계 (Boundaries)

### In Scope

- ✅ CLI 명령어: prepare, build, template, deploy, apply, status, history, rollback 등 16개
- ✅ 설정 검증: Pydantic 기반 unified/legacy 설정 파싱
- ✅ 외부 소스 다운로드: Helm, Git, OCI, HTTP
- ✅ 배포 상태 관리: SQLAlchemy + SQLite
- ✅ 사용자 인터페이스: Rich Console, multi-format output

### Out of Scope

- ❌ Kubernetes 클러스터 프로비저닝
- ❌ 컨테이너 이미지 빌드
- ❌ CI/CD 파이프라인 오케스트레이션
- ❌ 모니터링/로깅 수집

## 확장 포인트

### 새 명령어 추가

1. `sbkube/commands/` 디렉토리에 모듈 생성
2. `EnhancedBaseCommand` 상속 클래스 작성
3. `cli.py`에 Click 명령어 등록 + `SbkubeGroup.COMMAND_CATEGORIES`에 추가

### 새 앱 타입 추가

1. `models/config_model.py`에 타입 정의
2. 각 명령어에서 타입별 로직 추가
3. `docs/02-features/application-types.md` 문서화

### 새 검증 로직 추가

1. `validators/` 디렉토리에 검증 클래스 작성
2. `validation_system.py`에 등록

## 관련 문서

- **아키텍처**: [ARCHITECTURE.md](ARCHITECTURE.md) — 상세 레이어, 패턴, 예외 계층
- **의존성**: [DEPENDENCIES.md](DEPENDENCIES.md) — Python 패키지 및 시스템 도구
- **API 계약**: [API_CONTRACT.md](API_CONTRACT.md) — 인터페이스 명세
- ****아키텍처**: [ARCHITECTURE.md](../../../ARCHITECTURE.md) — 시스템 아키텍처

---

**문서 버전**: 2.0
**마지막 업데이트**: 2026-02-25
