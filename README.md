# GitHub-App-Token-Generator

Scripts and configuration for authenticating as a GitHub App to obtain short-lived installation tokens, used as a git credential helper.

## How it works

`get-token.sh` is registered as a git credential helper in `~/.gitconfig`. On every `git push` or `git pull`, git invokes the helper. `get-token.sh` runs `token-gen.py`, which:

1. Checks `~/.cache/github-app-token-generator/token.json` — if a valid token exists with more than 5 minutes remaining, it is used immediately with no API calls
2. Otherwise: reads `config/environment.json`, signs a short-lived JWT with the App's private key, fetches a new installation token from the GitHub API, writes it to the cache, and prints the credentials

GitHub installation tokens are valid for 1 hour. The cache means the API is only called when a token actually needs refreshing — roughly once per hour regardless of how many git operations happen in that window.

If anything goes wrong (missing config, bad key, API error), an error is printed to stderr and git surfaces it as a clear failure message.

## Setup

The install script requires Python 3 and the following packages:

```bash
pip3 install requests PyJWT cryptography
```

`cryptography` is a separate dependency required by PyJWT to handle RS256 signing — it is not pulled in automatically.

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

1. Verify it is being run from the correct directory and that Python dependencies are present
2. Create `config/` if it does not already exist
3. Ask for your GitHub App **Client ID** (found on the App's settings page)
4. Ask for the **private key filename** inside `config/` and verify it exists
5. Write `config/environment.json` and ask you to confirm the contents
6. Discover installations for the GitHub App — auto-selects if there is only one; prompts you to choose if there are multiple; caches the result so the API is not called on every git operation
7. Apply secure permissions (`chmod 700` on `config/`, `chmod 600` on the key and JSON, `chmod 750` on `get-token.sh`)
8. Register the credential helper in `~/.gitconfig` scoped to `https://github.com`
9. Run a smoke test to confirm a token can be obtained end-to-end

### Why scoped to `https://github.com`?

A global `credential.helper` fires for every remote regardless of host — GitHub, GitLab, Bitbucket, self-hosted servers, everything. Any other credential helpers you have configured would be silently overridden.

Scoping with `credential.https://github.com.helper` makes the helper activate only when git is authenticating against `https://github.com`. For any other host, git falls through to the next configured helper or prompts you normally. This lets you stack independent helpers per host:

```ini
[credential "https://github.com"]
    helper = /path/to/GitHub-App-Token-Generator/get-token.sh   # GitHub App token

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
GitHub-App-Token-Generator/
├── get-token.sh               # Credential helper entry point (called by git)
├── token-gen.py               # Fetches token (cached) and prints credentials
├── discover-installation.py   # Interactive installation selector (called by install.sh)
├── install.sh                 # Interactive setup wizard
├── .gitignore                 # Excludes config/ from version control
├── README.md
├── config/                    # NOT committed — created by install.sh
│   ├── environment.json       # GitHub App client_id + private key path
│   └── private-key.pem        # GitHub App private key (downloaded from App settings)
└── ~/.cache/github-app-token-generator/    # Created automatically by token-gen.py
    └── token.json                 # Cached token + expiry + installation_id
```

To clear the token cache (forces a fresh token on next git operation):

```bash
rm ~/.cache/github-app-token-generator/token.json
```
