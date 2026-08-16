# Integrity of shared building blocks

Goal: make sure a diff-based review isn't blinded by a doctored baseline. Every Solady / Uniswap-V4 /
Permit2 file bundled inside the **target's own verified source** was checked **against real upstream**
— the actual on-chain Uniswap deployments and the official GitHub repos — **not** against a copy that
shipped with the project. Reproduce: [`../tools/integrity_v3.py`](../tools/) (on-chain) and
`integrity_github.py` (GitHub).

## Method

1. **On-chain cross-check** — hash every library file in `contracts/target/` and compare to the
   *same* file inside the real deployed **PoolManager**, **PositionManager**, **Permit2**, and
   **StateView** verified source (ground truth = the code actually running on mainnet).
   → `onchain_crosscheck.json`.
2. **GitHub cross-check** — for files with no on-chain twin (Solady; the newer `PoolOperation.sol`)
   or that differed on-chain, fetch from `Vectorized/solady`, `Uniswap/v4-core`, `Uniswap/v4-periphery`
   `main` and compare. → `github_crosscheck.json`.
3. Any non-identical file is **diffed** and the diff saved under [`diffs/`](diffs/).

## Results

| Bucket | Count | Verdict |
|---|--:|---|
| Byte-identical to **real on-chain Uniswap** | **30 / 42** | ✅ genuine |
| Byte-identical to **GitHub upstream `main`** (of the remaining 12) | **8 / 12** | ✅ genuine |
| Differ from current `main` — **benign version drift only** | 4 | ✅ explained, diffed |
| **Quietly altered / suspicious** | **0** | ✅ none found |

### Value-bearing files are clean
`solady/tokens/ERC20.sol`, `solady/auth/Ownable.sol`, `solady/utils/ReentrancyGuard.sol` —
**byte-identical to Solady `main`.** These govern the token's balances, auth, and reentrancy; none is
modified. All Uniswap V4 **core interfaces & libraries** used in the value path
(`IHooks`, `IPoolManager`, `Hooks`, `PoolOperation`, `TransientStateLibrary`, `Currency`, types, etc.)
are identical to on-chain and/or `main`.

### The 4 benign differences (diffs in `diffs/`)
- **`solady/utils/Base64.sol`** — one function signature single-lined vs wrapped. Formatting only.
- **`solady/utils/LibString.sol`, `LibBytes.sol`** — signature line-wrapping + internal variable
  renames (`needleLen`→`searchLen`, loop var names). No logic change. Metadata-only string/bytes
  utilities (used by on-chain SVG art); touch no value.
- **`v4-periphery/libraries/Actions.sol`** — current `main` *adds* constants
  (`UNWIND_WITH_FALLBACK`, `SUBSCRIBE`, `UNSUBSCRIBE`) the target's older pinned copy lacks. Nothing
  removed or altered.

### Version-drift note (why some on-chain copies "differ")
The target pins a **newer v4-core** than the deployed PoolManager was compiled with:
`ModifyLiquidityParams`/`SwapParams` were extracted from `IPoolManager` into `types/PoolOperation.sol`
upstream. So `IHooks.sol`/`IPoolManager.sol` differ from the *older deployed* PoolManager but are
**identical to v4-core `main`** — see `diffs/v4core_IHooks_target_vs_deployedPOSM.diff`. This is
upstream evolution, ABI-compatible with the deployed singleton, not tampering.

## Also verified
- **PrismMirror**: the independently-verified deployed source (`0xc1e6…bacc`) is **byte-identical**
  to the `PrismMirror.sol` bundled in the target tree.
- **No proxies** anywhere in the graph — every `_meta.json` shows `Proxy=0`, `Implementation=""`, so
  "the implementation is the shell" holds for all; nothing to resolve through.
