#!/usr/bin/env python3
"""
End-to-end: generate a carousel PDF from a spec, push PDF+thumbnail to the
GitHub repo (for a stable public URL), then create a Buffer draft post on
the given LinkedIn channel with the document (carousel) attached.

Usage:
    python3 post_carousel.py spec.json "<caption text for the LinkedIn post>" <channel_id>

Requires:
    ~/.secrets/github_token   - GitHub PAT with Contents: Read and write on the repo
    ~/.secrets/buffer_token   - Buffer API access token

Prints a JSON result with keys: ok, post_id, pdf_url, thumbnail_url (or an error).
"""
import sys
import os
import json
import base64
import subprocess
import datetime

# IMPORTANT: Buffer silently promotes shareMode="addToQueue" drafts to a real
# scheduled slot in the background (observed: a draft created with
# saveToDraft=true + mode=addToQueue flipped to status="scheduled" with a
# real dueAt about 20 minutes later, with no further API calls involved).
# To guarantee a draft never auto-publishes before Samy reviews it, we always
# use mode="customScheduled" with a due date far in the future instead.
FAR_FUTURE_DUE_AT = (datetime.datetime.utcnow() + datetime.timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

HOME = os.path.expanduser("~")
GITHUB_TOKEN_PATH = os.path.join(HOME, ".secrets", "github_token")
BUFFER_TOKEN_PATH = os.path.join(HOME, ".secrets", "buffer_token")
GITHUB_OWNER = "Samyyusif"
GITHUB_REPO = "samy-linkedin-carousels"
GITHUB_BRANCH = "main"


def read_token(path):
    with open(path) as f:
        return f.read().strip()


def github_upload(local_path, repo_path, token):
    """Upload a local file to the GitHub repo via Contents API. Returns the raw.githubusercontent.com URL."""
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("ascii")
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{repo_path}"
    payload = json.dumps({
        "message": f"add {repo_path}",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    })
    result = subprocess.run(
        ["curl", "-s", "-X", "PUT",
         "-H", f"Authorization: Bearer {token}",
         "-H", "Accept: application/vnd.github+json",
         url, "-d", "@-"],
        input=payload, capture_output=True, text=True,
        env={**os.environ, "https_proxy": "", "HTTPS_PROXY": "", "http_proxy": "", "HTTP_PROXY": ""},
    )
    data = json.loads(result.stdout)
    if "content" not in data:
        raise RuntimeError(f"GitHub upload failed for {repo_path}: {data}")
    return f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{repo_path}"


def buffer_create_document_post(text, channel_id, pdf_url, thumb_url, title, token):
    mutation = """
    mutation CreateCarouselDraft($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id text status } }
        ... on MutationError { message }
      }
    }
    """
    variables = {
        "input": {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": FAR_FUTURE_DUE_AT,
            "saveToDraft": True,
            "assets": [
                {"document": {"url": pdf_url, "title": title, "thumbnailUrl": thumb_url}}
            ],
        }
    }
    payload = json.dumps({"query": mutation, "variables": variables})
    result = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "-H", "Content-Type: application/json",
         "-H", f"Authorization: Bearer {token}",
         "https://api.buffer.com", "-d", "@-"],
        input=payload, capture_output=True, text=True,
        env={**os.environ, "https_proxy": "", "HTTPS_PROXY": "", "http_proxy": "", "HTTP_PROXY": ""},
    )
    return json.loads(result.stdout)


def main():
    spec_path, caption, channel_id = sys.argv[1], sys.argv[2], sys.argv[3]
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(tools_dir, "out")

    gen = subprocess.run(
        ["python3", os.path.join(tools_dir, "generate_carousel.py"), spec_path, out_dir],
        capture_output=True, text=True,
    )
    if gen.returncode != 0:
        print(json.dumps({"ok": False, "stage": "generate", "error": gen.stderr[-4000:]}))
        sys.exit(1)
    gen_data = json.loads(gen.stdout.strip().splitlines()[-1])
    pdf_local = gen_data["pdf"]
    thumb_local = gen_data["thumbnail"]

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    slug = spec.get("slug", "carousel")
    # LinkedIn shows this as the document title above the carousel. Strip the
    # <hot> accent markup, which is presentation-only.
    title = spec.get("cover", {}).get("headline", slug)
    title = title.replace("<hot>", "").replace("</hot>", "").strip()

    gh_token = read_token(GITHUB_TOKEN_PATH)
    pdf_repo_path = f"carousels/{slug}.pdf"
    thumb_repo_path = f"carousels/{slug}-cover.png"
    try:
        pdf_url = github_upload(pdf_local, pdf_repo_path, gh_token)
        thumb_url = github_upload(thumb_local, thumb_repo_path, gh_token)
    except RuntimeError as e:
        print(json.dumps({"ok": False, "stage": "github_upload", "error": str(e)}))
        sys.exit(1)

    buf_token = read_token(BUFFER_TOKEN_PATH)
    result = buffer_create_document_post(caption, channel_id, pdf_url, thumb_url, title, buf_token)

    post = (result.get("data") or {}).get("createPost") or {}
    if post.get("post"):
        print(json.dumps({
            "ok": True,
            "post_id": post["post"]["id"],
            "status": post["post"]["status"],
            "pdf_url": pdf_url,
            "thumbnail_url": thumb_url,
        }))
    else:
        print(json.dumps({"ok": False, "stage": "buffer_create", "error": result}))
        sys.exit(1)


if __name__ == "__main__":
    main()
