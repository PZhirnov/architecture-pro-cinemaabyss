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
