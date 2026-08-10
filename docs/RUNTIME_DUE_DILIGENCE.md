# GenLayer runtime due diligence

Checked 2026-08-10 for TenderCouncil. This document records the runtime and
protocol conclusions used by the implementation; it is not a claim that a
local direct test replaces validator consensus.

## Official conclusions

- Intelligent Contracts combine deterministic contract state with explicitly
  nondeterministic web and LLM operations. Web and LLM calls must run inside a
  nondeterministic block, and storage writes, contract calls, message emits,
  and settlement effects must happen after the agreed result returns.
- The Equivalence Principle is leader/validator verification. A validator
  must independently reproduce or derive the decision; checking only the
  leader's JSON shape is not sufficient for ranking, scoring, authenticity, or
  settlement decisions.
- `run_nondet_unsafe` is the custom-validator primitive. Validator exceptions
  are not a substitute for application policy: the callback must fail closed
  and return `False` for malformed or non-equivalent results. `run_nondet` has
  built-in error comparison but is intended mainly for simpler wrappers.
- Structured LLM output via `response_format="json"` is supported, but the
  returned object remains untrusted model output and must be bounded and
  checked before state mutation.
- Payable methods use `@gl.public.write.payable` and `gl.message.value`.
  Value sent to another contract is asynchronous; use `on="finalized"` when a
  duplicate or premature child action would be unsafe.
- `ACCEPTED` is not protocol finality. A transaction can still be appealed
  during the finality window; only `FINALIZED` is irreversible. TenderCouncil's
  application response window is an additional product safeguard and does not
  replace protocol finality.

Primary references:

- https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism
- https://docs.genlayer.com/developers/intelligent-contracts/features/web-access
- https://docs.genlayer.com/developers/intelligent-contracts/features/calling-llms
- https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
- https://docs.genlayer.com/developers/intelligent-contracts/features/interacting-with-intelligent-contracts
- https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/transactions/transaction-statuses
- https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/finality
- https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/appeal-process
- https://docs.genlayer.com/developers/intelligent-contracts/testing
- https://docs.genlayer.com/developers/intelligent-contracts/deploying/deploy-scripts

## Installed local tooling

The working environment currently reports:

| Tool | Version/status |
|---|---|
| Python | 3.14.3 |
| `genlayer-test` package | 0.29.2 |
| `genlayer-py` package | 0.16.3 (the SDK is loaded into direct tests from the contract's pinned dependency) |
| `genvm-linter` package | 0.11.0 |
| `genlayer` CLI | 0.39.1 from the installed npm package; command startup was too slow for a short local version probe |
| Contract runner header | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Cached direct GenVM runners | v0.2.11, v0.2.11b, v0.2.11c, v0.2.16 |
| Current local lint/semantic validation | passes for the production contract |
| Current direct suite | 37 passed |

The direct loader confirms that the pinned contract header selects a specific
runner and standard-library dependency. It also patches nondeterministic
execution for in-process tests, so direct mode validates contract logic and
callback serialization but cannot prove Bradbury validator behavior.

## Hashing decision

The required application commitment is SHA-256 of the exact bytes returned by
the web response. The contract must hash the response bytes before UTF-8
decoding or semantic exposure. `hashlib.sha256` is present in the direct
Python environment, but direct mode alone is not sufficient evidence that a
cryptographic extension behaves identically inside every deployed GenVM.
Therefore the production contract will keep hashing in a small, pure-Python
SHA-256 routine using bounded bytes and integer operations, and will retain a
runtime probe for the installed `hashlib.sha256` behavior. The pure routine is
the consensus-critical implementation; the standard-library probe is
diagnostic, not authoritative.

## Boundary regression

The previous Bradbury failure was reproduced when `json.loads` reconstructed
lists/dictionaries inside the nondeterministic callback before web/LLM calls.
The safe pattern is now: prepare bounded primitive strings/tuples in the
deterministic contract context, use a separate custom-validator callback that
returns only `(status, bytes)` for each web fetch, perform exact hashing and
schema parsing after that result returns, and capture only immutable strings in
the later semantic callback. The semantic callback does not reconstruct storage
objects, source JSON lists, or JSON context containers before external calls.

The existing Bradbury probe artifacts remain preserved. A new Bradbury smoke
is not considered green until every validator agrees and the content hash is
actually checked.
