# PrismMigration — analysis (MIGRATION_VAULT)

**Address:** `0xdf0a7ec235fb104e5b3e7426da7709186a809d47` · **Verified** · Solidity 0.8.26 ·
runtime 1,824 bytes · not a proxy · Source: [`src/PrismMigration.sol`](src/PrismMigration.sol)

This is the **largest single piece of the target's attack surface**: at the hook's construction it
was minted **4,454.68 PRISM — 89% of the entire 5,000 supply** — and marked an *excluded* address in
the hook (so its balance mints no fee-shares and dilutes nobody). It is the "unlabeled address a
bespoke function sends real money to" that the trust graph exists to chase — except here it *is*
labeled and verified.

## What it is

A **Merkle-gated airdrop claim** contract (OpenZeppelin StandardMerkleTree, double-hashed leaves).
Holders in an off-chain snapshot each `claim(account, amount, proof)` once; PRISM is transferred to
`account`, which (being non-excluded) then mirror-mints their fee-share NFTs in the hook.

## Trust surface (tiny, by design)

| Element | Type | Who controls | Live status |
|---|---|---|---|
| `merkleRoot` | immutable | set at construction (off-chain tree) | fixed — `0x2cd6…e12f` |
| `deployer` | immutable | `0xfe76…f110` | can only call `setToken` |
| `setToken(token)` | deployer-only, one-shot | deployer | **DEAD** — `tokenFinal` = true |
| `token` | set once | deployer | = the hook `0xcf4d…e040` ✅ |
| `claim(...)` | **permissionless** | anyone (funds → `account`) | live |
| sweep / admin withdraw | — | — | **does not exist** |

## Outward graph

`PrismMigration` reaches **only the hook** — it calls `token.transfer(...)` and
`token.balanceOf(...)`. It stores no other address, sends value nowhere else. **The graph does not
grow through it.**

## Live state (snapshot)

- `token` = `0xcf4d…e040` (the hook), `tokenFinal` = **true**, `deployer` = `0xfe76…f110`.
- PRISM held: **742.40** (of 4,454.68 minted ⇒ **3,712.27 already claimed out**).
- `TokenSet` fired exactly once (block 25,646,647) wiring the hook.

## Distribution evidence (see `live-state/events_summary.json`)

- **321 `Claimed` events → 321 distinct recipients** — a genuine broad airdrop.
- Largest claims **287.24** and **228.04 PRISM** — these match the two figures the *hook's own
  source* cites as the largest holders of its published snapshot, so the on-chain root corresponds to
  the advertised tree.

## Notable design guards (from source, cross-read with the hook)

- `setToken` requires the candidate to be a deployed contract **and** to already hold this vault's
  reserve (`balanceOf(this) != 0`) — rejects a bare-fallback contract that would "succeed with
  nothing."
- `claim` uses a **behavioural** transfer check: it verifies the vault's balance actually fell by
  `amount` (not just a truthy return), catching a permissive-fallback token. The source is explicit
  that this guards against *error*, not against a hostile `setToken` — which is instead bounded by
  `setToken` being deployer-only + one-shot.
- CEI ordering: `claimed[account]` and `tokenFinal` latch before the external transfer;
  `tokenFinal` latches only **after** the proof verifies (so a bogus claim can't end the correction
  window).

## Residual (→ `UNRESOLVED.md` U-1)

The off-chain tree's **unclaimed** leaves are not enumerable from chain state. Worst case if the root
were crafted maliciously is bounded to **≤742.40 PRISM** (no sweep; token locked), with realizable
value further capped by the shallow pool depth.
