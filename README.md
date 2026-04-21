# agent-environment

Scripts and configuration for authenticating as a GitHub App to obtain short-lived installation tokens, used as a git credential helper.

## How it works

`get-token.sh` is registered as a git credential helper in `~/.gitconfig`. On every `git push` or `git pull`, git invokes the helper. `get-token.sh` runs `token-gen.py`, which:

1. Reads the GitHub App credentials from `config/environment.json`
2. Signs a short-lived JWT with the App's private key
3. Calls the GitHub API to retrieve the installation ID
4. Exchanges the JWT for a short-lived installation access token
5. Prints `username=x-access-token` and `password=<token>` — the format git expects

No token is stored on disk. A fresh one is generated on every git operation. If anything goes wrong (missing config, bad key, API error), an error is printed to stderr and git surfaces it as a clear failure message.

## Setup

Before running the install script, download a private key from your GitHub App's settings page and place it inside the `config/` folder (you may need to create it first):

```bash
mkdir -p config
cp ~/Downloads/your-private-key.pem config/private-key.pem
```

Then run the install script from the repo root:

```bash
./install.sh
```

The script will walk you through the following steps interactively:

1. Verify it is being run from the correct directory
2. Create `config/` if it does not already exist
3. Ask for your GitHub App **Client ID** (found on the App's settings page)
4. Ask for the **private key filename** inside `config/` and verify it exists
5. Write `config/environment.json` and ask you to confirm the contents
6. Apply secure permissions (`chmod 700` on `config/`, `chmod 600` on the key and JSON)
7. Register the credential helper in `~/.gitconfig` scoped to `https://github.com`
8. Run a smoke test to confirm a token can be obtained end-to-end

### Why scoped to `https://github.com`?

A global `credential.helper` fires for every remote regardless of host — GitHub, GitLab, Bitbucket, self-hosted servers, everything. Any other credential helpers you have configured would be silently overridden.

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

## Manual config reference

If you need to set up or modify `config/environment.json` by hand:

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

Permissions should be set as follows:

```bash
chmod 700 config/
chmod 600 config/private-key.pem
chmod 600 config/environment.json
```

## File structure

```
agent-environment/
├── get-token.sh       # Credential helper entry point (called by git)
├── token-gen.py       # Generates the installation token via GitHub API
├── install.sh         # Interactive setup script
├── .gitignore         # Excludes config/ from version control
├── README.md
└── config/            # NOT committed — created by install.sh
    ├── environment.json   # GitHub App client_id + private key path
    └── private-key.pem    # GitHub App private key (downloaded from App settings)
```
