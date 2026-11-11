## Общие сведения

MVP сервис events, который при вызове API создавать и сам же читать сообщения в топике Kafka.

    - Разработайте сервис на любом языке программирования с consumer'ами и producer'ами.
    - Реализован простой API, при вызове которого будут создаваться события User/Payment/Movie и обрабатываются внутри сервиса с записью в лог
    <!-- - Добавьте в docker-compose новый сервис, kafka там уже есть -->


Архитектура сервиса:
```text
===== Компоненты сервиса
POST /api/events/movie ──┐
POST /api/events/user  ──┼─► [Producer] ─► Kafka ─► [Consumer] ─► log
POST /api/events/payment─┘    (один процесс, два фоновых компонента)


===== Структура проекта (простой вариант):

src/microservices/events/
├── Dockerfile
├── requirements.txt
└── app/
    ├── __init__.py
    ├── config.py       ← настройки (Kafka, топики, лог)
    ├── models.py       ← pydantic-модели из спецификации
    ├── producer.py     ← aiokafka producer + graceful stop
    ├── consumer.py     ← aiokafka consumer в background task
    ├── service.py      ← бизнес-логика (обогащение → Event → publish)
    ├── routes.py       ← 4 роута из спеки + /health для проб
    └── main.py         ← lifespan, retry при старте


```

Проверка решения:

1) На этапе разработки достаточно поднять CinemaAbyss API без сервиса proxy и запустить main.py 
или запустить вложенный Dockerfile, если остальне сервисы уже запущены через Докер-композе. 
Прокси запускаемый из Docker-compose требуется остановить.

Выполнить команды в каталоге проекта:
```bash
docker build -t cinema-proxy-standalone:v1-test .

docker run -d `
  --name cinema-proxy-standalone `
  --network cinemaabyss-network `
  -p 8000:8000 `
  -e PORT=8000 `
  -e MONOLITH_URL=http://cinemaabyss-monolith:8080 `
  -e MOVIES_SERVICE_URL=http://cinemaabyss-movies-service:8081 `
  -e EVENTS_SERVICE_URL=http://cinemaabyss-events-service:8082 `
  -e GRADUAL_MIGRATION=true `
  -e MOVIES_MIGRATION_PERCENT=50 `
  cinema-proxy-standalone:v1-test
```

В проекте не генерируем схему из проксирующий роутов, а используем предоставленную - - см. 
[Спецификация шлюза](app/api-specification.yaml "api-specification.yaml")
После  запуска документация шлюза будет доступна по адресу:
```http request
http://localhost:8000/docs
```
