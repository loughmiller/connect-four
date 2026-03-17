FROM python:3-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gh \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --root-user-action=ignore \
    flask pytest pytest-cov

ARG CLAUDE_CODE_VERSION=latest
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

RUN useradd -m -s /bin/bash claude

COPY tools/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /work
RUN chown claude:claude /work

USER claude

CMD ["/usr/local/bin/entrypoint.sh"]
