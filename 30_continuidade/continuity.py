#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, tempfile, time, zipfile
from datetime import datetime, timezone
from pathlib import Path

VERSION="continuity-v1"
DEFAULT_ROOT=Path(os.environ.get("SISTEMA_CONTINUIDADE_DIR",str(Path.home()/".sistema-absoluto"/"continuidade")))
STATE="state.json"; JOURNAL="journal.jsonl"; CHECKPOINTS="checkpoints"
HEARTBEAT="heartbeat.json"; LOCK="lease.json"; MANIFEST="manifest.json"; MAX_CHECKPOINTS=20

def now(): return datetime.now(timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix="."+path.name+".",dir=str(path.parent))
    try:
        with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def read_json(path,default=None):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def append_event(root,event_type,payload):
    p=root/JOURNAL; previous=""
    if p.exists():
        lines=p.read_text(encoding="utf-8").splitlines()
        if lines:
            try: previous=json.loads(lines[-1])["hash"]
            except Exception: previous=""
    seq=len(p.read_text(encoding="utf-8").splitlines())+1 if p.exists() else 1
    event={"seq":seq,"at":now(),"type":event_type,"payload":payload,"previous_hash":previous}
    event["hash"]=digest(canonical(event))
    with p.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,ensure_ascii=False,separators=(",",":"))+"\n"); f.flush(); os.fsync(f.fileno())
    return event

def load_state(root):
    return read_json(root/STATE,{"schema":VERSION,"status":"initialized","generation":0,"updated_at":None,"last_checkpoint":None,"last_event":0,"owner":"Sistema Absoluto"})

def save_state(root,state):
    state["schema"]=VERSION; state["updated_at"]=now()
    atomic_write(root/STATE,canonical(state)+b"\n")

def checkpoint(root,reason="manual"):
    root.mkdir(parents=True,exist_ok=True); (root/CHECKPOINTS).mkdir(exist_ok=True)
    state=load_state(root); state["generation"]=int(state.get("generation",0))+1; state["status"]="checkpointed"
    event=append_event(root,"checkpoint",{"reason":reason,"generation":state["generation"]})
    state["last_event"]=event["seq"]; stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name=f"{stamp}-g{state['generation']:06d}.json"; state["last_checkpoint"]=name; save_state(root,state)
    atomic_write(root/CHECKPOINTS/name,canonical(state)+b"\n")
    cps=sorted((root/CHECKPOINTS).glob("*.json"))
    for old in cps[:-MAX_CHECKPOINTS]: old.unlink()
    return state

def verify(root):
    root.mkdir(parents=True,exist_ok=True); errors=[]; p=root/JOURNAL; prev=""; seq=0
    if p.exists():
        for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            seq+=1
            try:
                e=json.loads(line); body=dict(e); h=body.pop("hash",None)
                if e.get("seq")!=seq: errors.append(f"journal seq {n}")
                if e.get("previous_hash","")!=prev: errors.append(f"journal link {n}")
                if digest(canonical(body))!=h: errors.append(f"journal hash {n}")
                prev=h
            except Exception as exc: errors.append(f"journal parse {n}: {exc}")
    state=load_state(root)
    if state.get("last_event",0)>seq: errors.append("state.last_event exceeds journal")
    cps=sorted((root/CHECKPOINTS).glob("*.json")) if (root/CHECKPOINTS).exists() else []
    for cp in cps:
        try:
            if read_json(cp,{}).get("schema")!=VERSION: errors.append(f"checkpoint schema {cp.name}")
        except Exception as exc: errors.append(f"checkpoint parse {cp.name}: {exc}")
    return {"ok":not errors,"events":seq,"checkpoints":len(cps),"errors":errors}

def heartbeat(root,status="alive"):
    root.mkdir(parents=True,exist_ok=True)
    data={"service":"sistema-continuity","version":VERSION,"status":status,"pid":os.getpid(),"at":now()}
    atomic_write(root/HEARTBEAT,canonical(data)+b"\n"); return data

def recover(root,checkpoint_name=None):
    cps=sorted((root/CHECKPOINTS).glob("*.json"))
    if not cps: raise RuntimeError("nenhum checkpoint disponível")
    target=root/CHECKPOINTS/checkpoint_name if checkpoint_name else cps[-1]
    if not target.exists(): raise RuntimeError(f"checkpoint não encontrado: {target.name}")
    state=read_json(target)
    if not state: raise RuntimeError("checkpoint inválido")
    save_state(root,state); append_event(root,"recovery",{"checkpoint":target.name,"generation":state.get("generation",0)})
    heartbeat(root,"recovered"); return state

def lease(root,release=False):
    p=root/LOCK
    if release:
        try: p.unlink()
        except FileNotFoundError: pass
        return
    current=read_json(p)
    if current and current.get("expires_at",0)>time.time() and current.get("pid")!=os.getpid():
        raise RuntimeError("lease já está ativo")
    data={"pid":os.getpid(),"started_at":now(),"expires_at":time.time()+120}
    atomic_write(p,canonical(data)+b"\n"); return data

def manifest(root):
    files=[]
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name!=MANIFEST:
            files.append({"path":str(p.relative_to(root)),"sha256":digest(p.read_bytes()),"size":p.stat().st_size})
    m={"schema":VERSION,"generated_at":now(),"files":files}; atomic_write(root/MANIFEST,canonical(m)+b"\n"); return m

def export_bundle(root,destination):
    manifest(root); destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,"w",zipfile.ZIP_DEFLATED) as z:
        for p in root.rglob("*"):
            if p.is_file(): z.write(p,p.relative_to(root))
    return destination

def init(root):
    root.mkdir(parents=True,exist_ok=True); (root/CHECKPOINTS).mkdir(exist_ok=True)
    if not (root/STATE).exists():
        save_state(root,load_state(root)); append_event(root,"initialized",{"version":VERSION}); heartbeat(root,"ready"); checkpoint(root,"initial")
    else: heartbeat(root,"ready")

def main():
    ap=argparse.ArgumentParser(description="Continuidade Operacional do Sistema Absoluto")
    ap.add_argument("--root",default=str(DEFAULT_ROOT)); sub=ap.add_subparsers(dest="cmd",required=True)
    sub.add_parser("init"); sub.add_parser("status"); sub.add_parser("verify"); sub.add_parser("heartbeat"); sub.add_parser("manifest")
    p=sub.add_parser("checkpoint"); p.add_argument("--reason",default="manual")
    p=sub.add_parser("recover"); p.add_argument("--checkpoint")
    p=sub.add_parser("export"); p.add_argument("destination")
    sub.add_parser("start-lease"); sub.add_parser("release-lease")
    a=ap.parse_args(); root=Path(a.root).expanduser()
    if a.cmd=="init": init(root)
    elif a.cmd=="checkpoint": print(json.dumps(checkpoint(root,a.reason),ensure_ascii=False,indent=2))
    elif a.cmd=="verify": print(json.dumps(verify(root),ensure_ascii=False,indent=2))
    elif a.cmd=="recover": print(json.dumps(recover(root,a.checkpoint),ensure_ascii=False,indent=2))
    elif a.cmd=="heartbeat": print(json.dumps(heartbeat(root),ensure_ascii=False,indent=2))
    elif a.cmd=="manifest": print(json.dumps(manifest(root),ensure_ascii=False,indent=2))
    elif a.cmd=="export": print(export_bundle(root,a.destination))
    elif a.cmd=="start-lease": print(json.dumps(lease(root),ensure_ascii=False,indent=2))
    elif a.cmd=="release-lease": lease(root,True)
    elif a.cmd=="status": init(root); print(json.dumps({"state":load_state(root),"heartbeat":read_json(root/HEARTBEAT,{}),"integrity":verify(root)},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
