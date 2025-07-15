# Performance Tests

이 디렉토리는 SBKube 프로젝트의 성능 테스트를 포함합니다.

## 🎯 목적

SBKube CLI 도구의 성능 특성을 측정하고 성능 저하를 조기에 발견합니다.

## 📁 테스트 파일

```
performance/
├── test_performance_benchmarks.py  # 성능 벤치마크 테스트
└── conftest.py                     # 성능 테스트 전용 fixture
```

## 🧪 측정 항목

### 실행 시간 벤치마크

- **prepare** 명령어 실행 시간
- **build** 명령어 실행 시간
- **template** 명령어 실행 시간
- **deploy** 명령어 실행 시간

### 리소스 사용량

- **메모리 사용량**: 대용량 설정 파일 처리
- **CPU 사용률**: 다중 앱 동시 처리
- **디스크 I/O**: Chart 다운로드 및 빌드

### 스케일링 테스트

- **다중 앱 배포**: 10개, 50개, 100개 앱
- **대용량 매니페스트**: 10MB+ YAML 파일
- **동시 실행**: 병렬 배포 성능

## 🏃‍♂️ 실행 방법

```bash
# 전체 성능 테스트 실행
pytest tests/performance/ -v

# 벤치마크 결과 저장
pytest tests/performance/ -v --benchmark-json=benchmark.json

# 마커 기반 실행
pytest -m performance -v

# 특정 벤치마크만 실행
pytest tests/performance/test_performance_benchmarks.py::test_prepare_command_performance -v
```

## 📊 벤치마크 리포트

### 기준선 성능 (예시)

```
Command Performance Benchmarks
├── prepare:  < 5초    (10개 앱)
├── build:    < 10초   (10개 앱)  
├── template: < 3초    (10개 앱)
└── deploy:   < 30초   (10개 앱, dry-run)

Memory Usage
├── 기본:     < 50MB
├── 대용량:   < 200MB  (100개 앱)
└── 피크:     < 500MB  (매니페스트 처리)
```

### 성능 임계값

- **prepare**: 5초 이내 (10개 앱 기준)
- **build**: 10초 이내 (10개 앱 기준)
- **메모리**: 200MB 이내 (일반적 사용)
- **실패율**: 1% 이내 (네트워크 재시도 포함)

## 🔧 사전 요구사항

### 개발 환경

```bash
# pytest-benchmark 설치
pip install pytest-benchmark

# 메모리 프로파일링 (선택사항)
pip install memory-profiler
pip install psutil
```

### 테스트 데이터

- 다양한 크기의 설정 파일
- 실제 Helm Chart 소스
- 모의 Kubernetes 클러스터

## ⚙️ 설정

### pytest-benchmark 설정

```python
# conftest.py 설정 예시
@pytest.fixture
def performance_benchmark():
    """성능 벤치마크 설정"""
    return {
        'min_rounds': 3,
        'max_time': 60.0,
        'warmup': True
    }
```

### 환경 최적화

```bash
# CPU 성능 모드 (Linux)
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 스왑 비활성화 (정확한 메모리 측정)
sudo swapoff -a
```

## 📈 모니터링

### 성능 저하 감지

```python
# 성능 회귀 테스트 예시
def test_prepare_performance_regression(benchmark):
    """prepare 명령어 성능 회귀 테스트"""
    
    def prepare_operation():
        # prepare 로직 실행
        pass
    
    result = benchmark(prepare_operation)
    
    # 기준선 대비 20% 이상 느려지면 실패
    assert result.stats.mean < 5.0, "prepare 성능 저하 감지"
```

### CI/CD 통합

```yaml
# GitHub Actions 예시
- name: Run Performance Tests
  run: |
    pytest tests/performance/ --benchmark-json=results.json
    
- name: Performance Regression Check
  run: |
    python scripts/check_performance_regression.py results.json
```

## 🎛️ 프로파일링

### 메모리 프로파일링

```bash
# 메모리 사용량 상세 분석
python -m memory_profiler scripts/profile_sbkube.py

# 라인별 메모리 사용량
python -m line_profiler scripts/profile_sbkube.py
```

### CPU 프로파일링

```bash
# cProfile 사용
python -m cProfile -o profile.stats scripts/profile_sbkube.py

# 결과 분석
python -m pstats profile.stats
```

## 🚨 알림 및 임계값

### 성능 경고

- **실행 시간**: 기준선 대비 50% 증가
- **메모리 사용량**: 기준선 대비 100% 증가
- **실패율**: 5% 이상

### 자동 알림

- CI/CD 파이프라인에서 성능 저하 감지 시 알림
- 주간 성능 리포트 생성
- 성능 트렌드 시각화

## 📝 리포트 생성

```bash
# HTML 리포트 생성
pytest tests/performance/ --benchmark-histogram=histogram.svg

# 비교 리포트 생성  
pytest-benchmark compare baseline.json current.json --histogram=comparison.svg
```
