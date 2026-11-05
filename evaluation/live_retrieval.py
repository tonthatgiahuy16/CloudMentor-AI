from pathlib import Path

from app.core import config


def collect_observations(
    dataset,
    subject_ids,
    embedder,
    retriever,
    diagnostic_include_filtered=False,
):
    sources_by_filename = {
        Path(source["path"]).name: source["source_id"]
        for source in dataset["sources"]
    }
    observations = []
    for case in dataset["cases"]:
        subject_id = subject_ids.get(case["subject_key"])
        if not subject_id:
            raise ValueError(f"missing subject_id: {case['subject_key']}")
        results = retriever.search(
            embedder.embed_query(case["question"]),
            subject_id=subject_id,
            **(
                {"threshold": float("inf")}
                if diagnostic_include_filtered
                else {}
            ),
        )
        evidence = []
        diagnostic_results = []
        for rank, result in enumerate(results, start=1):
            metadata = result.get("metadata") or {}
            source_id = sources_by_filename.get(metadata.get("source"))
            if not source_id:
                continue
            item = {"source_id": source_id}
            if metadata.get("page") is not None:
                item["page"] = metadata["page"]
            elif metadata.get("line_start") is not None:
                item["line_range"] = [metadata["line_start"], metadata["line_end"]]
            elif metadata.get("paragraph_start") is not None:
                item["paragraph_range"] = [metadata["paragraph_start"], metadata["paragraph_end"]]
            else:
                continue
            if result.get("distance", 0) <= config.SIMILARITY_THRESHOLD:
                evidence.append(item)
            if diagnostic_include_filtered:
                diagnostic_results.append({
                    **item,
                    "rank": rank,
                    "distance": result.get("distance"),
                    "chunk_id": result.get("chunk_id"),
                    "document_id": metadata.get("document_id"),
                })
        observation = {"case_id": case["case_id"], "retrieved_evidence": evidence}
        if diagnostic_include_filtered:
            observation["diagnostic_results"] = diagnostic_results
        observations.append(observation)
    return {"observations": observations}
