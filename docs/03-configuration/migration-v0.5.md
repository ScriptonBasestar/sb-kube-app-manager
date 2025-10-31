# 마이그레이션 가이드: v0.5.0 (Working Directory 통합)

> **⚠️ Breaking Changes**: v0.5.0에서 작업 디렉토리가 `.sbkube/` 하위로 통합되었습니다.

## 📋 변경 사항 요약

### 디렉토리 구조 변경

**v0.4.x 이전**:

```
project/
├── charts/          # Helm 차트
├── repos/           # Git 리포지토리
├── build/           # 빌드 결과
├── rendered/        # 템플릿 결과
├── config.yaml
└── sources.yaml
```

**v0.5.0 이후**:

```
project/
├── .sbkube/         # 모든 작업 디렉토리 통합
│   ├── charts/      # Helm 차트
│   ├── repos/       # Git 리포지토리
│   ├── build/       # 빌드 결과
│   └── rendered/    # 템플릿 결과
├── config.yaml
└── sources.yaml
```

### 변경된 기본 경로

| 명령어 | v0.4.x | v0.5.0 | |--------|--------|--------| | `prepare` | `charts/`, `repos/` | `.sbkube/charts/`,
`.sbkube/repos/` | | `build` | `build/` | `.sbkube/build/` | | `template` | `rendered/` (app-dir 기준) |
`.sbkube/rendered/` (base-dir 기준) | | `upgrade` | `build/` (app-dir 기준) | `.sbkube/build/` (base-dir 기준) |

### .gitignore 단순화

**v0.4.x**:

```gitignore
charts/
repos/
build/
rendered/
*.local.yaml
*.override.yaml
.sbkube/
```

**v0.5.0**:

```gitignore
# 모든 작업 디렉토리가 .sbkube/ 하나로 통합
.sbkube/
*.local.yaml
*.override.yaml
```

## 🔄 마이그레이션 방법

### 방법 1: 자동 마이그레이션 (권장)

기존 디렉토리를 `.sbkube/` 하위로 이동:

```bash
# 프로젝트 루트에서 실행
mkdir -p .sbkube

# 기존 디렉토리 이동
[ -d charts ] && mv charts .sbkube/
[ -d repos ] && mv repos .sbkube/
[ -d build ] && mv build .sbkube/
[ -d rendered ] && mv rendered .sbkube/

# .gitignore 업데이트
cat >> .gitignore << 'EOF'

# SBKube v0.5.0+ 작업 디렉토리
.sbkube/
EOF

# 이전 .gitignore 항목 제거 (선택사항)
# charts/, repos/, build/, rendered/ 제거
```

### 방법 2: 클린 재생성

기존 디렉토리를 삭제하고 재생성:

```bash
# 기존 작업 디렉토리 삭제
rm -rf charts repos build rendered

# .gitignore 업데이트
cat >> .gitignore << 'EOF'

# SBKube v0.5.0+ 작업 디렉토리
.sbkube/
EOF

# 재실행 (자동으로 .sbkube/ 하위에 생성)
sbkube prepare
sbkube build
sbkube template  # 필요시
```

### 방법 3: 점진적 마이그레이션

한 프로젝트씩 마이그레이션:

```bash
# 1. 새로운 브랜치 생성
git checkout -b migrate-v0.5

# 2. 방법 1 또는 방법 2 실행

# 3. 테스트
sbkube doctor
sbkube prepare
sbkube build
sbkube template

# 4. 배포 테스트 (--dry-run)
sbkube deploy --dry-run

# 5. 문제없으면 커밋 및 병합
git add .
git commit -m "chore: Migrate to SBKube v0.5.0 (.sbkube directory)"
git checkout main
git merge migrate-v0.5
```

## ⚠️ 주의사항

### 1. CI/CD 파이프라인 업데이트

기존 CI/CD 스크립트에서 경로를 참조하는 경우 업데이트 필요:

**v0.4.x**:

```yaml
# .github/workflows/deploy.yml
- name: Check rendered files
  run: ls -la rendered/
```

**v0.5.0**:

```yaml
# .github/workflows/deploy.yml
- name: Check rendered files
  run: ls -la .sbkube/rendered/
```

### 2. 커스텀 스크립트 업데이트

경로를 하드코딩한 스크립트가 있다면 수정:

```bash
# Before
if [ -d "charts/myapp" ]; then
  echo "Chart exists"
fi

# After
if [ -d ".sbkube/charts/myapp" ]; then
  echo "Chart exists"
fi
```

### 3. template --output-dir 변경

`template` 명령어의 `--output-dir` 기본값 변경:

**v0.4.x**:

```bash
# 기본값: rendered/ (app-dir 기준)
sbkube template --app-dir config
# → config/rendered/ 에 생성
```

**v0.5.0**:

```bash
# 기본값: .sbkube/rendered/ (base-dir 기준)
sbkube template --app-dir config
# → .sbkube/rendered/ 에 생성
```

**이전 동작 유지 방법**:

```bash
# 명시적으로 경로 지정
sbkube template --app-dir config --output-dir config/rendered
```

### 4. 멀티 환경 프로젝트

환경별로 별도 디렉토리를 사용하는 경우:

**v0.4.x**:

```
project/
├── dev/
│   ├── charts/
│   └── config.yaml
├── staging/
│   ├── charts/
│   └── config.yaml
└── prod/
    ├── charts/
    └── config.yaml
```

**v0.5.0**:

```
project/
├── dev/
│   ├── .sbkube/
│   └── config.yaml
├── staging/
│   ├── .sbkube/
│   └── config.yaml
└── prod/
    ├── .sbkube/
    └── config.yaml
```

각 환경 디렉토리가 독립적인 `.sbkube/`를 가집니다.

## ✅ 마이그레이션 체크리스트

마이그레이션 후 다음 항목을 확인하세요:

- [ ] 기존 `charts/`, `repos/`, `build/`, `rendered/` 디렉토리 제거 또는 이동
- [ ] `.sbkube/` 디렉토리 생성 확인
- [ ] `.gitignore`에 `.sbkube/` 추가
- [ ] `.gitignore`에서 이전 항목 제거 (선택사항)
- [ ] `sbkube doctor` 실행하여 환경 확인
- [ ] `sbkube prepare` 실행하여 차트 다운로드 확인
- [ ] `sbkube build` 실행하여 빌드 확인
- [ ] `sbkube template` 실행하여 템플릿 생성 확인
- [ ] `sbkube deploy --dry-run` 실행하여 배포 시뮬레이션
- [ ] CI/CD 파이프라인 스크립트 업데이트 확인
- [ ] 커스텀 스크립트 경로 업데이트 확인
- [ ] 팀원들에게 마이그레이션 공지

## 🚨 롤백 방법

마이그레이션 후 문제가 발생한 경우:

```bash
# 1. v0.4.x 버전으로 다운그레이드
pip install sbkube==0.4.9

# 2. .sbkube/ 디렉토리를 다시 분리
[ -d .sbkube/charts ] && mv .sbkube/charts ./
[ -d .sbkube/repos ] && mv .sbkube/repos ./
[ -d .sbkube/build ] && mv .sbkube/build ./
[ -d .sbkube/rendered ] && mv .sbkube/rendered ./
rm -rf .sbkube

# 3. .gitignore 복원
# (이전 버전의 .gitignore 사용)
```

## 📞 도움말

마이그레이션 중 문제가 발생한 경우:

1. **GitHub Issues**: https://github.com/archmagece/sb-kube-app-manager/issues
1. **문서**: https://github.com/archmagece/sb-kube-app-manager/tree/main/docs
1. **예제**: `examples/` 디렉토리 참조

## 🎯 마이그레이션 후 장점

1. **단순한 .gitignore**: 5개 항목 → 1개 항목
1. **명확한 구분**: 사용자 파일 vs SBKube 작업 파일
1. **일관성**: 모든 임시/캐시 파일이 한 곳에
1. **멀티 환경**: 각 환경별 독립적 작업 디렉토리

______________________________________________________________________

**버전**: v0.5.0 **작성일**: 2025-10-31 **업데이트**: 2025-10-31
