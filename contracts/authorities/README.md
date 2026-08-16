# Authorities — what holds power over PrismHookV2

This is the "upstream" direction of the trust graph: things that can act on the target without
*being* the target. The rule applied is behavioural — *what could a share, an approval, a role, or a
key resting here actually do to the target's funds or rules* — not "does it have a familiar name."

**There are no separate contracts holding standing power over the target beyond canonical Uniswap
infrastructure.** The authorities are: a renounced owner (EOA), a spent deployer power (EOA), the
mirror (a pure forwarder), a bounded Permit2→POSM allowance, and one off-chain merkle root. Each is
below, with the on-chain evidence.

There is no source folder here because **none of these authorities is a bespoke contract** — they
are EOAs, an off-chain artifact, or already-present canonical dependencies. The contracts that *do*
carry authority (the mirror; the Uniswap contracts) have their full source under
[`../dependencies/`](../dependencies/).

---

## 1. Owner (`Ownable`) — RENOUNCED

- **Address:** `owner()` returns `0x0000000000000000000000000000000000000000`.
- **Every power it ever had:** the *only* `onlyOwner` function on the hook is `seed()`, used once to
  create the pool. There is no fee-setter, pause, upgrade, or sweep gated on the owner.
- **Live power now: none.** Ownership is renounced. Solady's ownership *handover* mechanism cannot
  revive it, because `completeOwnershipHandover` is itself `onlyOwner` and the owner is `address(0)`.
- **Evidence:** `seed(...)` reverts `Unauthorized()` from a stranger **and** from the ex-owner
  `0xfe76…f110` (`simulations/permissionless_caller_matrix.json`).

## 2. Deployer EOA `0xfe76f05a01163e5c90329a0d1a2c8e389fd0f110`

- Was tx.origin for the hook+mirror creation tx and for the migration-vault creation tx; is the
  migration `deployer`.
- **Migration `setToken` was its only privileged power** — correctable until the first claim, then
  permanently locked. `tokenFinal` is now **true**.
- **Live power now: none over the protocol.** `setToken(...)` reverts `TokenLocked()` even from this
  address. It still (a) holds its own 1.67 PRISM + 1 fee-share NFT and (b) can submit *valid*
  migration proofs — but claimed funds go to the listed `account`, not the submitter.
- **Code type:** `eth_getCode` empty ⇒ plain EOA, no EIP-7702 delegation at snapshot.
- Full residual discussion: [`../../UNRESOLVED.md`](../../UNRESOLVED.md) (U-3).

## 3. PrismMirror `0xc1e66f065ee0960e2ee4e1d7c1b3b48a9972bacc`

- Holds the `onlyMirror` privilege to call the hook's `handleNFTTransfer / handleNFTApprove /
  handleNFTSetApprovalForAll`. Source: [`../dependencies/PrismMirror/`](../dependencies/PrismMirror/).
- **Not an independent authority:** the mirror only ever *forwards* a real user's `msg.sender` to the
  hook as `caller`, and has no path that makes itself the caller (no self-call, no delegatecall in).
  It holds no funds.
- **Binding verified both ways:** `hook.mirror()` = this mirror **and** `mirror.hook()` = the hook.
  Both were created in the same tx; the mirror is a `new PrismMirror(address(this))` from the hook's
  constructor.
- **Evidence:** `handle*` reverts `MirrorOnly()` for any non-mirror caller
  (`simulations/permissionless_caller_matrix.json`).

## 4. Permit2 → POSM standing allowance

- At construction the hook set an **infinite ERC-20 allowance to Permit2** (required — Solady fixes
  canonical Permit2's allowance at infinity) and, via Permit2, a scoped allowance letting **POSM pull
  up to `SUPPLY` (5,000) PRISM**. Snapshot value: **4,454.68 PRISM remaining**, expiration = uint48
  max, nonce 0 (`live-state/live_state.json` → `permit2`).
- **Why it's bounded, not a drain:** POSM (canonical V4) only pulls PRISM during a
  `modifyLiquidities` that the **hook itself initiates** (`seed`, `pokeFees`), and can only ever pull
  what the hook actually holds (currently ~13.26 PRISM). It is not a third-party spender.

## 5. Merkle root (off-chain) — governs the migration vault's remaining PRISM

- Immutable `merkleRoot 0x2cd6…e12f` decides who claims the 742.40 PRISM still in `PrismMigration`.
  This is the single genuine off-chain authority in the trust path — see
  [`../../UNRESOLVED.md`](../../UNRESOLVED.md) (U-1) for the decision it controls, the ≤742.40 PRISM
  bound, and the distribution evidence.

---

### Powers that do **not** exist (checked, absent)

No upgradeability (not a proxy), no pause, no fee/parameter setter, no mint after construction (fixed
supply), no owner/admin sweep, no setter to re-point `POSM` / `PERMIT2` / `MIGRATION_VAULT` / `mirror`
(all `immutable`). The hook is immutable and, at this snapshot, admin-less.
