FROM node:22-slim

# Claude Code braucht git; ripgrep beschleunigt die Codesuche
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app
COPY bridge.mjs server.mjs ./
RUN mkdir -p /app/space && chown -R node:node /app

# Nicht als root laufen - Claude Code meckert sonst
USER node

# HOST=0.0.0.0 nur hier: im Container muss der Server auf allen Interfaces
# lauschen, damit Docker den Port ueberhaupt weiterreichen kann. Nach aussen
# bindet docker-compose ihn auf 127.0.0.1. Ausserhalb des Containers greift
# server.mjs' eigener Loopback-Default.
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=8080 \
    CLAUDE_CONFIG_DIR=/app/.claude

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD node -e "fetch('http://127.0.0.1:8080/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.mjs"]
