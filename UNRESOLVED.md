# UNRESOLVED — what the chain cannot close

This is the explicit, prominent list the audit must carry forward. Everything **in the value path
resolved to verified source** — no contract required decompilation, no address in the graph is an
opaque blob. What remains is off-chain, or is an on-chain fact whose *meaning* lives off-chain. Each
item names the decision it controls, what goes wrong if that decision is wrong/compromised, and the
on-chain evidence that bounds it.

---

## U-1 — The migration Merkle snapshot (the one off-chain component in the trust path)

- **What it is.** `PrismMigration` (`0xdf0a…9d47`) releases PRISM only to `(account, amount)` pairs
  that verify against the immutable `merkleRoot = 0x2cd60218d3f802a855996dbcbf7db5db860f88c541468c7601e02e627d33e12f`
  (OpenZeppelin StandardMerkleTree, double-hashed leaves). **The tree itself is off-chain** — the
  chain stores only the root and the leaves that have already been claimed.
- **What it controls.** Who may claim the **742.40 PRISM still in the vault** (≈3.7% of total
  supply), plus, historically, the 3,712.27 PRISM already distributed.
- **What goes wrong if it's wrong.** If the deployer built the root to include a large allocation to
  an address they control that has **not yet claimed**, they could still `claim` up to the unclaimed
  remainder to themselves. **Bound: ≤ 742.40 PRISM** — the vault has **no sweep** and can never pay
  more than its balance, and `tokenFinal` is locked so the payout token can't be swapped for
  something else. Nominal mark ~0.32 ETH/PRISM, but realizable value is far lower and
  **liquidity-bounded** (the host pool holds only ~216 PRISM of depth; dumping 742 PRISM would crash
  the price long before realizing the mark).
- **Evidence gathered (bounds it, doesn't close it).** [`live-state/events_summary.json`](live-state/events_summary.json):
  - **321 `Claimed` events → 321 distinct recipients**, total 3,712.27 PRISM — a real broad
    distribution, not a single-address drain.
  - The two largest on-chain claims (**287.24** and **228.04 PRISM**) **exactly match** the figures
    PrismHookV2's own source names as the two largest holders of its *published* snapshot — so the
    live root corresponds to the advertised tree, at least at the top.
- **The open question for the audit.** *Enumerate the unclaimed leaves of the published tree and
  confirm the remaining 742.40 PRISM is allocated to independent snapshot holders, not to a
  deployer-controlled address.* Requires the off-chain tree/snapshot file (publisher: the Prism
  project — `github.com/0xsolazy`, `prism.0xsolazy.eth.limo`). Not resolvable from chain state alone.

## U-2 — `pokeFees()` collection cadence (off-chain operational assumption)

- **What it is.** Fee fairness relies on fees being **collected often**. The source states repeatedly
  that a late-minted fee-share can otherwise skim a compounding backlog ("swap-path fee-timing
  residual"), and that a failed collect must be alarmed on (`PokeCollectFailed`).
- **What it controls.** How much accrued-but-uncollected fee sits in the V4 position between pokes.
- **What goes wrong if neglected.** No funds are lost to an admin — but a share minted just before a
  large delayed collection can capture fees it didn't earn, diluting honest holders. This is a
  documented, bounded fairness residual, not an admin drain.
- **Why it's only an assumption, not a hole.** `pokeFees()` is **permissionless** — anyone can call
  it, and `claim`/`claimMany` call it first — but **nobody is obligated to**. There is no on-chain
  keeper guarantee.
- **Evidence.** `PokeCollectFailed` events = **0** (every collect has succeeded); ≥1,000
  `PendingCredited` and 138 `PendingWithdrawn` events (the system is actively poked in practice).
- **Open question.** *Is there a keeper, and what is its real cadence?* Off-chain/operational.

## U-3 — Deployer EOA `0xfe76f05a01163e5c90329a0d1a2c8e389fd0f110` (private key)

- **Status: no live protocol power.** It was the hook `owner` (now **renounced**, `owner()` = 0) and
  the migration `deployer` (its only power, `setToken`, is **locked** by `tokenFinal`). Empirically
  confirmed: `seed(...)` and `setToken(...)` both revert for this address ([simulations](simulations/permissionless_caller_matrix.json)).
- **What a key compromise would yield.** Only the deployer's *own* holdings (1.67 PRISM + 1
  fee-share NFT) and its ability to submit *valid* migration proofs on behalf of listed accounts
  (funds still go to `account`, not the submitter). **It cannot touch the pool, the hook's funds, or
  re-point/relock anything.** Named here only because it is the historical root of trust and the
  chooser of the U-1 merkle root.
- Code type verified: `eth_getCode` = empty ⇒ plain EOA (no contract, no EIP-7702 delegation at
  snapshot).

## U-4 — Uniswap V4 / Permit2 as trusted infrastructure (canonical, not novel)

- The target trusts the canonical mainnet **PoolManager**, **PositionManager**, and **Permit2** with
  the pool reserves, the LP position, and a standing pull allowance. Their full source is in
  [`contracts/dependencies/`](contracts/dependencies/) and integrity-checked in
  [`integrity/`](integrity/). These are industry-standard, widely-audited singletons — flagged for
  completeness, not as a bespoke risk. No proxies (all direct implementations; `Proxy=0`).

---

## Explicitly NOT unresolved (closed by this bundle)

- **No unverified contract in the graph.** Target, PrismMigration, PrismMirror, PoolManager, POSM,
  Permit2, StateView are **all verified**; PrismArt is an **inlined** library (no separate address).
  Nothing needed bytecode recovery/decompilation.
- **No hidden proxy.** Every resolved contract is a direct implementation (`_meta.json` `Proxy=0`,
  `Implementation=""`), including the target.
- **No live admin / upgrade / pause / fee-setter.** The hook has no such functions (only `seed`
  = onlyOwner-dead, `handle*` = onlyMirror-forwarding, pool callbacks = onlyPoolManager); owner is
  renounced. All wired dependency addresses are `immutable` — no setters exist to re-point them.
- **No second contract with authority over PRISM beyond the enumerated Permit2→POSM allowance.**
  The systemic approval surface is: hook→Permit2 (infinite, required by Solady) and Permit2→POSM
  (≤4,454.68 PRISM, bounded by hook balance). Individual holders' own approvals to third-party
  routers/marketplaces are ordinary per-user DeFi risk, out of scope for the token's trust graph.
