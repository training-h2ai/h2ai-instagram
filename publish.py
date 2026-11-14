"""H2AI Code Lab: Instagram auto-publisher (runs on GitHub Actions).

Every run (daily at 19:00 IST):
  1. Publishes any post in posts.json whose date is today (or up to 3 days
     overdue) and that isn't on Instagram yet.
  2. Adds the quiz-answer comment (comments.json) to posts that went live
     20+ hours ago and don't have it yet.
State lives in state/state.json, which the workflow commits back to the repo.

Env vars:
  IG_ACCESS_TOKEN  long-lived Instagram token (Instagram API with Instagram Login)
  MEDIA_BASE_URL   optional; defaults to https://<owner>.github.io/<repo>/
  GITHUB_REPOSITORY  set automatically by GitHub Actions

Local test without touching Instagram:
  python publish.py --dry-run --today 2026-12-14
"""
import argparse, datetime as dt, json, os, pathlib, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
API_VERSION = os.environ.get("IG_API_VERSION", "v25.0")
# Instagram-login tokens (IGAA...) use graph.instagram.com; Facebook / Business-login
# tokens (EAA..., including never-expiring system-user tokens) use graph.facebook.com.
IG_USER_ID = os.environ.get("IG_USER_ID") or "17841452650254696"  # @h2ai.codelab (not secret)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
CATCH_UP_DAYS = 3
COMMENT_AFTER_HOURS = 20
COMMENT_WINDOW_DAYS = 7


def log(*a):
    print(*a, flush=True)


class IG:
    def __init__(self, token):
        self.token = token
        host = "graph.facebook.com" if token.startswith("EAA") else "graph.instagram.com"
        self.api = f"https://{host}/{API_VERSION}"

    def call(self, method, path, **params):
        params["access_token"] = self.token
        data = urllib.parse.urlencode(params).encode()
        url = f"{self.api}/{path}"
        if method == "GET":
            req = urllib.request.Request(url + "?" + data.decode())
        else:
            req = urllib.request.Request(url, data=data, method=method)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")
                if e.code >= 500 and attempt < 2:
                    time.sleep(10)
                    continue
                raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {body}") from None

    def wait_ready(self, container, timeout=600):
        start = time.time()
        while time.time() - start < timeout:
            st = self.call("GET", container, fields="status_code,status").get("status_code")
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {container} status {st}")
            time.sleep(10)
        raise RuntimeError(f"container {container} not ready after {timeout}s")


def load(name, default):
    p = ROOT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_state(state):
    p = ROOT / "state" / "state.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def first_line(text):
    return (text or "").split("\n", 1)[0].strip()


def media_base():
    if os.environ.get("MEDIA_BASE_URL"):
        return os.environ["MEDIA_BASE_URL"].rstrip("/") + "/"
    owner, repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO").split("/")
    return f"https://{owner.lower()}.github.io/{repo}/"


def publish_post(ig, user_id, post, base):
    if post["type"] == "CAROUSEL":
        children = []
        for img in post["images"]:
            c = ig.call("POST", f"{user_id}/media", image_url=base + img, is_carousel_item="true")
            children.append(c["id"])
        for c in children:
            ig.wait_ready(c)
        container = ig.call("POST", f"{user_id}/media", media_type="CAROUSEL",
                            children=",".join(children), caption=post["caption"])["id"]
    else:
        params = dict(media_type="REELS", video_url=base + post["video"], caption=post["caption"],
                      share_to_feed="true")
        if post.get("cover"):
            params["cover_url"] = base + post["cover"]
        container = ig.call("POST", f"{user_id}/media", **params)["id"]
    ig.wait_ready(container)
    return ig.call("POST", f"{user_id}/media_publish", creation_id=container)["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", help="pretend today is YYYY-MM-DD (IST)")
    args = ap.parse_args()

    now = dt.datetime.now(IST)
    today = dt.date.fromisoformat(args.today) if args.today else now.date()
    posts = load("posts.json", [])
    comments = load("comments.json", [])
    state = load("state/state.json", {"published": {}, "commented": {}})
    base = media_base()

    due = [p for p in posts if p["key"] not in state["published"]
           and 0 <= (today - dt.date.fromisoformat(p["date"])).days <= CATCH_UP_DAYS]
    missed = [p["key"] for p in posts if p["key"] not in state["published"]
              and (today - dt.date.fromisoformat(p["date"])).days > CATCH_UP_DAYS]
    upcoming = [p for p in posts if dt.date.fromisoformat(p["date"]) > today]
    log(f"Today {today} (IST). Due: {len(due)}. Upcoming: {len(upcoming)}. Missed: {len(missed)}.")
    if missed:
        log("WARNING: posts missed beyond catch-up window:", missed)

    if args.dry_run:
        for p in due:
            files = p["images"] if p["type"] == "CAROUSEL" else [p["video"], p["cover"]]
            for f in files:
                assert (ROOT / "docs" / f).exists(), f"missing media {f}"
            log(f"[dry-run] would publish {p['key']} ({p['type']}): {first_line(p['caption'])}")
            log(f"          media: {base}{files[0]} (+{len(files)-1} more)")
        nxt = upcoming[0] if upcoming else None
        log(f"[dry-run] next upcoming: {nxt['key'] if nxt else 'none'}")
        return 0

    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        log("ERROR: IG_ACCESS_TOKEN secret is not set.")
        return 1
    ig = IG(token)
    if token.startswith("EAA"):
        user_id = IG_USER_ID
        me = ig.call("GET", user_id, fields="username")
    else:
        me = ig.call("GET", "me", fields="user_id,username")
        user_id = me.get("user_id") or me["id"]
    log(f"Logged in as @{me.get('username')} ({user_id}) via {ig.api.split('/')[2]}")

    recent = ig.call("GET", f"{user_id}/media", fields="id,caption,timestamp", limit=50).get("data", [])
    live_by_line = {first_line(m.get("caption")): m for m in recent}

    failures = 0
    for p in due:
        line = first_line(p["caption"])
        if line in live_by_line:  # already on Instagram (e.g. posted manually); don't duplicate
            log(f"skip {p['key']}: already live as {live_by_line[line]['id']}")
            state["published"][p["key"]] = live_by_line[line]["id"]
            save_state(state)
            continue
        try:
            media_id = publish_post(ig, user_id, p, base)
            state["published"][p["key"]] = media_id
            save_state(state)
            log(f"PUBLISHED {p['key']} -> {media_id}")
        except Exception as e:  # keep going; report at the end
            failures += 1
            log(f"FAILED {p['key']}: {e}")

    # quiz-answer comments
    answers = {c["match"]: c["answer"] for c in comments}
    for m in recent:
        line = first_line(m.get("caption"))
        if line not in answers or m["id"] in state["commented"]:
            continue
        posted = dt.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
        age_h = (dt.datetime.now(dt.timezone.utc) - posted).total_seconds() / 3600
        if age_h < COMMENT_AFTER_HOURS or age_h > COMMENT_WINDOW_DAYS * 24:
            continue
        try:
            existing = ig.call("GET", f"{m['id']}/comments", fields="text,username", limit=50).get("data", [])
            if any(c.get("username") == me.get("username") and "Answer:" in c.get("text", "") for c in existing):
                state["commented"][m["id"]] = "existing"
            else:
                cid = ig.call("POST", f"{m['id']}/comments", message=answers[line])["id"]
                state["commented"][m["id"]] = cid
                log(f"COMMENTED answer on {m['id']} ({line[:40]})")
            save_state(state)
        except Exception as e:
            failures += 1
            log(f"FAILED comment on {m['id']}: {e}")

    save_state(state)
    if failures:
        log(f"{failures} action(s) failed. Check the log above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
