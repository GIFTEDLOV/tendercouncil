# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Small nondeterministic-boundary probes used by the Stage 1 investigation."""

import json

from genlayer import *


class EvaluatorProbe(gl.Contract):
    def __init__(self):
        pass

    @gl.public.write
    def probe_a(self):
        def leader_fn():
            return {"probe": "A", "value": 7}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            return leader_result.calldata == {"probe": "A", "value": 7}

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def probe_b(self, url: str):
        def leader_fn():
            body = gl.nondet.web.get(url).body
            return {"probe": "B", "body": body.decode("utf-8")[:64]}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            body = gl.nondet.web.get(url).body.decode("utf-8")[:64]
            return leader_result.calldata == {"probe": "B", "body": body}

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def probe_c(self):
        def leader_fn():
            return gl.nondet.exec_prompt(
                "Return JSON with exactly {probe: C, value: 11}.",
                response_format="json",
            )

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            own = gl.nondet.exec_prompt(
                "Return JSON with exactly {probe: C, value: 11}.",
                response_format="json",
            )
            return (
                own.get("probe") == "C"
                and own.get("value") == 11
                and leader_result.calldata.get("probe") == "C"
                and leader_result.calldata.get("value") == 11
            )

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def probe_d(self, url: str):
        def leader_fn():
            body = gl.nondet.web.get(url).body.decode("utf-8")[:64]
            result = gl.nondet.exec_prompt(
                "Return JSON with exactly {probe: D, supported: true}.",
                response_format="json",
            )
            return {"probe": "D", "body_len": len(body), "supported": result.get("supported")}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            body = gl.nondet.web.get(url).body.decode("utf-8")[:64]
            result = gl.nondet.exec_prompt(
                "Return JSON with exactly {probe: D, supported: true}.",
                response_format="json",
            )
            return leader_result.calldata == {
                "probe": "D",
                "body_len": len(body),
                "supported": result.get("supported"),
            }

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def probe_e(self, url: str, tender_text: str, bid_text: str):
        stable_url = str(url)
        stable_tender = str(tender_text)
        stable_bid = str(bid_text)

        def leader_fn():
            body = gl.nondet.web.get(stable_url).body.decode("utf-8")[:64]
            prompt = (
                "Return JSON with exactly {probe: E, supported: true}. "
                + json.dumps(
                    {"tender": stable_tender, "bid": stable_bid, "body": body},
                    sort_keys=True,
                )
            )
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            return {"probe": "E", "supported": result.get("supported"), "body_len": len(body)}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            body = gl.nondet.web.get(stable_url).body.decode("utf-8")[:64]
            prompt = (
                "Return JSON with exactly {probe: E, supported: true}. "
                + json.dumps(
                    {"tender": stable_tender, "bid": stable_bid, "body": body},
                    sort_keys=True,
                )
            )
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            return leader_result.calldata == {
                "probe": "E",
                "supported": result.get("supported"),
                "body_len": len(body),
            }

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def probe_f(self, url: str, tender_text: str, bid_text: str, source_json: str):
        stable_url = str(url)
        stable_context = json.dumps(
            {"tender": str(tender_text), "bid": str(bid_text)}, sort_keys=True
        )
        stable_sources = str(source_json)

        def leader_fn():
            sources = []
            for item in json.loads(stable_sources):
                body = gl.nondet.web.get(item["uri"]).body.decode("utf-8")[:64]
                sources.append({"uri": item["uri"], "body": body})
            context = json.loads(stable_context)
            result = gl.nondet.exec_prompt(
                "Return JSON with exactly {decision: ACCEPT, score: 80, evidence_count: 1}. "
                + json.dumps(
                    {"tender": context["tender"], "bid": context["bid"], "sources": sources},
                    sort_keys=True,
                ),
                response_format="json",
            )
            return {
                "decision": result.get("decision"),
                "score": result.get("score"),
                "evidence_count": len(sources),
            }

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            sources = []
            for item in json.loads(stable_sources):
                body = gl.nondet.web.get(item["uri"]).body.decode("utf-8")[:64]
                sources.append({"uri": item["uri"], "body": body})
            context = json.loads(stable_context)
            result = gl.nondet.exec_prompt(
                "Return JSON with exactly {decision: ACCEPT, score: 80, evidence_count: 1}. "
                + json.dumps(
                    {"tender": context["tender"], "bid": context["bid"], "sources": sources},
                    sort_keys=True,
                ),
                response_format="json",
            )
            return leader_result.calldata == {
                "decision": result.get("decision"),
                "score": result.get("score"),
                "evidence_count": len(sources),
            }

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
