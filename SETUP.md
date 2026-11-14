# H2AI Instagram auto-publisher: one-time setup

This repository publishes @h2ai.codelab's remaining posts (Topics 10–26, Reels and
carousels) **from GitHub's servers**, every day at 19:00 IST, with your laptop off.
It also adds the quiz-answer comment about 24 hours after each post.

You do steps 1–6 once (about 30–45 minutes). Claude does the upload part (step 2).

---

## 1. Create a free GitHub account
1. Go to **https://github.com/signup** and create an account (free plan).
2. Verify your email.

## 2. Create the repository (Claude uploads the files)
1. Go to **https://github.com/new**.
2. Repository name: **`h2ai-instagram`**. Choose **Public** (needed so Instagram can fetch the images and videos). Don't add a README.
3. Click **Create repository**.
4. Tell Claude your GitHub username. Claude pushes this folder from your PC. A browser window opens once asking you to **sign in to GitHub and authorise Git**; click Authorise.

## 3. Turn on GitHub Pages (hosts the media)
1. In the repo: **Settings → Pages**.
2. Source: **Deploy from a branch**. Branch: **main**, folder: **/docs**. Click **Save**.
3. After 1–2 minutes, `https://<your-username>.github.io/h2ai-instagram/` shows "Media host for @h2ai.codelab posts."

## 4. Create the Instagram API token (Meta)
@h2ai.codelab must be a **Professional (Creator or Business)** account (it already is).
1. Go to **https://developers.facebook.com/** and log in (Meta asks for a Facebook login to register as a developer, which is free).
2. **My Apps → Create app**. Choose the use case **"Manage messaging & content on Instagram"** (Instagram API). App name: `H2AI Publisher`. Finish creating it.
3. Open **Instagram → API setup with Instagram login**.
4. Under **Generate access tokens**, click **Add account** and log in as **@h2ai.codelab**. Allow the permissions:
   `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_comments`.
5. Click **Generate token** next to h2ai.codelab and **copy the token**. Treat it like a password: don't share it in chat.

> The app can stay in *Development* mode: it only posts to your own account.

## 5. Save the token in GitHub
1. In the repo: **Settings → Secrets and variables → Actions → New repository secret**.
2. Name: **`IG_ACCESS_TOKEN`**. Value: paste the token. **Add secret**.

## 6. Let the token renew itself (only for tokens that expire)
**Skip this step if your token starts with `EAA`.** That's a never-expiring system-user token, created via
"API setup with Unified login" → *Create new configuration* (System-user access token, Expiration: Never),
which is what @h2ai.codelab uses. The refresh workflow detects it and does nothing.

Only for `IGAA…` tokens, which last 60 days: a weekly workflow renews the token, but it needs permission to save the new one:
1. Go to **https://github.com/settings/personal-access-tokens/new**.
2. Name `h2ai token refresher`, Expiration **1 year** (or the longest offered), Repository access **Only select repositories → h2ai-instagram**.
3. Permissions → Repository permissions → **Secrets: Read and write**. **Generate token** and copy it.
4. Add it as another repository secret named **`GH_PAT`** (same place as step 5).

## 7. Test it
1. Repo → **Actions** tab. If asked, click **"I understand my workflows, go ahead and enable them"**.
2. **Publish to Instagram → Run workflow**, mode **check** → it logs in with the token and lists recent posts, **publishing nothing**. Green tick and "Token works" in the log = ready.
3. (Optional) mode **dry-run** shows what today's run would publish.
4. Never pick mode **publish** by hand unless you want today's post to go out right now. The daily schedule does that automatically.

Done. From here it runs on its own. GitHub emails you if a run ever fails.

---

### How it works
- `posts.json`: the 34 remaining posts (date, caption, media). Times are 19:00 IST.
- `comments.json`: the quiz answers. They're posted on any matching post (including ones scheduled in Business Suite) 20+ hours after it goes live.
- `publish.py`: runs daily. It publishes today's post (or catches up to 3 days late) and never duplicates a post that's already on the account.
- `state/state.json`: what has been published and commented. The workflow updates it.
- `docs/media/`: JPEG slides, Reel videos and covers, served by GitHub Pages.

To change a caption or date: edit `posts.json` on GitHub (pencil icon) and commit.
Limits: Instagram's API can't pin comments or add music, so do those in the app if you want them.
