# agent-environment

Scripts and configuration for authenticating as a GitHub App to obtain short-lived installation tokens, used as a git credential helper.

## How it works

`get-token.sh` is registered as a git credential helper in `~/.gitconfig`. On every `git push` or `git pull`, git invokes the helper. `get-token.sh` runs `token-gen.py`, which:

1. Reads the GitHub App credentials from `config/environment.json`
2. Signs a short-lived JWT with the App's private key
3. Calls the GitHub API to retrieve the installation ID
4. Exchanges the JWT for a short-lived installation access token
5. Prints `username=x-access-token` and `password=<token>` — the format git expects

No token is stored on disk. A fresh one is generated on every git operation. If anything goes wrong (missing config, bad key, API error), an error is printed to stderr and git surfaces it as a credential failure.

## Setup

### 1. Create the config folder

The `config/` folder is excluded from version control via `.gitignore`. Create it and lock down its permissions so only your user can read the private key:

```bash
mkdir config
chmod 700 config
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
| `private_key_path` | Path to the private key file — relative to the repo root, or absolute |

### 3. Add the private key

Download a private key from your GitHub App's settings page and save it as `config/private-key.pem`, then restrict its permissions:

```bash
# save the downloaded .pem file as config/private-key.pem, then:
chmod 600 config/private-key.pem
```

The file should be a standard RSA private key in PEM format (begins with `-----BEGIN RSA PRIVATE KEY-----`).

### 4. Register the credential helper

Run the install script from inside the repo:

```bash
./install.sh
```

This registers the credential helper **scoped to `https://github.com`** only, by adding the following to `~/.gitconfig`:

```ini
[credential "https://github.com"]
    helper = /absolute/path/to/agent-environment/get-token.sh
```

To verify it was registered correctly:

```bash
git config --global credential.https://github.com.helper
```

#### Why scoped instead of global?

A global `credential.helper` fires for every remote, regardless of host — GitHub, GitLab, Bitbucket, self-hosted servers, everything. That means this GitHub App token would be sent to all of them, and any other credential helpers you have configured (e.g. a personal PAT for GitLab) would be silently overridden.

Scoping with `credential.https://github.com.helper` makes the helper activate only when git is authenticating against `https://github.com`. For any other host, git falls through to the next configured helper or prompts you normally. This lets you stack independent helpers per host:

```ini
[credential "https://github.com"]
    helper = /path/to/agent-environment/get-token.sh   # GitHub App token

[credential "https://gitlab.com"]
    helper = /path/to/some-other-helper.sh             # different auth

[credential "https://my-internal-server.com"]
    helper = store                                     # plain stored credential
```

Each helper only sees requests for its matching URL prefix and is completely independent of the others.

## File structure

```
agent-environment/
├── get-token.sh       # Credential helper entry point (called by git)
├── token-gen.py       # Generates the installation token via GitHub API
├── install.sh         # Registers the credential helper in ~/.gitconfig
├── .gitignore         # Excludes config/ from version control
├── README.md
└── config/            # NOT committed — create manually
    ├── environment.json   # GitHub App client_id + private key path
    └── private-key.pem    # GitHub App private key (downloaded from App settings)
```
