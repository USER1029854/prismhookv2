"""Fetch a verified contract's full source tree + metadata and save into a repo dir.
Usage: python3 save_contract.py <address> <dest_dir> [label]
Writes source files under dest_dir/, plus dest_dir/_meta.json with compiler/proxy/etc.
Robust getCode with re-query on suspiciously short results.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ethlib

def robust_code(addr, retries=4):
    best = "0x"
    for _ in range(retries):
        c = ethlib.get_code(addr)
        if c and len(c) > len(best):
            best = c
        # if it looks complete (matches a re-query), accept
        c2 = ethlib.get_code(addr)
        if c2 == best and best not in (None, "0x", ""):
            return best
    return best

def save(address, dest_dir, label=None):
    src = ethlib.get_source(address)
    code = robust_code(address)
    codelen = (len(code) - 2)//2 if code and code != "0x" else 0
    os.makedirs(dest_dir, exist_ok=True)
    meta = {
        "label": label,
        "address": address,
        "ContractName": src.get("ContractName"),
        "CompilerVersion": src.get("CompilerVersion"),
        "OptimizationUsed": src.get("OptimizationUsed"),
        "Runs": src.get("Runs"),
        "EVMVersion": src.get("EVMVersion"),
        "Proxy": src.get("Proxy"),
        "Implementation": src.get("Implementation"),
        "LicenseType": src.get("LicenseType"),
        "verified": ethlib.is_verified(src),
        "runtime_codesize_bytes": codelen,
        "ConstructorArguments": src.get("ConstructorArguments"),
    }
    if ethlib.is_verified(src):
        files = ethlib.parse_sources(src)
        for p, content in files.items():
            dest = os.path.join(dest_dir, p)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w") as f:
                f.write(content)
        meta["source_files"] = sorted(files.keys())
        # also save standard-json if multi-file
        sc = src.get("SourceCode","")
        if sc.startswith("{{"):
            open(os.path.join(dest_dir, "_standard_input.json"), "w").write(sc[1:-1])
        # save ABI
        if src.get("ABI") and src["ABI"] != "Contract source code not verified":
            open(os.path.join(dest_dir, "_abi.json"), "w").write(src["ABI"])
    else:
        # save runtime bytecode for recovery work
        open(os.path.join(dest_dir, "runtime_bytecode.hex"), "w").write(code or "0x")
    json.dump(meta, open(os.path.join(dest_dir, "_meta.json"), "w"), indent=2)
    return meta

if __name__ == "__main__":
    address = sys.argv[1]
    dest = sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else None
    m = save(address, dest, label)
    print(json.dumps({k: m[k] for k in ("label","address","ContractName","verified","runtime_codesize_bytes","Proxy","Implementation")}, indent=2))
    if m.get("source_files"):
        print("Files:", len(m["source_files"]))
