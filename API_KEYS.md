# API Keys Setup Guide

RCE MCP works out of the box with 5 free sources (Wikipedia, Wikidata, DuckDuckGo, arXiv, Local filesystem). Three additional sources require API keys for access.

## Quick Start

Run the interactive setup wizard:

```bash
python -m rce_mcp.setup
```

Or check connectivity without interaction:

```bash
python -m rce_mcp.setup --check
```

---

## 1. GitHub Token (`GITHUB_TOKEN`)

**Source:** GitHub code search, issue/PR search  
**Rate limit:** 5,000 requests/hour with token (60 without)  
**Cost:** Free  

### How to create a token

1. Go to [GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Set a descriptive name: `rce-mcp`
4. Select scopes: `public_repo` (for public repos) or `repo` (for private repos)
5. Click **"Generate token"**
6. Copy the token (starts with `ghp_`)

### Set it

```bash
# Temporary (current session)
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"

# Persistent (add to your shell rc)
echo 'export GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"' >> ~/.bashrc
source ~/.bashrc
```

---

## 2. Context7 API Key (`CONTEXT7_API_KEY`)

**Source:** Library/framework documentation search  
**Rate limit:** Varies by plan  
**Cost:** Varies (free tier available)

### How to get a key

1. Go to [Context7](https://context7.com)
2. Create an account or sign in
3. Navigate to **API Keys** in your dashboard
4. Create a new API key
5. Copy the key

### Set it

```bash
# Temporary
export CONTEXT7_API_KEY="YOUR_CONTEXT7_API_KEY_HERE"

# Persistent
echo 'export CONTEXT7_API_KEY="YOUR_CONTEXT7_API_KEY_HERE"' >> ~/.bashrc
source ~/.bashrc
```

---

## 3. Stack Exchange API Key (`STACKEXCHANGE_KEY`)

**Source:** Programming Q&A (Stack Overflow, Super User, etc.)  
**Rate limit:** 10,000 requests/day with key (300 without)  
**Cost:** Free  

### How to register

1. Go to [Stack Apps → Register an Application](https://stackapps.com/apps/oauth/register)
2. Fill in the form:
   - **Application Name:** `RCE MCP`
   - **Application Website:** `https://github.com/user/rce-mcp`
   - **OAuth Domain:** (leave blank)
   - **Client ID:** (auto-generated)
3. Check **"Enable Client Side OAuth Flow"** if prompted
4. Click **"Register application"**
5. Your **Key** will be displayed on the application page

### Set it

```bash
# Temporary
export STACKEXCHANGE_KEY="YOUR_STACKEXCHANGE_KEY_HERE"

# Persistent
echo 'export STACKEXCHANGE_KEY="YOUR_STACKEXCHANGE_KEY_HERE"' >> ~/.bashrc
source ~/.bashrc
```

---

## Security Best Practices

- **Never commit API keys** to version control. Use `.env` files (add to `.gitignore`) or MCP client env config.
- **Use minimal scopes** — only grant the permissions each source actually needs.
- **Rotate keys regularly** — regenerate tokens periodically and update your config.
- **Monitor usage** — check API dashboards for unusual activity.
- **Revoke compromised keys immediately** — each platform allows instant revocation.

## Environment Variables Summary

| Variable | Source | Required | Free? |
|----------|--------|----------|-------|
| `GITHUB_TOKEN` | GitHub | No (lower limits without) | Yes |
| `CONTEXT7_API_KEY` | Context7 | Yes (source disabled without) | Free tier |
| `STACKEXCHANGE_KEY` | Stack Exchange | No (lower limits without) | Yes |

## Troubleshooting

### "Source skipped: no API key configured"

This is normal — sources without keys are silently disabled. Set the corresponding environment variable to enable them.

### "GitHub token rejected: 401"

Your token may have expired or been revoked. Generate a new one from GitHub Settings.

### "Stack Exchange key rejected"

Ensure you registered the key at Stack Apps and it matches exactly. Keys are long hex strings.

### Verify connectivity

```bash
python -m rce_mcp.setup --check
# Or with JSON output:
python -m rce_mcp.setup --check --json
```
