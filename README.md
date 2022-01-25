# Flathub website backend

This is the fastapi based backend for https://www.flathub.org
Not the backend for flathub itself. Go here, if your looking for that https://github.com/flathub/flathub

## Development

### Prerequisites

- Docker
- Docker-compose

### Running

Start the database:

```bash
docker-compose up
```

You need to seed the database:

```bash
curl -X POST localhost:8000/update
```

If you change any files, the server should restart and you should be able to see the changes.

If you want to explore the endpoints, you can use the UI:
https://localhost:8000/docs

### Accessing redis

You can use a redis tool of your choice to interact with the database.
Just connect to localhost:6379.

### Running the smoketests locally

If you want to run the smoketests locally, you can use the following commands:

```bash
    docker compose up -d
    docker exec backend-backend-1 pip3 install pytest
    docker exec backend-backend-1 python3 -m pytest tests/main.py
```

You might need to flush your redis database before running the tests. As it assumes that the database is empty.
