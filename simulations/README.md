# Empirical simulations — permissionless caller matrix

**Method.** Each row is an `eth_call` executed against **current mainnet state** with `from` set to
an **arbitrary unprivileged EOA** (`0x1111…1111`), or, where noted, another address via `from`
override (a real pending-fee holder; an excluded address; the ex-owner/deployer). Reverts are
captured from the node's `error.data` and decoded by 4-byte custom-error selector. This determines
empirically *what an unprivileged caller can actually reach and what reverts* — not from reading the
code, but from running it. Raw results: [`permissionless_caller_matrix.json`](permissionless_caller_matrix.json).
Reproduce: [`../tools/simulate.py`](../tools/).

> `eth_call` proves reachability and revert-vs-success against live state; it does not persist state,
> so "credits the owner, not the caller" is established by the code path plus the `pendingFees` view,
> and the value-movement row uses a real holder who already has a pending balance.

## Results

### Permissionless surface — reachable from a stranger (all SUCCESS)
| Call | Result | Meaning |
|---|---|---|
| `pokeFees()` | ✅ SUCCESS | Anyone can trigger fee collection. |
| `claim(562)` | ✅ SUCCESS | Anyone can claim a live token; credits the **owner's** pending, not the caller (code: `_claimOne` → `_ownerOf(id)`). |
| `claimMany([562])` | ✅ SUCCESS | Batch claim, same. |
| `withdrawPending()` | ✅ SUCCESS | No-op for a stranger (no pending). |
| `withdrawPendingTo(0x1111…)` | ✅ SUCCESS | No-op. |
| `syncNFTs(0)` | ✅ SUCCESS | No-op (stranger holds 0 PRISM). |
| `withdrawPending()` **from `0x98f0c7…`** | ✅ SUCCESS | **Real value moves** — holder had pendingETH 0.001132 + pendingPRISM 0.007535; withdraws to self. |

`pendingFees(562)` = owedETH 0.001869, owedPRISM 0.009131 — live accrued value the permissionless
`claim` realizes for token #562's owner.

### Guards — revert as designed (all REVERT)
| Call (from stranger unless noted) | Revert |
|---|---|
| `withdrawPendingTo(PoolManager)` | `ExcludedRecipient()` |
| `withdrawPendingTo(address(0))` | `TransferToZero()` |
| `handleNFTTransfer(...)` | `MirrorOnly()` |
| `handleNFTApprove(...)` | `MirrorOnly()` |
| `syncNFTs(0)` from an **excluded** address (PoolManager) | `ExcludedRecipient()` |
| `seed(...)` from stranger | `Unauthorized()` |
| `seed(...)` from **ex-owner** `0xfe76…f110` | `Unauthorized()` |

### Migration vault
| Call | Revert / result |
|---|---|
| `claim(0x1111…, 1, [])` (bogus proof) | `InvalidProof()` |
| `claim(0x8347…, 287.24e18, [])` (already-claimed acct) | `AlreadyClaimed()` |
| `setToken(0x1111…)` from stranger | `NotDeployer()` |
| `setToken(0x1111…)` from **deployer** | `TokenLocked()` |

## What this establishes

1. The fund-touching surface is genuinely **permissionless and reachable**, and pays **credited
   holders**, not callers.
2. Every access/exclusion guard **holds at current chain state**.
3. **No privileged escape hatch remains** — neither the ex-owner nor the deployer can re-seed,
   re-point, or unlock anything. The system behaves as immutable and admin-less right now.
