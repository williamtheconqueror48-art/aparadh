#!/usr/bin/env python3
"""Deploy APARADH (plain static site) to Vercel.

- Creates project `aparadh` with no framework (static, no build).
- Tries git-link to williamtheconqueror48-art/aparadh (rootDirectory=public);
  falls back to direct file-upload of public/.
- Disables Deployment Protection SSO so the site is public.
- Waits for READY and prints the live URL.

Auth: stored custom.vercel connector via authd surrogates. api.vercel.com only.
"""
from __future__ import annotations
import hashlib, json, os, sys, time, urllib.request, urllib.error

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response, DynamicCredentialError

CRED, API = "custom.vercel", "https://api.vercel.com"
HOSTS = ["api.vercel.com"]
PROJECT, REPO = "aparadh", "williamtheconqueror48-art/aparadh"
ROOT = "/home/hatch/workspace/aparadh-push/public"
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".vercel"}

def api(method, path, payload=None):
    req = urllib.request.Request(API + path, method=method)
    if payload is not None:
        req = urllib.request.Request(API + path, data=json.dumps(payload).encode(), method=method)
        req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    add_surrogate_to_request(req, CRED, allowed_hosts=HOSTS)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return {} if resp.status == 204 else read_json_response(resp)
    except urllib.error.HTTPError as e:
        raise DynamicCredentialError(f"Vercel {method} {path} -> {e.code}: {e.read().decode('utf-8','replace')[:500]}")

def get_project():
    try: return api("GET", f"/v10/projects/{PROJECT}")
    except DynamicCredentialError as e:
        return None if "404" in str(e) else (_ for _ in ()).throw(e)

def collect_files(root):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root)
            with open(full, "rb") as fh:
                out.append((rel, fh.read()))
    out.sort()
    return out

def upload_file(content, digest):
    req = urllib.request.Request(API + "/v2/files", data=content, method="POST")
    req.add_header("Content-Type", "application/octet-stream")
    req.add_header("x-vercel-digest", digest)
    add_surrogate_to_request(req, CRED, allowed_hosts=HOSTS)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        raise DynamicCredentialError(f"Vercel file upload -> {e.code}: {e.read().decode('utf-8','replace')[:300]}")

def deploy_from_files(project, root):
    files = collect_files(root)
    print(f"uploading {len(files)} files…")
    file_list = []
    for rel, content in files:
        digest = hashlib.sha1(content).hexdigest()
        upload_file(content, digest)
        file_list.append({"file": rel, "sha": digest, "size": len(content)})
    return api("POST", "/v13/deployments", {"name": project["name"], "project": project["id"],
               "target": "production", "files": file_list,
               "projectSettings": {"framework": None}})

def wait_ready(dep_id, timeout=420):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = api("GET", f"/v13/deployments/{dep_id}")
        st = d.get("status") or d.get("readyState")
        print(f"  deployment {dep_id}: {st}")
        if st == "READY": return d
        if st in ("ERROR", "CANCELED"): raise RuntimeError(f"deploy failed: {st}")
        time.sleep(12)
    raise TimeoutError("deploy not ready in time")

def main():
    me = api("GET", "/v2/user")["user"]
    print("authenticated as:", me.get("username"))
    proj = get_project()
    if proj:
        print("project exists:", PROJECT)
    else:
        try:
            proj = api("POST", "/v10/projects", {"name": PROJECT, "gitRepository": {"type": "github", "repo": REPO}})
            print("project created with GitHub link")
        except DynamicCredentialError as e:
            print("git link failed; creating unlinked:", str(e)[:100])
            proj = api("POST", "/v10/projects", {"name": PROJECT})
    pid = proj["id"]
    # static: no framework, no build; public site (no SSO gate)
    api("PATCH", f"/v9/projects/{pid}", {"framework": None, "ssoProtection": None})
    print("project set: framework=null, ssoProtection=null (public)")

    link = proj.get("link") or {}
    if link.get("repoId"):
        api("PATCH", f"/v9/projects/{pid}", {"rootDirectory": "public"})
        dep = api("POST", "/v13/deployments", {"name": PROJECT, "project": pid,
                  "target": "production",
                  "gitSource": {"type": "github", "repoId": link["repoId"], "ref": "main"}})
        print("deploying from git main…")
    else:
        dep = deploy_from_files(proj, ROOT)
        print("deploying from file upload…")
    d = wait_ready(dep["id"])
    url = d.get("url")
    print("LIVE:", f"https://{url}")
    # confirm public (no SSO gate)
    import subprocess
    r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}",f"https://{url}/"],capture_output=True,text=True,timeout=60)
    print("public check HTTP:", r.stdout.strip())

if __name__ == "__main__":
    main()
