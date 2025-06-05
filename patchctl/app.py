from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess, os, json, tempfile, yaml

AUTH = yaml.safe_load(open("/config/authz.yaml"))
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

class Patch(BaseModel):
    author: str
    files: list
    dry_run: bool = False
    signature: str = "UNSIGNED"

@app.post("/apply")
def apply(patch: Patch):
    if patch.author not in AUTH:
        raise HTTPException(403, "author not allowed")
    # very naive diff writer
    for f in patch.files:
        allowed = any(fnmatch := (glob := g) for g in AUTH[patch.author] if __import__("fnmatch").fnmatch(f["path"], g))
        if not allowed:
            raise HTTPException(403, f"path {f['path']} not allowed")
    if patch.dry_run:
        return {"dry_run": True, "status": "accepted"}
    # write files
    for f in patch.files:
        os.makedirs(os.path.dirname(f["path"]), exist_ok=True)
        with open(f["path"], "w") as fp:
            fp.write("PATCHED\n")
    subprocess.run(["just", "ci", "--subset", "changed-files"], check=True)
    # TODO: restart affected container
    return {"status": "applied"} 