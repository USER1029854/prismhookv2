import os, hashlib, json
ROOT = "/home/user/prismhookv2/contracts"
TARGET = os.path.join(ROOT, "target")
# tree -> root package to prepend for its OWN src/ files (None if all files carry a marker)
DEP_TREES = {
    "PoolManager": (os.path.join(ROOT,"dependencies/UniswapV4-PoolManager"), "v4-core"),
    "StateView":   (os.path.join(ROOT,"dependencies/UniswapV4-StateView"), "v4-periphery"),
    "PositionManager": (os.path.join(ROOT,"dependencies/UniswapV4-PositionManager"), None),
    "Permit2":     (os.path.join(ROOT,"dependencies/Permit2"), "permit2"),
}
MARKERS = ["v4-core/","v4-periphery/","permit2/","solady/"]
def logical_key(rel):
    best=None
    for m in MARKERS:
        i=rel.rfind(m)
        if i!=-1 and (best is None or i>best[0]):
            best=(i, m.rstrip('/')+'/'+rel[i+len(m):])
    return best[1] if best else None
def key_for(rel, rootpkg):
    k=logical_key(rel)
    if k: return k
    if rootpkg and rel.startswith("src/"): return f"{rootpkg}/{rel}"
    return None
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()

corpus={}
for name,(base,rootpkg) in DEP_TREES.items():
    for dp,_,fns in os.walk(base):
        for fn in fns:
            if not fn.endswith('.sol'): continue
            rel=os.path.relpath(os.path.join(dp,fn),base)
            k=key_for(rel, rootpkg)
            if not k: continue
            corpus.setdefault(k,{}).setdefault(sha(os.path.join(dp,fn)),[]).append(name)

results=[]
for dp,_,fns in os.walk(TARGET):
    for fn in fns:
        if not fn.endswith('.sol'): continue
        rel=os.path.relpath(os.path.join(dp,fn),TARGET)
        k=logical_key(rel)
        if not k: continue
        h=sha(os.path.join(dp,fn))
        if k in corpus:
            if h in corpus[k]: results.append((k,"IDENTICAL-ONCHAIN",",".join(corpus[k][h])))
            else: results.append((k,"DIFFERS-ONCHAIN",";".join(f"{n}" for hh,ns in corpus[k].items() for n in ns)))
        else: results.append((k,"NO-ONCHAIN-COPY",""))

by={}
for k,s,d in results: by.setdefault(s,[]).append((k,d))
print(f"Target library files carrying a package marker: {len(results)}")
for s in sorted(by): print(f"  {s}: {len(by[s])}")
print()
for s in ("DIFFERS-ONCHAIN","NO-ONCHAIN-COPY"):
    if by.get(s):
        print(f"=== {s} ===")
        for k,d in sorted(by[s]): print(f"   {k}   [{d}]")
        print()
json.dump(sorted(results), open(os.path.dirname(os.path.abspath(__file__))+"/raw/integrity_v3.json","w"),indent=2)
