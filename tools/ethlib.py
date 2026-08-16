"""Helper library for Etherscan V2 API + Ethereum RPC (via Etherscan proxy).
Defensive-security contract-audit repo assembly.
"""
import json, os, time, urllib.request, urllib.parse, urllib.error

ETHERSCAN_KEY = "R6PYYNEX4CNFAXX4YX3K8W4NXSBGGG4QGJ"
BLOCKSCOUT_KEY = "proapi_CXlzRYJyLN9T7Uxugw1KTDV51rjzCrMXVSKTfyf5Tn5CUzrqEWYCSWcXQUiKfmNB_fNH9s"
CHAINID = 1
BASE = "https://api.etherscan.io/v2/api"

SCRATCH = "/tmp/claude-0/-home-user-prismhookv2/4f6785d0-c4af-5c6c-b3d6-58cada9abf7a/scratchpad"

_last_call = [0.0]
_MIN_INTERVAL = 0.23  # stay under Etherscan 5 req/s

def _throttle():
    dt = time.time() - _last_call[0]
    if dt < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - dt)
    _last_call[0] = time.time()

def _get(url, tries=6):
    last = None
    for i in range(tries):
        try:
            _throttle()
            req = urllib.request.Request(url, headers={"User-Agent": "audit/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            # retry on explicit rate-limit / NOTOK
            msg = str(d.get("message","")) + str(d.get("result",""))
            if "rate limit" in msg.lower() or "max calls" in msg.lower():
                time.sleep(1.0 * (i + 1)); last = RuntimeError(msg); continue
            return d
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last

def es(params):
    """Call Etherscan V2 API with given params dict."""
    p = dict(params)
    p["chainid"] = CHAINID
    p["apikey"] = ETHERSCAN_KEY
    url = BASE + "?" + urllib.parse.urlencode(p)
    return _get(url)

def get_source(address):
    """Return the raw getsourcecode result[0] dict for an address."""
    d = es({"module": "contract", "action": "getsourcecode", "address": address})
    if d.get("status") != "1" or not d.get("result"):
        return {"_error": d.get("message"), "_result": d.get("result")}
    return d["result"][0]

def is_verified(src):
    return bool(src.get("SourceCode"))

def parse_sources(src):
    """Extract {path: content} from a getsourcecode result. Handles all 3 formats."""
    sc = src.get("SourceCode", "")
    if not sc:
        return {}
    # Multi-file standard-json wrapped in {{ }}
    if sc.startswith("{{") and sc.endswith("}}"):
        obj = json.loads(sc[1:-1])
        out = {}
        for path, v in obj.get("sources", {}).items():
            out[path] = v.get("content", "")
        return out
    # Sometimes a plain JSON object (single braces) with sources
    if sc.startswith("{"):
        try:
            obj = json.loads(sc)
            if "sources" in obj:
                out = {}
                for path, v in obj["sources"].items():
                    out[path] = v.get("content", "")
                return out
            # {path: {content:...}} form
            out = {}
            for path, v in obj.items():
                if isinstance(v, dict) and "content" in v:
                    out[path] = v["content"]
            if out:
                return out
        except Exception:
            pass
    # Single-file flat source
    name = src.get("ContractName") or "Contract"
    return {f"{name}.sol": sc}

def rpc(method, params):
    """eth JSON-RPC via Etherscan V2 proxy module."""
    p = {"module": "proxy", "action": method}
    # map param positions per method
    d = es_proxy(method, params)
    return d

def es_proxy(action, extra):
    p = {"module": "proxy", "action": action}
    p.update(extra)
    p["chainid"] = CHAINID
    p["apikey"] = ETHERSCAN_KEY
    url = BASE + "?" + urllib.parse.urlencode(p)
    return _get(url)

def eth_call(to, data, tag="latest", frm=None):
    extra = {"to": to, "data": data, "tag": tag}
    if frm:
        extra["from"] = frm
    d = es_proxy("eth_call", extra)
    return d.get("result")

def get_storage_at(addr, slot, tag="latest"):
    d = es_proxy("eth_getStorageAt", {"address": addr, "position": slot, "tag": tag})
    return d.get("result")

def get_code(addr, tag="latest"):
    d = es_proxy("eth_getCode", {"address": addr, "tag": tag})
    return d.get("result")

def get_balance(addr):
    d = es({"module": "account", "action": "balance", "address": addr, "tag": "latest"})
    return d.get("result")


# ---- ABI encoding / calls ----
from eth_hash.auto import keccak
from eth_abi import encode as abi_encode, decode as abi_decode

def selector(sig):
    return keccak(sig.encode())[:4]

def encode_call(sig, argtypes, args):
    return "0x" + selector(sig).hex() + (abi_encode(argtypes, args).hex() if argtypes else "")

def call(to, sig, argtypes, args, rettypes, frm=None, tag="latest"):
    data = encode_call(sig, argtypes, args)
    res = eth_call(to, data, tag=tag, frm=frm)
    if res is None or res == "0x" or not isinstance(res, str) or not res.startswith("0x"):
        return None, res
    try:
        raw = bytes.fromhex(res[2:])
    except ValueError:
        return None, res
    try:
        dec = abi_decode(rettypes, raw)
        return (dec[0] if len(dec) == 1 else dec), res
    except Exception as e:
        return f"DECODE_ERR:{e}", res

def addr_topic(a):
    return "0x" + "0"*24 + a.lower().replace("0x","")

def slot_hex(i):
    return "0x" + format(i, "064x")

def map_slot(key_bytes32, slot):
    """keccak(key . slot) for a mapping at storage `slot`."""
    return "0x" + keccak(bytes.fromhex(key_bytes32.replace('0x','')) + bytes.fromhex(slot_hex(slot)[2:])).hex()

if __name__ == "__main__":
    print("ethlib ready; keccak('')=", keccak(b'').hex()[:16])
