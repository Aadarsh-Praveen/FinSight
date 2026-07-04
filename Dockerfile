# FinSight Cloud Run image: the ADK app + the MCP Toolbox in one container (see PROGRESS.md's
# deploy-architecture notes for why -- keeps the deployed read-only-SQL guarantee identical to
# what Phase 6/9 built and measured, rather than swapping to a more permissive tool layer).
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# MCP Toolbox binary (linux/amd64 -- Cloud Run's default architecture).
ARG TOOLBOX_VERSION=1.6.0
RUN curl -L -o /usr/local/bin/toolbox \
    "https://storage.googleapis.com/mcp-toolbox-for-databases/v${TOOLBOX_VERSION}/linux/amd64/toolbox" \
    && chmod +x /usr/local/bin/toolbox

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY finsight/ ./finsight/
COPY mcp-toolbox/tools.yaml ./mcp-toolbox/tools.yaml
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# The app always talks to the toolbox over localhost, regardless of deploy environment.
ENV TOOLBOX_URL=http://127.0.0.1:5000

ENTRYPOINT ["./entrypoint.sh"]
