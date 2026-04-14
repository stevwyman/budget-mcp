FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py .

# Expose the HTTP/SSE port
EXPOSE 8080

ENTRYPOINT ["python", "mcp_server.py"]