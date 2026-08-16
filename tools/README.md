# tools — reproducibility

The exact scripts used to gather every JSON artifact and integrity result in this repo. They use the
Etherscan V2 API (source, ABI, logs, `eth_call`/`eth_getCode` via the proxy module) and GitHub raw
(upstream integrity). Python 3.11 + `eth-abi` + `eth-hash[pycryptodome]`.

| Script | Produces |
|---|---|
| `ethlib.py` | shared helper: Etherscan V2 calls, throttled RPC, ABI encode/decode, keccak, storage-slot math |
| `save_contract.py` | fetch a verified contract's full source tree + `_meta.json`/`_abi.json` into a dir |
| `livestate.py` | `live-state/live_state.json` — hook/migration/pool/POSM/Permit2 reads |
| `events.py` | `live-state/events_summary.json` — claim/seed/fee event history & distribution |
| `simulate.py` | `simulations/permissionless_caller_matrix.json` — unprivileged-caller `eth_call` matrix |
| `integrity_v3.py` | on-chain library cross-check vs real deployed Uniswap/Permit2 |
| `integrity_github.py` | GitHub-upstream cross-check for Solady + remaining files |

An Etherscan V2 API key is required (`ETHERSCAN_KEY` in `ethlib.py`). All reads are at the
2026-08-16 snapshot; re-running reflects current chain state.
