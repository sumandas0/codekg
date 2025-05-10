# Docker Services Documentation

This directory contains Docker Compose configuration for running various graph database services.

## Available Services

The `docker-compose.yaml` file configures the following services:

### Memgraph

- **Image**: `memgraph/memgraph-mage:latest`
- **Ports**: 
  - `7687:7687` - Bolt protocol for graph database connections
  - `7444:7444` - HTTP API
- **Details**: 
  - Memgraph is a high-performance, in-memory graph database optimized for real-time analytics and transactional workloads
  - MAGE (Memgraph Advanced Graph Extensions) is included in this image

### Memgraph Lab

- **Image**: `memgraph/lab:latest`
- **Ports**: `3000:3000` - Web interface
- **Dependencies**: Requires the Memgraph service to be running
- **Environment**:
  - `QUICK_CONNECT_MG_HOST=memgraph` - Host name of the Memgraph service
  - `QUICK_CONNECT_MG_PORT=7687` - Port of the Memgraph service
- **Details**: Memgraph Lab is a web-based UI for visualizing and querying Memgraph databases

### KuzuDB Explorer

- **Image**: `kuzudb/explorer:latest`
- **Ports**: `8000:8000` - Web interface
- **Volumes**: 
  - `/Users/suman/suman/projects/codekg/kuzudb_data:/database` - Maps the local KuzuDB data directory to the container
- **Details**: 
  - KuzuDB Explorer provides a web interface for exploring and querying KuzuDB graph databases
  - Directly accesses database files mounted from the host system

## Usage Instructions

### Starting All Services

```bash
cd /Users/suman/suman/projects/codekg
docker-compose -f docker/docker-compose.yaml up
```

### Starting Specific Services

To start only the KuzuDB Explorer:

```bash
docker-compose -f docker/docker-compose.yaml up kuzudb-explorer
```

To start only Memgraph and Lab:

```bash
docker-compose -f docker/docker-compose.yaml up memgraph lab
```

### Stopping Services

To stop all running services:

```bash
docker-compose -f docker/docker-compose.yaml down
```

## Accessing Services

- **Memgraph Lab**: http://localhost:3000
- **KuzuDB Explorer**: http://localhost:8000
- **Memgraph API**: http://localhost:7444

## Data Persistence

- **KuzuDB**: Data is stored in the `/Users/suman/suman/projects/codekg/kuzudb_data` directory on the host
- **Memgraph**: Data is ephemeral by default in this configuration

## Troubleshooting

### Docker is not installed or not in PATH

If you encounter errors related to Docker not being found:
1. Ensure Docker Desktop is installed: https://docs.docker.com/desktop/install/mac-install/
2. Make sure Docker Desktop is running
3. Verify Docker is in your PATH by running `which docker`

### Image Pull Errors

If you encounter "access denied" errors when pulling images:
1. Ensure you're connected to the internet
2. Try manually pulling the image: `docker pull kuzudb/explorer:latest`
3. Check Docker Hub status if issues persist 