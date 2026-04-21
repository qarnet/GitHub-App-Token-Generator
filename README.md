# agent-environment

Scripts and configuration for authenticating as a GitHub App to obtain short-lived installation tokens, used as a git credential helper.

## How it works

`get-token.sh` is registered as a git credential helper in `~/.gitconfig`:

```ini
[credential]
    helper = /path/to/get-token.sh
```

On every `git push` or `git pull`, git invokes the helper. `get-token.sh` runs `qarnet-token-gen.py`, which:

1. Reads the GitHub App credentials from `config/environment.json`
2. Signs a short-lived JWT with the App's private key
3. Calls the GitHub API to retrieve the installation ID
4. Exchanges the JWT for a short-lived installation access token
5. Prints `username=x-access-token` and `password=<token>` — the format git expects

No token is stored on disk. A fresh one is generated on every git operation.

## Setup

### 1. Create the config folder

The `config/` folder is excluded from version control via `.gitignore`. Create it manually:

```bash
mkdir config
```

### 2. Add `environment.json`

Create `config/environment.json` with the following structure:

```json
{
  "client_id": "<your-github-app-client-id>",
  "private_key_path": "config/private-key.pem"
}
```

| Key | Description |
|---|---|
| `client_id` | The Client ID of your GitHub App (found under the App's settings page) |
| `private_key_path` | Path to the private key file — relative or absolute |

### 3. Add the private key

Download a private key from your GitHub App's settings page and save it as:

```
config/private-key.pem
```

The file should be a standard RSA private key in PEM format (begins with `-----BEGIN RSA PRIVATE KEY-----`).

### 4. Register the credential helper

Run the following command, replacing the path with the actual location of your clone:

```bash
git config --global credential.helper '/absolute/path/to/agent-environment/get-token.sh'
```

For example, if cloned to `~/claude/agent-environment`:

```bash
git config --global credential.helper '/home/karnet-dev-station/claude/agent-environment/get-token.sh'
```

This adds the following to `~/.gitconfig`:

```ini
[credential]
    helper = /home/karnet-dev-station/claude/agent-environment/get-token.sh
```

To verify it was registered correctly:

```bash
git config --global credential.helper
```

## File structure

```
agent-environment/
├── get-token.sh          # Credential helper entry point (called by git)
├── qarnet-token-gen.py   # Generates the installation token via GitHub API
├── .gitignore            # Excludes config/ from version control
├── README.md
└── config/               # NOT committed — create manually
    ├── environment.json  # GitHub App client_id + private key path
    └── private-key.pem   # GitHub App private key (downloaded from App settings)
```
