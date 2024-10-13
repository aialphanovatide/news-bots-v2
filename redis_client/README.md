# Redis Client for Flask Application

This Redis client is designed to work with our Flask application, providing caching functionality and cache invalidation for API endpoints.

## Installing Redis on macOS

To use this Redis client locally on macOS, you need to install Redis. Follow these steps:

1. Install Homebrew (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install Redis using Homebrew:
   ```bash
   brew install redis
   ```

3. Start the Redis service:
   ```bash
   brew services start redis
   ```

4. Verify the installation:
   ```bash
   redis-cli ping
   ```
   If you see "PONG" as the response, Redis is installed and running correctly.

## Starting Redis Service

After installation, Redis is configured to start automatically when your Mac boots up. However, if you need to manually start, stop, or restart the service, use these commands:

- Start Redis:
  ```bash
  brew services start redis
  ```

- Stop Redis:
  ```bash
  brew services stop redis
  ```

- Restart Redis:
  ```bash
  brew services restart redis
  ```

## Connecting to Redis

By default, Redis runs on `localhost` (127.0.0.1) and port 6379. No password is required for the local development setup.

In your `.env` file or environment variables, set:

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1 # Use database 1 for development
```
