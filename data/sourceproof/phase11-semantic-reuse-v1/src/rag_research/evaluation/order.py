"""Reproducible permutations and five real same-order trials, sharing one call."""

import random

from rag_research.experiments.frozen_trace import digest, require


def trial_plan(trace, config):
    spec = config["trials"]
    require(spec["order_conditions"] ==
            ["original", "reversed", "shuffle_1", "shuffle_2", "shuffle_3"],
            "Unsupported order conditions")
    original = [d["passage_id"] for d in trace["documents"]]
    seed = int(digest([spec["shuffle_seed"], trace["record_id"]]), 16)
    rng = random.Random(seed)
    candidates = [("original", original), ("reversed", original[::-1])]
    for index in range(1, 4):
        ids = list(original)
        rng.shuffle(ids)
        candidates.append((f"shuffle_{index}", ids))
    trials, seen, aliases, order_group = [], {}, {}, []
    for name, ids in candidates:
        key = tuple(ids)
        if key in seen:
            aliases[name] = seen[key]
            continue
        seen[key] = name
        order_group.append(name)
        trials.append({"trial_id": name, "document_ids": ids})
    repeat_group = ["original"]
    for index in range(2, spec["same_order_total_trials"] + 1):
        name = f"repeat_{index}"
        repeat_group.append(name)
        trials.append({"trial_id": name, "document_ids": list(original)})
    rng = random.Random(int(digest([spec["execution_order_seed"], trace["record_id"]]), 16))
    rng.shuffle(trials)
    return {"trials": trials, "order_group": order_group, "repeat_group": repeat_group,
            "duplicate_order_aliases": aliases, "unique_order_count": len(order_group)}
