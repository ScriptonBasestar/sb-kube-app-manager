# 📋 문서 검토 보고서 (2025-01-24)

## 🎯 검토 범위

- **대상**: `docs/**` 전체 디렉토리
- **현재 버전**: `0.4.5` (pyproject.toml 기준)
- **검토일**: 2025-01-24

---

## ✅ 수정 완료 항목

### 1. **`docs/02-features/commands.md` - delete 명령어 섹션 업데이트**

**문제**: `--dry-run`과 `--skip-not-found` 옵션 누락

**수정 내용**:
- `--dry-run` 옵션 추가 및 사용 예제 작성
- `--skip-not-found` 옵션 문서화
- Helm, YAML, Action 타입별 dry-run 동작 설명 추가
- 주의사항 섹션 추가

**위치**: [docs/02-features/commands.md:236-284](docs/02-features/commands.md#L236-L284)

### 2. **버전 불일치 수정**

#### README.md
- **변경**: `0.4.1` → `0.4.5`
- **위치**: Badge 라인

#### docs/05-deployment/README.md
- **변경**: `SBKUBE_VERSION: "0.1.10"` → `"0.4.5"`
- **위치**: GitLab CI 예제

---

## ⚠️ 발견된 문제 (미수정)

### 1. **문서화되지 않은 명령어들**

다음 명령어들이 `docs/02-features/commands.md`에 문서화되지 않음:

#### 1.1 `sbkube init` - 프로젝트 초기화
```bash
# 기능
- 새 프로젝트 초기화
- 기본 설정 파일 및 디렉토리 구조 생성
- 템플릿 선택 (basic, web-app, microservice)

# 주요 옵션
--template [basic|web-app|microservice]
--name TEXT
--non-interactive
--force
```

#### 1.2 `sbkube doctor` - 시스템 진단
```bash
# 기능
- Kubernetes 클러스터 연결 진단
- Helm 설치 확인
- 설정 파일 유효성 검사
- 문제점 진단 및 해결 방안 제시

# 주요 옵션
--detailed
--fix
--check TEXT
--config-dir TEXT
```

#### 1.3 `sbkube fix` - 자동 수정
```bash
# 기능
- 자동 수정 시스템
- 백업 및 롤백 지원

# 주요 옵션
--dry-run
--force
--rollback INTEGER
--backup-cleanup
--history
--config-dir TEXT
```

#### 1.4 `sbkube assistant` - 대화형 문제 해결
```bash
# 기능
- 대화형 문제 해결 도우미
- 컨텍스트 기반 문제 분석
- 오류 메시지 분석

# 주요 옵션
--context TEXT
--error TEXT
--quick
```

**하위 명령어**: `assistant-history` (지원 세션 히스토리 조회)

#### 1.5 `sbkube profiles` - 프로파일 관리
```bash
# 기능
- 환경별 프로파일 관리
- 프로파일 목록 조회, 내용 표시, 검증

# 하위 명령어
- profiles list
- profiles show
- profiles validate
```

#### 1.6 `sbkube history` - 실행 히스토리
```bash
# 기능
- 최근 실행 기록 조회
- 성공/실패 통계
- 오래된 기록 정리

# 주요 옵션
--limit INTEGER (기본값: 10)
--detailed
--failures
--profile TEXT
--clean
--stats
```

**하위 명령어**: `diagnose` (진단 실행)

### 2. **문서 우선순위 불일치**

#### 2.1 commands.md 순서
현재 문서의 명령어 순서가 사용 빈도/중요도와 맞지 않음:

**현재**:
1. prepare
2. build
3. template
4. deploy
5. upgrade
6. delete
7. apply (★ 가장 많이 사용)
8. validate
9. state

**권장**:
1. **init** (최초 1회)
2. **apply** (가장 많이 사용)
3. prepare, build, template, deploy (apply 상세)
4. upgrade
5. delete
6. validate
7. state
8. profiles
9. history
10. doctor
11. fix
12. assistant

### 3. **예제 디렉토리 참조 불일치**

README.md에서 `docs/06-examples/` 참조하나, 실제로는 `examples/` 디렉토리 존재:

```markdown
# README.md (line 46)
- 📖 [사용 예제](docs/06-examples/) - 다양한 배포 시나리오
```

**실제 구조**:
```
examples/
├── basic/
├── k3scode/
├── deploy/
├── overrides/
└── complete-workflow/
```

### 4. **app-dir 기본값 불일치**

#### docs/02-features/commands.md
```bash
# prepare 섹션 (line 46)
- `--app-dir <디렉토리>` - 앱 설정 디렉토리 (기본값: `config`)
```

#### 실제 코드 (delete.py, apply.py 등)
```python
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default=".",  # 기본값이 "." (현재 디렉토리)
    ...
)
```

**영향 범위**: prepare, build, template, deploy, delete, apply 모든 명령어

---

## 📊 통계

### 문서 파일 수
- **전체**: 36개 마크다운 파일 (docs/**)
- **제품 문서**: 4개 (00-product/)
- **기능 문서**: 5개 (02-features/)
- **설정 문서**: 3개 (03-configuration/)
- **내부 문서**: 9개 (99-internal/)

### 명령어 문서화 현황
- **문서화됨**: 9개 (prepare, build, template, deploy, upgrade, delete, apply, validate, state)
- **미문서화**: 6개 (init, doctor, fix, assistant, profiles, history)
- **문서화율**: 60% (9/15)

---

## 🎯 권장 조치사항

### 우선순위 1 (긴급)
1. ✅ **delete 명령어 `--dry-run` 문서화** (완료)
2. ✅ **버전 정보 통일** (0.4.5로 통일 완료)
3. **app-dir 기본값 문서 수정** (`config` → `.`)

### 우선순위 2 (중요)
4. **미문서화 명령어 추가**
   - init, doctor, fix, assistant 추가 (사용자 경험 개선 도구)
   - profiles, history 추가 (운영 도구)
5. **명령어 순서 재구성** (사용 빈도 기반)
6. **예제 경로 수정** (`docs/06-examples/` → `examples/`)

### 우선순위 3 (개선)
7. **각 명령어의 실제 사용 예제 추가**
8. **명령어 간 관계 다이어그램 추가**
9. **트러블슈팅 섹션 강화**

---

## 📝 개선 제안

### 1. 문서 구조 개선
```
docs/02-features/
├── commands.md (현재)
├── commands-basic.md (신규) - init, apply, delete
├── commands-advanced.md (신규) - prepare~deploy, upgrade
├── commands-troubleshooting.md (신규) - doctor, fix, assistant
└── commands-management.md (신규) - profiles, history, state
```

### 2. Quick Reference 추가
```markdown
## 🚀 빠른 참조

| 상황 | 명령어 |
|------|--------|
| 새 프로젝트 시작 | `sbkube init` |
| 전체 배포 | `sbkube apply` |
| 문제 진단 | `sbkube doctor` |
| 자동 수정 | `sbkube fix --dry-run` |
| 배포 히스토리 | `sbkube history` |
| 리소스 삭제 | `sbkube delete --dry-run` |
```

### 3. 워크플로우 다이어그램 업데이트
현재 PRODUCT.md의 워크플로우 다이어그램에 새 명령어 추가:

```
init (최초 1회)
  ↓
apply (통합 실행)
  ├─ prepare
  ├─ build
  ├─ template
  └─ deploy
  ↓
history (실행 확인)
  ↓
doctor (문제 진단)
  ↓
fix (자동 수정)
```

---

## 🔍 검증 방법

### 자동화된 문서 검증
```bash
# 1. 모든 명령어 도움말 추출
for cmd in $(sbkube --help | grep "^\s\s" | awk '{print $1}'); do
  echo "## $cmd"
  sbkube $cmd --help
done

# 2. 문서화된 명령어와 비교
grep "^## [🔧🔨📄🚀🗑️].*-" docs/02-features/commands.md

# 3. 차이점 확인
diff <(sbkube --help | grep "^\s\s" | awk '{print $1}' | sort) \
     <(grep "^## [🔧🔨📄🚀🗑️].*-" docs/02-features/commands.md | \
       sed 's/.*- \(.*\)/\1/' | sort)
```

---

## 📅 다음 단계

1. 이 리포트를 바탕으로 문서 개선 이슈 생성
2. 우선순위 1 항목부터 순차 처리
3. CI/CD에 문서 검증 단계 추가 고려

---

**작성자**: Claude (claude-sonnet-4-5)
**검토 방법**: 자동 분석 + 코드 대조 + 실제 CLI 테스트
**다음 검토 예정**: 2025-02 (v0.5.0 릴리스 전)
