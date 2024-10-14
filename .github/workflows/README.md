# Deployment Workflows

This directory contains GitHub Actions workflows for deploying our application to development and production environments using a self-hosted runner.

## Workflows

1. `deploy-dev.yml`: Deploys to the development environment
2. `deploy-prod.yml`: Deploys to the production environment

## Prerequisites

Before using these workflows, ensure the following are set up:

1. A macOS machine (Sonoma 14.2) with Docker Desktop installed
2. GitHub Actions self-hosted runner installed and configured
3. Necessary environment variables set on the host machine

## Workflow Details

### Development Deployment (`deploy-dev.yml`)

- Triggered on pushes to the `develop` branch
- Deploys to the development environment
- Uses `docker-compose-dev.yml` for container orchestration
- Health check on `http://localhost:5000/health`

### Production Deployment (`deploy-prod.yml`)

- Triggered on pushes to the `main` branch
- Deploys to the production environment
- Uses `docker-compose.yml` for container orchestration
- Health check on `http://localhost:5001/health`

## Deployment Process

Both workflows follow these steps:

1. Check out the code
2. Navigate to the project directory
3. Pull the latest changes
4. Build and start Docker containers
5. Perform a health check
6. Rollback if the health check fails

## GitHub Actions Self-Hosted Runner Management

### Starting the Runner
```bash
cd /path/to/actions-runner
./run.sh
```

### Installing the Runner as a Service
```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

### Stopping the Runner Service
```bash
sudo ./svc.sh stop
```

### Uninstalling the Runner Service
```bash
sudo ./svc.sh uninstall
```

### Checking Runner Status
```bash
sudo ./svc.sh status
```

### Viewing Runner Logs
```bash
tail -f /var/log/syslog | grep runner
```

### Updating the Runner
```bash
cd /path/to/actions-runner
./run.sh
```

### Useful Commands

1. List all runners:
   ```
   gh api -X GET repos/{owner}/{repo}/actions/runners
   ```

2. Check runner application version:
   ```
   ./run.sh --version
   ```

3. Configure runner without prompts:
   ```
   ./config.sh --url https://github.com/[OWNER]/[REPO] --token [TOKEN]
   ```

## Troubleshooting

If deployments fail:

1. Check the GitHub Actions logs in the GitHub repository
2. Verify that the self-hosted runner is online and connected
3. Ensure Docker and docker-compose are properly installed and running
4. Check the project path in the workflow files matches the actual path on the runner machine

## Security Notes

- Regularly update the runner application
- Keep the runner machine's operating system and Docker up to date
- Limit access to the runner machine
- Use repository restrictions for self-hosted runners to limit which repositories can use the runner

## Customization

To modify the deployment process:

1. Edit the respective YAML file (`deploy-dev.yml` or `deploy-prod.yml`)
2. Adjust paths or commands as needed
3. Test changes in a safe environment before applying to the main workflow

For any questions or issues, please contact the DevOps team.