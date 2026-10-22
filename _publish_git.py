"""Create GitHub repo and push ozon_analytics using git credential helper."""
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "ozon_analytics"
ORG = "omnysmm"
WORKDIR = Path(r"C:\Users\Alex\ozon_analytics")
PUBLIC = True  # GitHub Pages requires a public repo on free plan


def git_cred():
    p = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=False,
    )
    user = pwd = None
    for line in p.stdout.splitlines():
        if line.startswith("username="):
            user = line.split("=", 1)[1]
        elif line.startswith("password="):
            pwd = line.split("=", 1)[1]
    return user, pwd


def gh_api(token, path, method="GET", body=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body_txt)
        except Exception:
            return e.code, {"message": body_txt[:300]}


def main():
    user, token = git_cred()
    if not user or not token:
        print("NO_CREDS")
        return 1
    print("cred user:", user, "token_len:", len(token))

    # create repo under org (fallback to user)
    body = {"name": REPO, "private": not PUBLIC, "has_issues": True, "has_projects": False}
    status, resp = gh_api(token, f"/orgs/{ORG}/repos", "POST", body)
    if status in (201, 200):
        print("created org repo", resp.get("html_url"))
    elif status == 422 and "already exists" in json.dumps(resp):
        print("repo already exists")
    else:
        print("org create failed", status, resp)
        status, resp = gh_api(token, "/user/repos", "POST", body)
        if status in (201, 200):
            print("created user repo", resp.get("html_url"))
        else:
            print("user create failed", status, resp)
            return 1

    clone_url = f"https://github.com/{ORG}/{REPO}.git"
    # set remote without touching global config
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=WORKDIR, capture_output=True, text=True)
    if r.returncode == 0:
        subprocess.run(["git", "remote", "set-url", "origin", clone_url], cwd=WORKDIR, check=True)
    else:
        subprocess.run(["git", "remote", "add", "origin", clone_url], cwd=WORKDIR, check=True)
    print("remote", clone_url)

    push = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=WORKDIR, capture_output=True, text=True)
    print("push stdout:", push.stdout[-500:])
    print("push stderr:", push.stderr[-800:])
    if push.returncode != 0:
        return 1

    # enable GitHub Pages (index.html at root)
    status, resp = gh_api(
        token,
        f"/repos/{ORG}/{REPO}/pages",
        "POST",
        {"source": {"branch": "main", "path": "/"}},
    )
    print("pages create:", status, resp if status >= 400 else {k: resp.get(k) for k in ("html_url", "status", "url")})

    status2, resp2 = gh_api(token, f"/repos/{ORG}/{REPO}/pages")
    print("pages get:", status2, resp2 if isinstance(resp2, dict) else resp2)
    html_url = (resp2 or {}).get("html_url") or (resp or {}).get("html_url")
    print("SITE_URL", html_url or f"https://{ORG}.github.io/{REPO}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
