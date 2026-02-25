# Integration: Data Pipeline

Kafka + Spark + MinIO 데이터 파이프라인 예제입니다.

## 📋 개요

**구성 요소**:
- **Kafka** (메시지 스트림)
- **Spark** (데이터 처리)
- **MinIO** (S3 스토리지)

## 🎯 아키텍처

```
Producer → Kafka → Spark Processing → MinIO (결과 저장)
```

## 🚀 빠른 시작

```bash
sbkube apply -f sbkube.yaml \
  --app-dir examples/integration/03-data-pipeline \
  --namespace data-pipeline
```

---

**데이터 파이프라인 구축 완료! 📊**
