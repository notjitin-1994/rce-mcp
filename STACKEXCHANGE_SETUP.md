# Stack Exchange Setup Guide

RCE MCP can search Stack Exchange sites (Stack Overflow, Super User, Server Fault, etc.) for programming Q&A. This guide walks you through registering for an API key.

## Do You Need a Key?

**No.** The Stack Exchange source works without an API key. However:

| Without Key | With Key |
|-------------|----------|
| 300 requests/day | 10,000 requests/day |
| Cross-site requests limited | Full cross-site access |

If you're a light user, you can skip this entirely. The source will still work.

## Step-by-Step Registration

### 1. Create a Stack Apps Application

1. Sign in to [Stack Apps](https://stackapps.com/) using your Stack Exchange account
2. Click **"Register an Application"** at the top
3. Fill in the form:

   | Field | Value |
   |-------|-------|
   | Application Name | `RCE MCP` (or any name you like) |
   | Application Website | `https://github.com/user/rce-mcp` |
   | OAuth 2.0 Redirect URI | *(leave blank)* |
   | Client ID | *(auto-generated)* |
   | Client Secret | *(auto-generated)* |

4. Under **"Support"**, check the box for your desired sites
5. Click **"Register application"**

### 2. Copy Your Key

After registration, you'll see your application details page. Look for the **Key** field — this is your API key. It will be a long hex string.

### 3. Set the Environment Variable

```bash
# Add to your shell configuration (~/.bashrc, ~/.zshrc, etc.)
export STACKEXCHANGE_KEY="YOUR_STACKEXCHANGE_KEY_HERE"

# Reload
source ~/.bashrc  # or ~/.zshrc
```

### 4. Verify

```bash
# Run the RCE setup check
python -m rce_mcp.setup --check

# Or test manually
curl "https://api.stackexchange.com/2.3/info?site=stackoverflow&key=YOUR_STACKEXCHANGE_KEY_HERE"
```

You should see a JSON response with `"quota_remaining"` showing 10,000.

## Configuration with MCP Clients

### OpenClaw

```bash
openclaw mcp set rce-mcp '{
  "command": "uv",
  "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"],
  "env": {
    "STACKEXCHANGE_KEY": "YOUR_STACKEXCHANGE_KEY_HERE"
  }
}'
```

### Claude Code

```bash
claude mcp add rce-mcp -- \
  env STACKEXCHANGE_KEY=YOUR_STACKEXCHANGE_KEY_HERE \
  -- uv --directory /path/to/rce-mcp run rce-mcp
```

### VS Code / Cursor

Add to `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "rce-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"],
      "env": {
        "STACKEXCHANGE_KEY": "YOUR_STACKEXCHANGE_KEY_HERE"
      }
    }
  }
}
```

## Supported Stack Exchange Sites

The source defaults to `stackoverflow` but can search any Stack Exchange site:

| Site | Parameter |
|------|-----------|
| Stack Overflow | `stackoverflow` |
| Server Fault | `serverfault` |
| Super User | `superuser` |
| Ask Ubuntu | `askubuntu` |
| Math | `math` |
| Physics | `physics` |
| English | `english` |
| ...and [170+ more](https://stackexchange.com/sites) | |

To change the default site, set the `RCE_STACKEXCHANGE_SITE` environment variable (future feature — currently hardcoded to `stackoverflow`).

## Rate Limits

- **With key:** 10,000 requests per day
- **Without key:** 300 requests per day
- Both limits reset at 00:00 UTC

Monitor your quota via the API response's `quota_remaining` field.

## Troubleshooting

### "Stack Exchange key rejected"

- Ensure the key is copied exactly (no extra spaces or line breaks)
- Check that the application is still active at [Stack Apps](https://stackapps.com/users/current)
- Try regenerating the key if it's been compromised

### Empty results

- Stack Exchange search requires well-formed queries. Try rephrasing.
- Some niche topics may have better results on specific sites (e.g., `math` for mathematical proofs)
- Check `quota_remaining` — you may have hit the daily limit
