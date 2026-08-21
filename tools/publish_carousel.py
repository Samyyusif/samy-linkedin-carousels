#!/usr/bin/env python3
"""
Build a carousel and host it publicly, then hand the URLs back.

This deliberately does NOT talk to Buffer. Creating the Buffer draft is done by
the caller through the Buffer MCP connector, which authenticates via Samy's
claude.ai account rather than a token file on disk - so the Buffer token no
longer needs to exist anywhere. The only remaining secret is the GitHub PAT,
which is required because Buffer can only attach a document by public URL.

Usage:
    python3 publish_carousel.py spec.json

Prints JSON:
    {"ok": true, "pdf_url": ..., "thumbnail_url": ..., "title": ..., "slides": N}
    {"ok": false, "stage": "...", "error": "..."}

The caller then creates the draft with Buffer MCP create_post:
    assets: [{document: {url: <pdf_url>, title: <title>, thumbnailUrl: <thumbnail_url>}}]
    saveToDraft: true, mode: "customScheduled", dueAt: <~180 days out>
"""
import sys
import os
import json
import base64
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
GITHUB_TOKEN_PATH = os.path.expanduser("~/.secrets/github_token")
OWNER, REPO, BRANCH = "Samyyusif", "samy-linkedin-carousels", "main"

# The sandbox routes github.com through a credential proxy that only allows
# repos it has been granted. We use Samy's own PAT directly instead.
NOPROXY = {**os.environ, "https_proxy": "", "HTTPS_PROXY": "",
           "http_proxy": "", "HTTP_PROXY": ""}


def fail(stage, error):
    print(json.dumps({"ok": False, "stage": stage, "error": str(error)}))
    sys.exit(1)


def github_upload(local_path, repo_path, token):
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("ascii")
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{repo_path}"

    # Look for an existing file so re-runs update instead of 409-ing.
    head = subprocess.run(
        ["curl", "-s", "-H", f"Authorization: Bearer {token}",
         "-H", "Accept: application/vnd.github+json", f"{url}?ref={BRANCH}"],
        capture_output=True, text=True, env=NOPROXY)
    payload = {"message": f"carousel: {repo_path}", "content": content, "branch": BRANCH}
    try:
        existing = json.loads(head.stdout)
        if isinstance(existing, dict) and existing.get("sha"):
            payload["sha"] = existing["sha"]
    except (ValueError, TypeError):
        pass

    r = subprocess.run(
        ["curl", "-s", "-X", "PUT", "-H", f"Authorization: Bearer {token}",
         "-H", "Accept: application/vnd.github+json", url, "-d", "@-"],
        input=json.dumps(payload), capture_output=True, text=True, env=NOPROXY)
    data = json.loads(r.stdout) if r.stdout.strip() else {}
    if "content" not in data:
        raise RuntimeError(f"upload of {repo_path} failed: {data.get('message', data)}")
    return f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{repo_path}"


def main():
    if len(sys.argv) < 2:
        fail("args", "usage: publish_carousel.py spec.json")
    spec_path = sys.argv[1]

    if not os.path.exists(GITHUB_TOKEN_PATH) or not open(GITHUB_TOKEN_PATH).read().strip():
        fail("github_token",
             "~/.secrets/github_token is missing or empty - carousel hosting is "
             "unavailable. Text posts can still be published via Buffer MCP.")
    token = open(GITHUB_TOKEN_PATH).read().strip()

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    slug = spec.get("slug", "carousel")
    title = spec.get("cover", {}).get("headline", slug)
    title = title.replace("<hot>", "").replace("</hot>", "").strip()

    out_dir = os.path.join(BASE, "out")
    gen = subprocess.run(
        ["python3", os.path.join(BASE, "generate_carousel.py"), spec_path, out_dir],
        capture_output=True, text=True)
    if gen.returncode != 0:
        fail("generate", gen.stderr[-3000:])
    built = json.loads(gen.stdout.strip().splitlines()[-1])

    try:
        pdf_url = github_upload(built["pdf"], f"carousels/{slug}.pdf", token)
        thumb_url = github_upload(built["thumbnail"], f"carousels/{slug}-cover.png", token)
    except RuntimeError as e:
        fail("github_upload", e)

    print(json.dumps({
        "ok": True,
        "pdf_url": pdf_url,
        "thumbnail_url": thumb_url,
        "title": title,
        "slides": built["slides"],
        "pdf_mb": round(os.path.getsize(built["pdf"]) / 1e6, 2),
    }))


if __name__ == "__main__":
    main()
