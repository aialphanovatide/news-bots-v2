# News Bots v2 - Docker Environment Guide

Welcome to the News Bots v2 project! This guide will help you set up and manage the Docker environment for both development and production. Let's get started!

## Getting Started

First, make sure you have Docker and Docker Compose installed on your system.

### Development Environment

To start the development environment:

```bash
docker compose -f docker-compose-dev.yml up -d
```


This command starts all services defined in the development configuration.

### Production Environment

For the production environment:

```bash
docker compose up -d
```


## Accessing Data

### Redis

To access Redis data:

1. Connect to the Redis container:
   ```bash
   docker compose exec redis-dev redis-cli -a ${REDIS_PASSWORD}
   ```
   Replace `${REDIS_PASSWORD}` with your actual Redis password.

2. Once connected, you can use Redis commands like:
   ```
   KEYS *
   GET key_name
   ```

### PostgreSQL

To access PostgreSQL data:

1. Connect to the PostgreSQL container:
   ```bash
   docker compose exec postgres-dev psql -U ${DB_USER} -d ${DB_NAME}_dev
   ```
   Replace `${DB_USER}` and `${DB_NAME}` with your actual database user and name.

2. Once connected, you can run SQL queries, for example:
   ```sql
   SELECT * FROM your_table_name;
   ```

## Container Management

### View Running Containers

```bash
docker compose ps
```


### View Container Logs

```bash
docker compose logs -f service_name
```


Replace `service_name` with the actual service name.

## Helpful Tips

- The development environment uses ports 5432 for PostgreSQL and 6379 for Redis.
- The production environment uses ports 5433 for PostgreSQL and 6380 for Redis.
- Always use environment variables for sensitive information like passwords.
- Check the `docker-compose-dev.yml` and `docker-compose.yml` files for detailed service configurations.

## Troubleshooting

If you encounter any issues:
1. Ensure all required environment variables are set.
2. Check container logs for error messages.
3. Try rebuilding the containers: `docker compose -f docker-compose-dev.yml up --build -d`
