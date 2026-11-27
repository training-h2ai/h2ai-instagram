# H2AI Instagram Publisher

Automated publishing for the **@h2ai.codelab** Instagram account.

A scheduled GitHub Actions workflow posts each day's Reel at **19:00 IST** and adds the
quiz-answer comment about a day later. It runs entirely on GitHub's servers.

## How it works

| Part | What it does |
|---|---|
| `posts.json` | The schedule: date, time, caption and media for each post |
| `comments.json` | Quiz answers, added as a comment ~24 hours after a post |
| `publish.py` | Publishes today's post, catches up to 3 days late, never posts twice |
| `state/state.json` | Record of what has been published and commented (updated by the workflow) |
| `docs/media/` | Reel videos, covers and slides, served through GitHub Pages |
| `.github/workflows/` | Daily publish job and weekly token check |

## Common tasks

- **Change a caption or date:** edit `posts.json` and commit.
- **Test without posting:** Actions → *Publish to Instagram* → Run workflow → mode `check` or `dry-run`.
- **First-time setup or a new token:** see [SETUP.md](SETUP.md).

The Instagram access token is stored as a GitHub Actions secret and is never committed to this repository.
