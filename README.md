# budget-mcp
a simple MCP server to connect to the budget app

## set-up

```sh
python3 -m venv ../budget-mcp-env
source ../budget-mcp-env/bin/activate
`````

```sh
podman build -f Dockerfile -t budget-mcp:latest --ignorefile .dockerignore
````

```sh
podman compose --file container-compose.yaml up --detach

podman compose --file container-compose.yaml down
````
