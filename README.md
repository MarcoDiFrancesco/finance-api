![assets/swagger-example.png](assets/swagger-example.png)

https://api.marcodifrancesco.com/api/docs

## Kubernetes Build & Deploy

```bash
docker build -t localhost:30500/api:latest .
docker push localhost:30500/api:latest
kubectl rollout restart deployment/api -n api
```

## Production

```bash
docker compose up
```

## Development

```bash
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up
```
