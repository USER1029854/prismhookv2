import sys, os, json
sys.path.insert(0,'.')
import ethlib
from eth_hash.auto import keccak
from eth_abi import decode as abi_decode

HOOK="0xcf4d29f14cc585ddd1167f956092852af844e040"
MIG ="0xdf0a7ec235fb104e5b3e7426da7709186a809d47"
PM  ="0x000000000004444c5dc75cb358380d2e3de08a90"
POSM="0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e"
DEPLOYER="0xfe76f05a01163e5c90329a0d1a2c8e389fd0f110"
RAND="0x1111111111111111111111111111111111111111"   # arbitrary unprivileged EOA
ZERO="0x0000000000000000000000000000000000000000"

# ---- custom error selector table ----
ERRSIGS = [
 "AlreadySeeded()","NotSeeded()","ZeroAddress()","NotOwnerOrApproved()","InvalidTokenId()",
 "MirrorOnly()","TransferToZero()","SelfTransferDisallowed()","ExcludedRecipient()",
 "UnauthorizedInitialize()","BadMigration()","Reentrancy()","Unauthorized()",
 "NewOwnerIsZeroAddress()","AlreadyInitialized()","InsufficientBalance()","InsufficientAllowance()",
 "AllowanceOverflow()","AllowanceUnderflow()","TotalSupplyOverflow()","InvalidPermit()","PermitExpired()",
 # migration
 "AlreadyClaimed()","InvalidProof()","TokenLocked()","TokenNotSet()","NotDeployer()","ZeroDeployer()",
 "ZeroToken()","NotFunded()","TransferFailed()",
]
ERRMAP = {"0x"+keccak(s.encode()).hex()[:8]: s for s in ERRSIGS}
ERRMAP["0x08c379a0"]="Error(string)"
ERRMAP["0x4e487b71"]="Panic(uint256)"

def sim(to, sig, argtypes, args, frm, note=""):
    data = ethlib.encode_call(sig, argtypes, args)
    d = ethlib.es_proxy("eth_call", {"to":to,"data":data,"from":frm,"tag":"latest"})
    if "error" in d:
        edata = d["error"].get("data")
        sel = edata[:10] if isinstance(edata,str) and edata.startswith("0x") and len(edata)>=10 else None
        name = ERRMAP.get(sel, sel or d["error"].get("message"))
        # decode Error(string)
        if sel=="0x08c379a0":
            try: name=f'Error("{abi_decode(["string"], bytes.fromhex(edata[10:]))[0]}")'
            except: pass
        return {"call":sig,"from":frm,"result":"REVERT","revert":name,"note":note}
    return {"call":sig,"from":frm,"result":"SUCCESS","returndata":(d.get("result") or "0x")[:66],"note":note}

# ---- find a live tokenId (largest claimer holds ~287 PRISM -> ~287 NFTs) ----
BIG="0x8347ca89c40b139e8e9b38d82d7b799a3db68605"
owned,_ = ethlib.call(HOOK,"ownedTokensOf(address)",["address"],[BIG],["uint256[]"])
live_id = owned[0] if owned else 1
# pendingFees for that live id (what claim would realize for its owner)
pf,_ = ethlib.call(HOOK,"pendingFees(uint256)",["uint256"],[live_id],["uint256","uint256"])

# ---- find a holder with pending>0 ----
ev=json.load(open("raw/events.json"))
pending_holder=None; ph_eth=0; ph_prism=0
for h in ev.get("_holders_sample",[]):
    pe,_=ethlib.call(HOOK,"pendingETH(address)",["address"],[h],["uint256"])
    pp,_=ethlib.call(HOOK,"pendingPRISM(address)",["address"],[h],["uint256"])
    if (pe or 0)>0 or (pp or 0)>0:
        pending_holder=h; ph_eth=pe or 0; ph_prism=pp or 0; break

sims=[]
# ---- PERMISSIONLESS value/functionality paths from an arbitrary unprivileged EOA ----
sims.append(sim(HOOK,"pokeFees()",[],[],RAND,"permissionless fee collection"))
sims.append(sim(HOOK,"claim(uint256)",["uint256"],[live_id],RAND,f"claim live id {live_id} from stranger -> credits OWNER not caller"))
sims.append(sim(HOOK,"claimMany(uint256[])",["uint256[]"],[[live_id]],RAND,"batch claim from stranger"))
sims.append(sim(HOOK,"withdrawPending()",[],[],RAND,"stranger has no pending -> no-op success"))
sims.append(sim(HOOK,"withdrawPendingTo(address)",["address"],[RAND],RAND,"no-op success"))
sims.append(sim(HOOK,"syncNFTs(uint256)",["uint256"],[0],RAND,"stranger holds 0 PRISM -> no-op success"))
# value-moving: a holder WITH pending withdraws (from-override)
if pending_holder:
    sims.append(sim(HOOK,"withdrawPending()",[],[],pending_holder,
        f"holder {pending_holder} withdraws pendingETH={ph_eth/1e18:.6f} pendingPRISM={ph_prism/1e18:.6f}"))
# ---- GUARDS (must revert) ----
sims.append(sim(HOOK,"withdrawPendingTo(address)",["address"],[PM],RAND,"route fees to PoolManager -> ExcludedRecipient"))
sims.append(sim(HOOK,"withdrawPendingTo(address)",["address"],[ZERO],RAND,"route to zero -> TransferToZero"))
sims.append(sim(HOOK,"handleNFTTransfer(address,address,uint256,address)",["address","address","uint256","address"],[RAND,RAND,live_id,RAND],RAND,"non-mirror -> MirrorOnly"))
sims.append(sim(HOOK,"handleNFTApprove(address,uint256,address)",["address","uint256","address"],[RAND,live_id,RAND],RAND,"non-mirror -> MirrorOnly"))
sims.append(sim(HOOK,"seed(uint160,int24,int24,uint128)",["uint160","int24","int24","uint128"],[1000,-100,100,1],RAND,"stranger cannot seed -> Unauthorized(owner=0)"))
sims.append(sim(HOOK,"seed(uint160,int24,int24,uint128)",["uint160","int24","int24","uint128"],[1000,-100,100,1],DEPLOYER,"ex-owner (renounced) cannot re-seed -> Unauthorized/AlreadySeeded"))
sims.append(sim(HOOK,"syncNFTs(uint256)",["uint256"],[0],PM,"excluded address caller -> ExcludedRecipient"))
# ---- MIGRATION vault ----
sims.append(sim(MIG,"claim(address,uint256,bytes32[])",["address","uint256","bytes32[]"],[RAND,1,[]],RAND,"bogus proof -> InvalidProof"))
sims.append(sim(MIG,"claim(address,uint256,bytes32[])",["address","uint256","bytes32[]"],[BIG,287239345896629340786,[]],RAND,"already-claimed acct -> AlreadyClaimed"))
sims.append(sim(MIG,"setToken(address)",["address"],[RAND],RAND,"stranger cannot set token -> NotDeployer"))
sims.append(sim(MIG,"setToken(address)",["address"],[RAND],DEPLOYER,"deployer cannot re-point now (tokenFinal) -> TokenLocked"))

result={"live_token_id":live_id,
        "pendingFees(live_id)":{"owedETH":str(pf[0]) if pf else None,"owedPRISM":str(pf[1]) if pf else None} if pf else None,
        "pending_holder_tested":pending_holder,
        "simulations":sims}
print(json.dumps(result,indent=2,default=str))
json.dump(result,open("raw/simulations.json","w"),indent=2,default=str)
