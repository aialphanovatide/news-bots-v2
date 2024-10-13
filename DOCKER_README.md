<!-- # News Bots v2 - Docker Environment Guide

Welcome to the News Bots v2 project! This guide will help you set up and manage the Docker environment for both development and production. Let's get started!

## Getting Started

First, make sure you have Docker and Docker Compose installed on your system.

### Development Environment

To start the development environment:

```bash
docker compose -f docker-compose-dev.yml up -d  -p news-bot-prod
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

#### This command will effectively clean up all resources (containers, networks, volumes, and images) associated with your docker-compose-dev.yml file. 

```bash
docker-compose -f docker-compose-dev.yml down -v --rmi all --remove-orphans
```


### View Container Logs

```bash
docker compose logs -f service_name
```

### 
```bash
docker-compose -f docker-compose.yml -p news-bot-prod up
```

```bash
docker-compose -f docker-compose-dev.yml -p news-bot-prod #last part etiquete for naming the namesoce up
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
3. Try rebuilding the containers: `docker compose -f docker-compose-dev.yml up --build -d` -->


# News Bots v2 - Docker Environment Guide

Welcome to the News Bots v2 project! This guide will help you set up and manage the Docker environment for both development and production.

## Getting Started

Ensure Docker and Docker Compose are installed on your system.

### Development Environment

Start the development environment:

```bash
docker compose -f docker-compose-dev.yml up -d -p news-bot-dev
```

### Production Environment

Start the production environment:

```bash
docker compose -f docker-compose.yml up -d -p news-bot-prod
```

## Accessing Data

### Redis

Connect to the Redis container:

```bash
docker compose exec redis-dev redis-cli -a ${REDIS_PASSWORD}
```

Example Redis commands:
```
KEYS *
GET key_name
```

### PostgreSQL

Connect to the PostgreSQL container:

```bash
docker compose exec postgres-dev psql -U ${DB_USER} -d ${DB_NAME}_dev
```

Example SQL query:
```sql
SELECT * FROM your_table_name;
```

#### Connecting to PostgreSQL from Another Machine

1. Find the host machine's IP address:
   ```bash
   ip addr show
   ```

2. From another machine, use a PostgreSQL client with these details:
   - Host: <host_machine_ip>
   - Port: 5432
   - User: ${DB_USER}
   - Password: ${DB_PASSWORD}
   - Database: ${DB_NAME}_dev

## Container Management

### View Running Containers
```bash
docker compose ps
```

### Clean Up Resources
```bash
docker-compose -f docker-compose-dev.yml down -v --rmi all --remove-orphans
```

### View Container Logs
```bash
docker compose logs -f service_name
```

### Start Specific Service Group
```bash
docker-compose -f docker-compose.yml -p news-bot-prod --profile group1 up
```

## Volume Management

### List Volumes
```bash
docker volume ls
```

### Inspect a Volume
```bash
docker volume inspect volume_name
```

### Remove a Volume
```bash
docker volume rm volume_name
```

### To remove all unused volumes (including those from other projects)
```bash
docker volume prune
```

### Backup a Volume
```bash
docker run --rm -v volume_name:/source -v $(pwd):/backup alpine tar -czvf /backup/volume_backup.tar.gz -C /source .
```

### Restore a Volume
```bash
docker run --rm -v volume_name:/target -v $(pwd):/backup alpine sh -c "rm -rf /target/* /target/..?* /target/.[!.]* ; tar -xzvf /backup/volume_backup.tar.gz -C /target"
```

## Network Management

### List Networks
```bash
docker network ls
```

### Inspect a Network
```bash
docker network inspect network_name
```

### Remove a Network
```bash
docker network rm network_name
```

## Helpful Tips

- Development environment: PostgreSQL on port 5432, Redis on 6379
- Production environment: PostgreSQL on port 5433, Redis on 6380
- Use environment variables for sensitive information
- Check `docker-compose-dev.yml` and `docker-compose.yml` for detailed configurations

## Troubleshooting

1. Ensure all required environment variables are set
2. Check container logs: `docker compose logs -f service_name`
3. Rebuild containers: `docker compose -f docker-compose-dev.yml up --build -d`
4. Check Docker daemon logs: `sudo journalctl -fu docker.service`
5. Verify network connectivity: `docker network inspect network_name`

## Advanced Commands

### Execute a Command in a Running Container
```bash
docker compose exec service_name command
```

### View Resource Usage
```bash
docker stats
```

### Update a Single Service
```bash
docker compose up -d --no-deps service_name
```

Remember to replace placeholders like `${DB_USER}`, `${DB_PASSWORD}`, `${DB_NAME}`, `volume_name`, `network_name`, and `service_name` with actual values from your setup.