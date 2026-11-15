# Краткая инструкция: запуск Helm-чарта CinemaAbyss
Предварительные требования

Minikube запущен: minikube status → Running
Ingress-аддон включён: minikube addons enable ingress
Туннель запущен (для доступа к Ingress с хоста, в отдельном окне от админа):

powershell
minikube tunnel
В C:\Windows\System32\drivers\etc\hosts добавлена строка:

text
127.0.0.1 cinemaabyss.example.com
и выполнен ipconfig /flushdns

# 1. Установка «с нуля»
```powershell
# Создать namespace
kubectl create namespace cinemaabyss

# Установить чарт (Secret dockerconfigjson создастся из values.yaml)
helm install cinemaabyss ./src/kubernetes/helm -n cinemaabyss

# Дождаться готовности всех pod'ов (Ctrl+C — выйти)
kubectl get pods -n cinemaabyss -w
```
Ожидаемо: 7 pod'ов 1/1 Running (proxy, events, monolith, movies, postgres, kafka, zookeeper). Первый старт — 1–2 минуты.

2. Проверка работы
```powershell
# Статус релиза
helm list -n cinemaabyss
# cinemaabyss  cinemaabyss  1  deployed  cinemaabyss-0.1.0

# Все ресурсы
kubectl get all,cm,secret,pvc,ingress -n cinemaabyss

# Ingress получил адрес
kubectl get ingress -n cinemaabyss
```
HTTP-проверки через Ingress:
```powershell
# Proxy health
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/health" -UseBasicParsing | Select-Object -ExpandProperty Content
# Strangler Fig Proxy is healthy

# Список фильмов (через proxy → movies-service)
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/api/movies" -UseBasicParsing | Select-Object StatusCode, Content

# Список пользователей (через proxy → monolith)
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/api/users" -UseBasicParsing | Select-Object StatusCode, Content

# Events health (напрямую, минуя proxy)
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/api/events/health" -UseBasicParsing | Select-Object -ExpandProperty Content
# {"status":true}
```

Создание события:

```powershell
$body = @{ movie_id=1; title="Inception"; action="viewed"; user_id=1 } | ConvertTo-Json -Compress
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/api/events/movie" `
  -Method POST -ContentType "application/json" -Body $body -UseBasicParsing `
  | Select-Object -ExpandProperty Content
# {"status":"success","partition":0,"offset":0,...}

# Consumer получил событие
kubectl logs deploy/events-service -n cinemaabyss --tail=20 | Select-String "event received"
```

3. Обновление (upgrade)
```powershell
# Изменить параметры через --set
helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss `
  --set proxyService.replicas=2

# Или через отдельный values-файл
helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss -f custom-values.yaml

# История ревизий
helm history cinemaabyss -n cinemaabyss
```

4. Откат (rollback)
```powershell
# Откатиться на предыдущую ревизию
helm rollback cinemaabyss -n cinemaabyss

# Или на конкретную
helm rollback cinemaabyss 1 -n cinemaabyss
```

5. Удаление
```powershell
helm uninstall cinemaabyss -n cinemaabyss
```
⚠️ Secret dockerconfigjson останется (в шаблоне helm.sh/resource-policy: keep) — он нужен другим чартам/сервисам. Удалить вручную:

```powershell
kubectl delete secret dockerconfigjson -n cinemaabyss
```
Удалить всё, включая namespace:

```powershell
kubectl delete namespace cinemaabyss
```

6. Быстрая диагностика
```powershell
# Логи сервиса
kubectl logs deploy/proxy-service -n cinemaabyss --tail=50
kubectl logs deploy/events-service -n cinemaabyss --tail=50

# Логи предыдущего запуска (если pod рестартовал)
kubectl logs deploy/proxy-service -n cinemaabyss --previous

# События pod'а (причины ImagePullBackOff, Pending, CrashLoopBackOff)
kubectl describe pod -n cinemaabyss <имя-pod> | Select-Object -Last 30

# События namespace (свежие)
kubectl get events -n cinemaabyss --sort-by=.lastTimestamp | Select-Object -Last 20

# Проверить рендер чарта без установки
helm template cinemaabyss ./src/kubernetes/helm -n cinemaabyss > rendered.yaml
notepad rendered.yaml
```


7. Если что-то не работает

7. Если что-то не работает
7.1. cannot reuse a name that is still in use
Причина: предыдущий helm install упал на середине, релиз cinemaabyss висит в статусе failed или pending-install. Helm не даёт переиспользовать имя.

Фикс:

powershell
# 1. Удалить зависший релиз
helm uninstall cinemaabyss -n cinemaabyss

# 2. Если не помогает (pending-install) — удалить Secret'ы с историей релиза
kubectl get secret -n cinemaabyss -l owner=helm
kubectl delete secret -n cinemaabyss -l owner=helm

# 3. Проверить, что имя свободно
helm list -n cinemaabyss --all
# Должен быть пустой список
7.2. Secret "dockerconfigjson" exists and cannot be imported
Причина: Secret создан вручную через kubectl, у него нет Helm-меток (app.kubernetes.io/managed-by: Helm и аннотаций meta.helm.sh/release-name, meta.helm.sh/release-namespace). Helm не может «захватить» его автоматически.

Фикс — один из трёх:

powershell
# Вариант A: удалить существующий, Helm создаст из values.yaml
kubectl delete secret dockerconfigjson -n cinemaabyss
helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss

# Вариант B: «присвоить» существующий Helm'у
kubectl label secret dockerconfigjson -n cinemaabyss `
  app.kubernetes.io/managed-by=Helm --overwrite

kubectl annotate secret dockerconfigjson -n cinemaabyss `
  meta.helm.sh/release-name=cinemaabyss `
  meta.helm.sh/release-namespace=cinemaabyss --overwrite

helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss

# Вариант C: --take-ownership (Helm 3.17+)
helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss --take-ownership
7.3. field not declared in schema: .spec.containers
Причина: в templates/services/events-service.yaml сломан отступ — spec: оказался на уровне корневого spec, а не внутри template:.

Фикс:

powershell
# 1. Открыть файл
notepad src/kubernetes/helm/templates/services/events-service.yaml
Убедиться, что в блоке template: отступы правильные:

yaml
  template:
    metadata:              # 4 пробела
      labels:              # 6
        app: events-service
    spec:                  # 4 пробела (НЕ 0!)
      imagePullSecrets:    # 6
        - name: dockerconfigjson
      containers:          # 6
      - name: events-service
powershell
# 2. Проверить рендер
helm template cinemaabyss ./src/kubernetes/helm -n cinemaabyss > rendered.yaml
notepad rendered.yaml
# В rendered.yaml у events-service должно быть: template: → spec: → containers:
7.4. ImagePullBackOff
Причина: Secret dockerconfigjson не создан, имя не совпадает с imagePullSecrets в deployment, или токен GHCR истёк.

Диагностика:

powershell
# 1. Secret существует?
kubectl get secret dockerconfigjson -n cinemaabyss
# NAME                TYPE                             DATA   AGE
# dockerconfigjson    kubernetes.io/dockerconfigjson   1      ...

# 2. Что в событиях pod'а?
kubectl describe pod -n cinemaabyss <имя-pod> | Select-Object -Last 30
# Искать: 401 Unauthorized / denied / manifest unknown
Фикс:

powershell
# Перегенерировать base64 из ~/.docker/config.json
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content "$env:USERPROFILE\.docker\config.json" -Raw)))

# Вставить в values.yaml → imagePullSecrets.dockerconfigjson
notepad src/kubernetes/helm/values.yaml

# Обновить релиз
helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss
7.5. Pending у postgres или kafka
Причина: нет StorageClass, PVC не может привязаться к хранилищу.

Диагностика:

powershell
# 1. PVC в каком статусе?
kubectl get pvc -n cinemaabyss
# Если STATUS: Pending — идём дальше

# 2. Почему не привязывается?
kubectl describe pvc <имя-pvc> -n cinemaabyss | Select-Object -Last 20
# Искать: "no persistent volumes available" / "storageclass not found"

# 3. Есть ли StorageClass в кластере?
kubectl get sc
Фикс:

powershell
# Docker Desktop: Settings → Kubernetes → Enable default StorageClass (галочка)

# minikube
minikube addons enable storage-provisioner
minikube addons enable default-storageclass
7.6. CrashLoopBackOff у events-service
Причина: Kafka ещё не стартовал, а events-service делает retry 15×3с и падает. startupProbe (150с) должен дать время, но если Kafka реально не работает — pod всё равно упадёт.

Диагностика:

powershell
# 1. Логи текущего контейнера
kubectl logs deploy/events-service -n cinemaabyss --tail=50

# 2. Логи предыдущего (упавшего) запуска
kubectl logs deploy/events-service -n cinemaabyss --previous --tail=50
Что искать в логах и что делать:

Сообщение	Причина	Фикс
Kafka unavailable after retries	Kafka не поднялась	kubectl get pods -n cinemaabyss -l app=kafka → kafka-0 должен быть 1/1 Running
Topic ... does not exist	топики не созданы	kubectl exec -n cinemaabyss kafka-0 -- kafka-topics.sh --bootstrap-server kafka:9092 --list — должны быть 3 топика
Name or service not known	DNS-имя kafka не резолвится	kubectl get svc kafka -n cinemaabyss — Service существует?
Connection refused	Kafka слушает не на kafka:9092	проверить KAFKA_ADVERTISED_LISTENERS в StatefulSet
Проверка, что Kafka жива:

powershell
kubectl get pods -n cinemaabyss -l "app in (kafka,zookeeper)"
# kafka-0        1/1  Running
# zookeeper-0    1/1  Running

kubectl exec -n cinemaabyss kafka-0 -- kafka-topics.sh --bootstrap-server kafka:9092 --list
# movie-events
# user-events
# payment-events
7.7. 404 или 502 через Ingress
Причина: в ConfigMap опечатка в URL бэкенда — например, movies вместо movies-service.

Диагностика:

powershell
# 1. Что реально в ConfigMap?
kubectl get configmap cinemaabyss-config -n cinemaabyss -o yaml | Select-String "SERVICE_URL"
# Должно быть:
#   MOVIES_SERVICE_URL: "http://movies-service:8081"
#   MONOLITH_URL: "http://monolith:8080"

# 2. Service'ы с такими именами существуют?
kubectl get svc -n cinemaabyss
Фикс:

powershell
# 1. Исправить в templates/configmap.yaml
notepad src/kubernetes/helm/templates/configmap.yaml
Заменить на правильное имя:

yaml
data:
  MONOLITH_URL: "http://monolith:8080"
  MOVIES_SERVICE_URL: "http://movies-service:8081"      # не http://movies:8081
  EVENTS_SERVICE_URL: "http://events-service:8082"
powershell
# 2. Обновить релиз
helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss

# 3. Перезапустить proxy, чтобы он перечитал ConfigMap
kubectl rollout restart deploy/proxy-service -n cinemaabyss
7.8. ping cinemaabyss.example.com возвращает timeout
Причина: minikube tunnel не запущен, или ADDRESS у Ingress всё ещё 192.168.49.2 (внутренний IP ноды, с хоста недоступен).

Фикс:

``` powershell
# 1. Открыть ОТДЕЛЬНОЕ окно PowerShell от администратора
# и запустить туннель (НЕ ЗАКРЫВАТЬ это окно)
minikube tunnel
```
```powershell
# 2. В другом окне проверить, что Ingress жив
kubectl get ingress -n cinemaabyss
# ADDRESS должен быть 127.0.0.1 или 192.168.49.2
```
```powershell
# 3. Проверить hosts
Get-Content C:\Windows\System32\drivers\etc\hosts | Select-String "cinemaabyss"
# Должно быть: 127.0.0.1 cinemaabyss.example.com

# 4. Сбросить DNS-кэш
ipconfig /flushdns

# 5. Проверить ping и HTTP
ping cinemaabyss.example.com
# Ответ от 127.0.0.1: ...

Invoke-WebRequest -Uri "http://cinemaabyss.example.com/health" -UseBasicParsing | Select-Object -ExpandProperty Content
# Strangler Fig Proxy is healthy
```
```powershell
# 1. Все pod'ы
kubectl get pods -n cinemaabyss

# 2. Детали проблемного pod'а (последние 30 строк)
kubectl describe pod -n cinemaabyss <имя-проблемного-pod> | Select-Object -Last 30

# 3. Логи проблемного контейнера (текущего и предыдущего)
kubectl logs deploy/<имя-сервиса> -n cinemaabyss --tail=50
kubectl logs deploy/<имя-сервиса> -n cinemaabyss --previous --tail=50
# Замените <имя-проблемного-pod> и <имя-сервиса> на реальные (proxy-service, events-service, kafka-0 и т.д.).
```
##### Порядок «холодного старта» (пример)
```powershell
# 1. Подготовка
minikube status
minikube addons enable ingress

# 2. Туннель (в ОТДЕЛЬНОМ окне, от админа, не закрывать)
minikube tunnel

# 3. hosts (один раз)
# C:\Windows\System32\drivers\etc\hosts → 127.0.0.1 cinemaabyss.example.com
ipconfig /flushdns

# 4. Установка
kubectl create namespace cinemaabyss
helm install cinemaabyss ./src/kubernetes/helm -n cinemaabyss

# 5. Дождаться готовности
kubectl get pods -n cinemaabyss -w

# 6. Проверка
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/health" -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/api/movies" -UseBasicParsing | Select-Object StatusCode

# 7. Создание события
$body = @{ movie_id=1; title="Inception"; action="viewed"; user_id=1 } | ConvertTo-Json -Compress
Invoke-WebRequest -Uri "http://cinemaabyss.example.com/api/events/movie" `
  -Method POST -ContentType "application/json" -Body $body -UseBasicParsing

# 8. Проверка consumer'а
kubectl logs deploy/events-service -n cinemaabyss --tail=20 | Select-String "event received"
```


## Проверка кафки

```bash
# 1. Логи падающего Kafka (критично)
kubectl logs kafka-0 -n cinemaabyss --previous --tail=100

# 2. События pod'а
kubectl describe pod kafka-0 -n cinemaabyss | Select-Object -Last 40

# 3. PVC в каком статусе
kubectl get pvc -n cinemaabyss

# Service существует?
kubectl get svc kafka -n cinemaabyss

# Endpoints у Service есть? (это IP pod'а Kafka)
kubectl get endpoints kafka -n cinemaabyss

# Если ENDPOINTS: <none> — Service не видит pod. Причина — селектор не совпадает с labels pod'а

# Labels Service
kubectl get svc kafka -n cinemaabyss -o jsonpath="{.spec.selector}"

# Топики
kubectl exec -n cinemaabyss kafka-0 -- kafka-topics.sh --bootstrap-server kafka:9092 --list
```
#### Вариант исправления:
🛠️ Шаг 1: Убедиться, что PVC действительно удалён и пересоздан
```powershell
# 1. Масштабируем Kafka в 0, чтобы освободить PVC
kubectl scale statefulset kafka -n cinemaabyss --replicas=0

# 2. Проверяем, что поды Kafka удалены
kubectl get pods -n cinemaabyss -l app=kafka
# (Вывод должен быть пустым)

# 3. Удаляем PVC. Обратите внимание на имя — оно может быть kafka-data или kafka-data-kafka-0
kubectl delete pvc kafka-data -n cinemaabyss --ignore-not-found
# Если PVC не найден, проверьте точное имя:
kubectl get pvc -n cinemaabyss

# 4. Убеждаемся, что PVC удалён
kubectl get pvc -n cinemaabyss
# (В списке не должно быть PVC, связанного с kafka)
```
🛠️ Шаг 2: Пересоздать PVC и запустить Kafka
```bash
# 1. Применяем Helm-чарт. Это должно пересоздать PVC, так как его больше нет.
helm upgrade cinemaabyss ./src/kubernetes/helm -n cinemaabyss

# 2. Запускаем Kafka обратно
kubectl scale statefulset kafka -n cinemaabyss --replicas=1

# 3. Смотрим за запуском
kubectl get pods -n cinemaabyss -l app=kafka -w
```


### Рестарт сервиса events после падения kafka
```bash
# 1. Логи (главное)
kubectl logs deploy/events-service -n cinemaabyss --previous --tail=50

# 2. Связность с Kafka (Порт доступен?)
kubectl exec -n cinemaabyss deploy/events-service -- python -c "import socket; s=socket.socket(); s.settimeout(3); print(s.connect_ex(('kafka', 9092)))"

# 3. Топики
kubectl exec -n cinemaabyss kafka-0 -- kafka-topics.sh --bootstrap-server kafka:9092 --list


# 4. Детали pod'а (включая Last State)
kubectl describe pod -n cinemaabyss -l app=events-service | Select-Object -Last 40

# 5. Пересоздать pod
kubectl delete pod -n cinemaabyss -l app=events-service
kubectl get pods -n cinemaabyss -l app=events-service -w
```
