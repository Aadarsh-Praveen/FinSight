# TODO(Phase 10): flesh out for Cloud Run deploy.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY finsight/ finsight/
COPY mcp-toolbox/ mcp-toolbox/

CMD ["python", "-m", "finsight.agent"]
