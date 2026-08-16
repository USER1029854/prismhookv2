import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ethlib
from eth_hash.auto import keccak
from eth_abi import encode as abi_encode, decode as abi_decode

HOOK   = "0xcf4d29f14cc585ddd1167f956092852af844e040"
MIG    = "0xdf0a7ec235fb104e5b3e7426da7709186a809d47"
PM     = "0x000000000004444c5dc75cb358380d2e3de08a90"
POSM   = "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e"
PERMIT2= "0x000000000022d473030f116ddee9f6b43ac78ba3"
BURN   = "0x000000000000000000000000000000000000dEaD"
OWNER_CARG = "0xfe76f05a01163e5c90329a0d1a2c8e389fd0f110"

def c(to, sig, at, ar, rt, frm=None):
    v, raw = ethlib.call(to, sig, at, ar, rt, frm=frm)
    return v

out = {}

# ---- HOOK state ----
h = {}
h["owner"]                 = c(HOOK, "owner()", [], [], ["address"])
h["seeded"]                = c(HOOK, "seeded()", [], [], ["bool"])
h["forfeitNextCollection"] = c(HOOK, "forfeitNextCollection()", [], [], ["bool"])
h["hookPositionTokenId"]   = c(HOOK, "hookPositionTokenId()", [], [], ["uint256"])
h["totalShares"]           = c(HOOK, "totalShares()", [], [], ["uint256"])
h["accFeesPerShareETH"]    = c(HOOK, "accFeesPerShareETH()", [], [], ["uint256"])
h["accFeesPerSharePRISM"]  = c(HOOK, "accFeesPerSharePRISM()", [], [], ["uint256"])
h["mirror"]                = c(HOOK, "mirror()", [], [], ["address"])
h["POSM"]                  = c(HOOK, "POSM()", [], [], ["address"])
h["PERMIT2"]               = c(HOOK, "PERMIT2()", [], [], ["address"])
h["MIGRATION_VAULT"]       = c(HOOK, "MIGRATION_VAULT()", [], [], ["address"])
h["poolManager"]           = c(HOOK, "poolManager()", [], [], ["address"])
h["decimals"]              = c(HOOK, "decimals()", [], [], ["uint8"])
h["totalSupply"]           = c(HOOK, "totalSupply()", [], [], ["uint256"])
h["globalTickLower"]       = c(HOOK, "globalTickLower()", [], [], ["int24"])
h["globalTickUpper"]       = c(HOOK, "globalTickUpper()", [], [], ["int24"])
h["balanceOf(hook)"]       = c(HOOK, "balanceOf(address)", ["address"], [HOOK], ["uint256"])
h["balanceOf(migration)"]  = c(HOOK, "balanceOf(address)", ["address"], [MIG], ["uint256"])
h["balanceOf(burn)"]       = c(HOOK, "balanceOf(address)", ["address"], [BURN], ["uint256"])
h["balanceOf(poolMgr)"]    = c(HOOK, "balanceOf(address)", ["address"], [PM], ["uint256"])
h["balanceOf(owner)"]      = c(HOOK, "balanceOf(address)", ["address"], [OWNER_CARG], ["uint256"])
h["balanceOf(posm)"]       = c(HOOK, "balanceOf(address)", ["address"], [POSM], ["uint256"])
h["ETH_balance"]           = ethlib.get_balance(HOOK)
out["hook"] = h

# ---- MIGRATION vault state ----
m = {}
m["deployer"]   = c(MIG, "deployer()", [], [], ["address"])
m["token"]      = c(MIG, "token()", [], [], ["address"])
m["tokenFinal"] = c(MIG, "tokenFinal()", [], [], ["bool"])
m["merkleRoot"] = c(MIG, "merkleRoot()", [], [], ["bytes32"])
m["PRISM_balance_via_hook"] = c(HOOK, "balanceOf(address)", ["address"], [MIG], ["uint256"])
m["ETH_balance"] = ethlib.get_balance(MIG)
out["migration"] = m

# ---- POOL state via PoolManager reserves + StateView ----
# poolId = keccak(abi.encode(currency0, currency1, fee, tickSpacing, hooks))
poolkey = abi_encode(
    ["address","address","uint24","int24","address"],
    ["0x0000000000000000000000000000000000000000", HOOK, 10000, 200, HOOK]
)
poolId = keccak(poolkey)
p = {}
p["poolId"] = "0x"+poolId.hex()
p["poolManager_ETH_balance"]  = ethlib.get_balance(PM)
p["poolManager_PRISM_balance"] = c(HOOK, "balanceOf(address)", ["address"], [PM], ["uint256"])
# Try canonical StateView addresses
STATEVIEW = "0x7ffe42c4a5deea5b0fec41c94c136cf115597227"
sv_liq = c(STATEVIEW, "getLiquidity(bytes32)", ["bytes32"], [poolId], ["uint128"])
sv_slot0 = c(STATEVIEW, "getSlot0(bytes32)", ["bytes32"], [poolId], ["uint160","int24","uint24","uint24"])
p["stateview_addr"] = STATEVIEW
p["getLiquidity"] = sv_liq
p["getSlot0 (sqrtPriceX96,tick,protoFee,lpFee)"] = sv_slot0
out["pool"] = p

# ---- POSM position ownership ----
po = {}
tid = h.get("hookPositionTokenId")
tid = tid[0] if isinstance(tid, tuple) else tid
if tid:
    po["hookPositionTokenId"] = tid
    po["ownerOf(tokenId)"] = c(POSM, "ownerOf(uint256)", ["uint256"], [tid], ["address"])
out["posm_position"] = po

# ---- Permit2 allowance (hook token -> POSM spender, owner=hook) ----
pa = {}
# allowance(address owner, address token, address spender) -> (uint160 amount, uint48 expiration, uint48 nonce)
pa["allowance(hook, PRISM, POSM)"] = c(PERMIT2, "allowance(address,address,address)",
    ["address","address","address"], [HOOK, HOOK, POSM], ["uint160","uint48","uint48"])
# ERC20 allowance PRISM: hook -> permit2 (should be max)
pa["erc20_allowance(hook->permit2)"] = c(HOOK, "allowance(address,address)",
    ["address","address"], [HOOK, PERMIT2], ["uint256"])
out["permit2"] = pa

def norm(o):
    if isinstance(o, tuple): return [norm(x) for x in o]
    if isinstance(o, list):  return [norm(x) for x in o]
    if isinstance(o, dict):  return {k: norm(v) for k,v in o.items()}
    if isinstance(o, bytes): return "0x"+o.hex()
    if isinstance(o, int):   return str(o)
    return o

print(json.dumps(norm(out), indent=2))
json.dump(norm(out), open(os.path.dirname(os.path.abspath(__file__))+"/raw/livestate.json","w"), indent=2)
