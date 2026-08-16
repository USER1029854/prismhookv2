# Live-state snapshot

On-chain reality the source can't show, captured **2026-08-16** via Etherscan V2 `eth_call` /
`eth_getStorageAt` / logs against Ethereum mainnet. Reproduce with
[`../tools/livestate.py`](../tools/) and `events.py`.

## Files

- **`live_state.json`** — hook, migration, pool, POSM-position, and Permit2 reads.
- **`events_summary.json`** — migration `Claimed`/`TokenSet`, hook `Seeded`/`PendingCredited`/
  `PendingWithdrawn`/`FeesForfeited`/`PokeCollectFailed` counts + distribution.
- **`binding_and_provenance.json`** — `mirror.hook()` binding + contract-creation (deployer, tx) for
  hook, mirror, migration.

## Key facts (all directly read)

| Fact | Value | Why it matters |
|---|---|---|
| Hook `owner()` | **`address(0)`** | Ownership renounced — no admin. |
| Migration `tokenFinal` / `token` | **true** / hook | Deployer's `setToken` power is dead; payout token locked to the hook. |
| Migration PRISM balance | **742.40** | Unclaimed airdrop remainder (≤ this is the U-1 bound). |
| Permit2 `allowance(hook,PRISM,POSM)` | **4,454.68** / exp uint48-max / nonce 0 | Standing pull allowance (bounded by hook balance; POSM canonical). |
| Hook ETH / PRISM | **3.17 ETH** / 13.26 PRISM | Undistributed fees held by hook (movable only via permissionless distribution to credited holders). |
| `totalShares` | **3,834** | Live fee-share NFT count = fee denominator. |
| Hook LP position | POSM **#356052**, `ownerOf` = hook | The hook owns its own V4 position. |
| Pool `getSlot0` tick | **11398** ⇒ ~**0.32 ETH/PRISM** | Matches DexScreener ~0.325 — pool real & correctly priced. |
| Pool `getLiquidity` | 204,958,960,128,548,666,643 | Active liquidity (raw L). |
| PoolManager PRISM balance | **215.95** | This pool's entire PRISM reserve (PRISM trades only here). |

### Supply reconciliation (totalSupply = 5,000 PRISM)

| Location | PRISM |
|---|---|
| Migration vault (unclaimed) | 742.40 |
| Pool (PoolManager) | 215.95 |
| Hook fee-reserve | 13.26 |
| Burn sink `0x…dEaD` | 8.78 |
| Deployer EOA | 1.67 |
| **Circulating (claimants/traders)** | **~4,017.94** |

## Notes on precision

- `PoolManager` ETH balance in `live_state.json` (~46,001 ETH) is the **singleton total across all V4
  pools**, *not* this pool's ETH — V4 commingles native ETH. This pool's ETH reserve must be derived
  from `getLiquidity` + the tick range (`globalTickLower=-887200`, `globalTickUpper=44800`); external
  aggregators put total pool value at ~$220–277k, consistent with the discovery note (~118 ETH).
  Left to the auditor rather than asserted here.
- Values are strings in JSON to preserve full uint256 precision.
