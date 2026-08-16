import os, hashlib, urllib.request, json, time
TARGET="/home/user/prismhookv2/contracts/target"
def sha(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return sha(open(p,'rb').read())

# target file (relative to TARGET) -> (repo, path_in_repo, [candidate refs])
FILES = {
 "lib/solady/src/auth/Ownable.sol": ("Vectorized/solady","src/auth/Ownable.sol"),
 "lib/solady/src/tokens/ERC20.sol": ("Vectorized/solady","src/tokens/ERC20.sol"),
 "lib/solady/src/utils/Base64.sol": ("Vectorized/solady","src/utils/Base64.sol"),
 "lib/solady/src/utils/LibBytes.sol": ("Vectorized/solady","src/utils/LibBytes.sol"),
 "lib/solady/src/utils/LibString.sol": ("Vectorized/solady","src/utils/LibString.sol"),
 "lib/solady/src/utils/ReentrancyGuard.sol": ("Vectorized/solady","src/utils/ReentrancyGuard.sol"),
 "lib/v4-periphery/lib/v4-core/src/interfaces/IHooks.sol": ("Uniswap/v4-core","src/interfaces/IHooks.sol"),
 "lib/v4-periphery/lib/v4-core/src/interfaces/IPoolManager.sol": ("Uniswap/v4-core","src/interfaces/IPoolManager.sol"),
 "lib/v4-periphery/lib/v4-core/src/libraries/Hooks.sol": ("Uniswap/v4-core","src/libraries/Hooks.sol"),
 "lib/v4-periphery/lib/v4-core/src/types/PoolOperation.sol": ("Uniswap/v4-core","src/types/PoolOperation.sol"),
 "lib/v4-periphery/src/libraries/Actions.sol": ("Uniswap/v4-periphery","src/libraries/Actions.sol"),
 "lib/v4-periphery/src/libraries/PositionInfoLibrary.sol": ("Uniswap/v4-periphery","src/libraries/PositionInfoLibrary.sol"),
}
REFS = {"Vectorized/solady":["main"], "Uniswap/v4-core":["main"], "Uniswap/v4-periphery":["main"]}

def fetch(repo, ref, path):
    url=f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"
    for _ in range(4):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"audit/1.0"})
            with urllib.request.urlopen(req,timeout=40) as r:
                if r.status==200: return r.read()
        except Exception: time.sleep(1.0)
    return None

out=[]
for tf,(repo,path) in FILES.items():
    tsha=shaf(os.path.join(TARGET,tf))
    matched=None; got=None
    for ref in REFS[repo]:
        b=fetch(repo,ref,path)
        if b is None: continue
        got=(ref, sha(b), len(b), b)
        if sha(b)==tsha: matched=ref; break
    status="IDENTICAL-GITHUB@"+matched if matched else "DIFF-vs-main"
    out.append({"file":tf,"repo":repo,"status":status,
                "target_sha":tsha[:16],"github_sha":(got[1][:16] if got else None)})
    print(f"{status:26} {repo:20} {os.path.basename(tf)}")
    # save the github copy for any that differ, for diffing
    if not matched and got:
        d="/tmp/claude-0/-home-user-prismhookv2/4f6785d0-c4af-5c6c-b3d6-58cada9abf7a/scratchpad/gh"
        os.makedirs(d,exist_ok=True)
        open(os.path.join(d, os.path.basename(tf)+".main"),"wb").write(got[3])
print()
n_id=sum(1 for o in out if o['status'].startswith('IDENTICAL'))
print(f"IDENTICAL to GitHub main: {n_id}/{len(out)}")
json.dump(out, open("/tmp/claude-0/-home-user-prismhookv2/4f6785d0-c4af-5c6c-b3d6-58cada9abf7a/scratchpad/raw/integrity_github.json","w"),indent=2)
