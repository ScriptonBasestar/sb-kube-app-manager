# 📋 BACKLOG 항목들

이 문서는 향후 구현이 필요하지만 현재는 보류 중인 기능 및 개선사항들을 관리합니다.

---

## 🚨 template 명령어의 지원 타입 범위 불일치

- 📌 관련 기능: template 명령어 - 지원 타입
- 📁 관련 파일/모듈: `FEATURES.md` vs 실제 구현
- 📎 문제 요약: FEATURES.md에는 template 명령어가 `install-helm`과 `install-yaml` 타입만 지원한다고 명시되어 있으나, 실제 template.py 구현을 보면 빌드된 Helm 차트를 처리하므로 `pull-helm`, `pull-helm-oci` 등도 지원할 수 있음
- 🛠️ 보류 사유: 구현 검토 후 FEATURES.md 또는 구현 조정 필요. template 명령어의 정확한 지원 범위를 정의하고 일관성 있게 구현해야 함

---

## 📊 BACKLOG 요약

총 1개 구현 검토 필요 사항:
- template 명령어: 지원 타입 범위 확인 및 문서/구현 일치화 필요