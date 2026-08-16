import sys, os, json
sys.path.insert(0,'.')
import ethlib
from eth_hash.auto import keccak
from eth_abi import decode as abi_decode

HOOK="0xcf4d29f14cc585ddd1167f956092852af844e040"
MIG ="0xdf0a7ec235fb104e5b3e7426da7709186a809d47"

def topic0(sig): return "0x"+keccak(sig.encode()).hex()

def get_logs(addr, t0, fromBlock=0):
    d = ethlib.es({"module":"logs","action":"getLogs","address":addr,
                   "fromBlock":fromBlock,"toBlock":"latest","topic0":t0})
    if d.get("status")=="1": return d["result"]
    return []

out={}

# --- Migration Claimed(address indexed account, uint256 amount) ---
mc = get_logs(MIG, topic0("Claimed(address,uint256)"))
claims=[]
for L in mc:
    acct = "0x"+L["topics"][1][-40:]
    amt  = int(L["data"],16)
    claims.append((acct, amt, int(L["blockNumber"],16)))
total_claimed = sum(a for _,a,_ in claims)
distinct = len(set(a for a,_,_ in claims))
out["migration_claims"] = {
    "count": len(claims),
    "distinct_recipients": distinct,
    "total_claimed_wei": str(total_claimed),
    "total_claimed_PRISM": total_claimed/1e18,
    "largest": sorted([(a,amt) for a,amt,_ in claims], key=lambda x:-x[1])[:10],
    "sample_first5": [(a,amt/1e18) for a,amt,_ in claims[:5]],
}

# --- Migration TokenSet(address) ---
ts = get_logs(MIG, topic0("TokenSet(address)"))
out["migration_tokenset"] = [{"token":"0x"+L["data"][-40:], "block":int(L["blockNumber"],16), "tx":L["transactionHash"]} for L in ts]

# --- Hook Seeded(uint256 indexed posmTokenId, uint160, uint128) ---
sd = get_logs(HOOK, topic0("Seeded(uint256,uint160,uint128)"))
seeded=[]
for L in sd:
    tid=int(L["topics"][1],16)
    data=bytes.fromhex(L["data"][2:])
    sqrtP=int.from_bytes(data[0:32],"big"); liq=int.from_bytes(data[32:64],"big")
    seeded.append({"posmTokenId":tid,"sqrtPriceX96":str(sqrtP),"liquidity":str(liq),"block":int(L["blockNumber"],16),"tx":L["transactionHash"]})
out["hook_seeded"]=seeded

# --- Hook PendingCredited(address indexed user, uint256, uint256) : find holders w/ pending ---
pc = get_logs(HOOK, topic0("PendingCredited(address,uint256,uint256)"))
holders = list(dict.fromkeys("0x"+L["topics"][1][-40:] for L in pc))
out["pending_credited_events"]=len(pc)
out["distinct_pending_holders"]=len(holders)
out["_holders_sample"]=holders[:40]

# --- Hook PendingWithdrawn count ---
pw = get_logs(HOOK, topic0("PendingWithdrawn(address,uint256,uint256)"))
out["pending_withdrawn_events"]=len(pw)

# --- Hook FeesForfeited / PokeCollectFailed (alarms) ---
out["fees_forfeited_events"]=len(get_logs(HOOK, topic0("FeesForfeited(uint256,uint256)")))
out["poke_collect_failed_events"]=len(get_logs(HOOK, topic0("PokeCollectFailed()")))

print(json.dumps(out, indent=2, default=str))
json.dump(out, open("raw/events.json","w"), indent=2, default=str)
