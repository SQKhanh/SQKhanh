#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.request

# ====== CAU HINH ======
# Paste token GitHub cua may vao bien TOKEN ben duoi (hoac set bien moi truong GH_PAT)
# Lay token tai: https://github.com/settings/tokens (classic, scope: repo)
TOKEN = ""  # <-- paste token vo trong cap dau nhay nay
USER = "SQKhanh"
# =========================

if TOKEN:
    GH_PAT = TOKEN
else:
    GH_PAT = os.environ.get("GH_PAT") or None
TOKEN_VAR = GH_PAT or os.environ.get("GITHUB_TOKEN") or None


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER,
            **({"Authorization": f"Bearer {TOKEN_VAR}"} if TOKEN_VAR else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        if r.status == 202:
            return None
        return json.loads(body) if body else []


def list_owned_repos():
    base = (
        "/user/repos?affiliation=owner" if GH_PAT else f"/users/{USER}/repos?type=owner"
    )
    repos, page = [], 1
    while True:
        batch = api(f"{base}&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def extract_contrib(data):
    for c in data:
        author = c.get("author") or {}
        if author.get("login", "").lower() == USER.lower():
            return (
                c["total"],
                sum(w["a"] for w in c["weeks"]),
                sum(w["d"] for w in c["weeks"]),
            )
    return 0, 0, 0


def contributor_stats(repo_names):
    results, pending = {}, list(repo_names)
    deadline = time.time() + 300
    wait = 5
    while pending:
        still = []
        for name in pending:
            try:
                data = api(f"/repos/{USER}/{name}/stats/contributors")
            except urllib.error.HTTPError as e:
                if e.code == 451:
                    print(f"skip {name}: HTTP 451")
                    continue
                raise
            if data is None:
                still.append(name)
            else:
                results[name] = extract_contrib(data)
        pending = still
        if pending and time.time() >= deadline:
            print(f"warn: stats timeout, skip: {', '.join(pending)}")
            break
        if pending:
            time.sleep(wait)
            wait = min(wait * 2, 60)
    return results


def fetch_stats():
    if not TOKEN_VAR:
        return None
    own = [r["name"] for r in list_owned_repos() if not r["fork"]]
    commits = add = dele = 0
    for c, a, d in contributor_stats(own).values():
        commits += c
        add += a
        dele += d
    return {
        "commits": commits,
        "followers": api(f"/users/{USER}")["followers"],
        "loc_add": add,
        "loc_del": dele,
    }


if __name__ == "__main__":
    stats = fetch_stats()
    if stats is None:
        print("Khong co GH_PAT/TOKEN/GITHUB_TOKEN -> stats ?? (preview)")
    else:
        net = stats["loc_add"] - stats["loc_del"]
        print(f"User:      {USER}")
        print(f"LOC added: {stats['loc_add']:,}")
        print(f"LOC del:   {stats['loc_del']:,}")
        print(f"LOC net:   {net:,}")
