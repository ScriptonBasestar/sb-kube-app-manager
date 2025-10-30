# Use Case: Message Queue (RabbitMQ Cluster)

RabbitMQ 클러스터를 활용한 비동기 메시지 처리 예제입니다.

## 📋 개요

**카테고리**: Use Cases

**구성 요소**:
- **RabbitMQ Cluster** (3 nodes)
- **Producer** (메시지 발행)
- **Consumer** (메시지 소비)
- **Management UI**

**학습 목표**:
- RabbitMQ 클러스터 구성
- 비동기 메시지 패턴
- 고가용성 큐
- 메시지 영속성

## 🎯 사용 사례

### 1. 비동기 작업 처리
```
API → RabbitMQ → Worker Pool
                    ↓
                (이메일, 이미지 처리, 알림)
```

### 2. 이벤트 기반 아키텍처
```
Service A → Exchange → Queue A → Consumer A
                     → Queue B → Consumer B
```

### 3. 부하 분산
```
Multiple Producers → Queue → Multiple Consumers (라운드 로빈)
```

## 🚀 빠른 시작

```bash
# RabbitMQ 클러스터 배포
sbkube apply \
  --app-dir examples/use-cases/11-message-queue \
  --namespace mq-demo

# 배포 확인
kubectl get pods -n mq-demo
kubectl get pvc -n mq-demo

# Management UI 접속
kubectl port-forward -n mq-demo svc/rabbitmq 15672:15672 &
# 브라우저: http://localhost:15672
# 로그인: user / password123
```

## 📖 RabbitMQ 사용법

### 1. 클러스터 상태 확인

```bash
# 클러스터 노드 확인
kubectl exec -it rabbitmq-0 -n mq-demo -- rabbitmqctl cluster_status

# 큐 목록
kubectl exec -it rabbitmq-0 -n mq-demo -- rabbitmqctl list_queues

# 연결 확인
kubectl exec -it rabbitmq-0 -n mq-demo -- rabbitmqctl list_connections
```

### 2. Producer (메시지 발행)

**Python 예제**:
```python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters('rabbitmq.mq-demo.svc.cluster.local')
)
channel = connection.channel()

# 큐 선언
channel.queue_declare(queue='task_queue', durable=True)

# 메시지 발행
channel.basic_publish(
    exchange='',
    routing_key='task_queue',
    body='Hello RabbitMQ',
    properties=pika.BasicProperties(delivery_mode=2)  # 영속성
)

connection.close()
```

### 3. Consumer (메시지 소비)

**Python 예제**:
```python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters('rabbitmq.mq-demo.svc.cluster.local')
)
channel = connection.channel()

channel.queue_declare(queue='task_queue', durable=True)

def callback(ch, method, properties, body):
    print(f"Received: {body}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='task_queue', on_message_callback=callback)

channel.start_consuming()
```

## 🎓 학습 포인트

### 1. Exchange Types

**Direct Exchange**:
```yaml
# Routing Key 완전 일치
routing_key: "email" → Queue: email_queue
```

**Topic Exchange**:
```yaml
# 패턴 매칭
routing_key: "log.error" → Queue: error_logs
routing_key: "log.*" → Queue: all_logs
```

**Fanout Exchange**:
```yaml
# 브로드캐스트 (모든 큐로 전송)
```

### 2. 메시지 영속성

**Durable Queue**:
```python
channel.queue_declare(queue='task_queue', durable=True)
```

**Persistent Message**:
```python
channel.basic_publish(
    exchange='',
    routing_key='task_queue',
    body='message',
    properties=pika.BasicProperties(delivery_mode=2)
)
```

### 3. 고가용성

**Mirrored Queue** (클러스터 전체 복제):
```bash
kubectl exec -it rabbitmq-0 -n mq-demo -- rabbitmqctl set_policy ha-all \
  "^ha\." '{"ha-mode":"all"}' --apply-to queues
```

**Quorum Queue** (Raft 기반):
```python
channel.queue_declare(
    queue='quorum_queue',
    durable=True,
    arguments={'x-queue-type': 'quorum'}
)
```

## 💡 실전 패턴

### Work Queue (작업 큐)

```yaml
# Producer: 작업 발행
task_queue → [task1, task2, task3, ...]

# Multiple Consumers: 라운드 로빈
Consumer 1 → task1, task3
Consumer 2 → task2
```

### Pub/Sub (발행/구독)

```yaml
# Publisher → Exchange (fanout)
Publisher → logs_exchange
              ↓
        ┌─────┼─────┐
        ↓     ↓     ↓
    Queue1 Queue2 Queue3
        ↓     ↓     ↓
     Sub1  Sub2  Sub3
```

### RPC (원격 프로시저 호출)

```yaml
Client → request_queue → Server
Client ← reply_queue ← Server
```

## 🔍 트러블슈팅

### 문제: 클러스터 노드가 조인되지 않음

**확인**:
```bash
# Erlang Cookie 확인
kubectl exec -it rabbitmq-0 -n mq-demo -- cat /var/lib/rabbitmq/.erlang.cookie

# DNS 확인
kubectl exec -it rabbitmq-0 -n mq-demo -- nslookup rabbitmq-headless.mq-demo.svc.cluster.local
```

### 문제: 메시지가 유실됨

**원인**: Durable 설정 누락

**해결**:
- Queue: `durable=True`
- Message: `delivery_mode=2`
- Consumer: `basic_ack()` 사용

### 문제: Consumer가 메시지를 받지 못함

**확인**:
```bash
# 큐 상태 확인
kubectl exec -it rabbitmq-0 -n mq-demo -- rabbitmqctl list_queues name messages consumers

# Management UI 확인
http://localhost:15672/#/queues
```

## 📚 참고 자료

- [RabbitMQ 공식 문서](https://www.rabbitmq.com/documentation.html)
- [RabbitMQ Cluster Operator](https://www.rabbitmq.com/kubernetes/operator/operator-overview.html)

## 🧹 정리

```bash
kubectl delete namespace mq-demo
```

---

**RabbitMQ로 확장 가능한 메시징 시스템을 구축하세요! 🐰**
