# Server Stack Setup

## What's Here
`docker-compose.yml` — the always-on stack: Jellyfin (media), Nextcloud (your files), Portainer (a web UI to manage all of it). These start together and stay running.

**The MCP server is NOT in this file, on purpose.** It runs over stdio — an MCP client (Antigravity, Claude Desktop) launches it on-demand when it wants to ask the vault something, it doesn't sit listening in the background like the other three. Keep using the `ai-os-mcp/` folder's own `docker-compose.yml` from before, placed as a sibling folder to this one. Nothing changes there — this file is additive, not a replacement.

## Run It
```bash
mkdir -p jellyfin/config jellyfin/cache nextcloud/data portainer/data
docker compose up -d
```

Then, before anything else:
1. Edit the `/path/to/your/media` line in `docker-compose.yml` to point at wherever your external USB drive actually mounts.
2. Jellyfin setup wizard: `http://<server-ip>:8096`
3. Nextcloud first-run: `http://<server-ip>:8080`
4. Portainer first-run: `http://<server-ip>:9000`

## Reaching It From Your Phone
This is exactly what Tailscale (already installed) is for — once it's connected, use the server's Tailscale IP instead of its local network IP, and these URLs work from anywhere, including your dad's place. No port-forwarding, no exposing anything to the open internet.

## Not Done Here
Media folder path is a placeholder — has to be set to your real mount point before Jellyfin can see anything. Nextcloud is running on SQLite by default (fine for one person); if it ever feels slow, migrating to a real database (MariaDB) is the next step, not needed yet.
