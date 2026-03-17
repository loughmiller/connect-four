FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3 \
    python3-pip \
    gh \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --root-user-action=ignore \
    flask pytest pytest-cov

ARG CLAUDE_CODE_VERSION=latest
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

COPY tools/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /work

CMD ["/usr/local/bin/entrypoint.sh"]
