# Deployment Workflows

This directory contains GitHub Actions workflows for deploying our application to development and production environments.

## Workflows

1. `deploy-dev.yml`: Deploys to the development environment
2. `deploy-prod.yml`: Deploys to the production environment

## Prerequisites

Before using these workflows, ensure the following are set up:

1. A macOS machine (Sonoma 14.2) with Docker Desktop installed
2. SSH access to the macOS machine
3. GitHub repository secrets configured (see below)

## GitHub Secrets

The following secrets need to be set in the GitHub repository:

- `MACOS_SSH_PRIVATE_KEY`: The SSH private key for accessing the macOS machine
- `MACOS_HOST_IP`: The IP address of the macOS machine
- `MACOS_USERNAME`: The username for SSH access on the macOS machine

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
2. SSH into the macOS machine
3. Navigate to the project directory
4. Pull the latest changes
5. Build and start Docker containers
6. Perform a health check
7. Rollback if the health check fails

## Rollback Mechanism

If the health check fails after deployment, the workflow will:

1. Reset to the previous commit
2. Rebuild and restart containers with the previous version
3. Log the rollback for review

## Troubleshooting

If deployments fail:

1. Check the GitHub Actions logs for error messages
2. Verify that all secrets are correctly set
3. Ensure the macOS machine is accessible and properly configured
4. Check Docker and docker-compose installations on the macOS machine

## Security Notes

- Keep the SSH private key and other secrets secure
- Regularly rotate SSH keys and review access permissions
- Ensure the macOS machine has proper firewall and security settings

## Customization

To modify the deployment process:

1. Edit the respective YAML file (`deploy-dev.yml` or `deploy-prod.yml`)
2. Adjust environment variables, paths, or commands as needed
3. Test changes in a safe environment before applying to the main workflow

For any questions or issues, please contact the DevOps team.