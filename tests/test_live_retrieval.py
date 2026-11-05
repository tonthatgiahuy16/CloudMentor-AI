from evaluation.live_retrieval import collect_observations


class Embedder:
    def embed_query(self, _question): return [0.1]


class Retriever:
    def search(self, _embedding, subject_id, **_kwargs):
        return [{"chunk_id": "chunk-1", "distance": 0.2, "metadata": {"document_id": "doc-1", "source": "source.txt", "line_start": 2, "line_end": 3}}] if subject_id == "subject-1" else []


def test_collects_traceable_live_retrieval_observations():
    dataset = {"sources": [{"source_id": "source-1", "path": "fixtures/source.txt"}], "cases": [{"case_id": "case-1", "subject_key": "subject", "question": "What is the evidence?"}]}
    result = collect_observations(dataset, {"subject": "subject-1"}, Embedder(), Retriever())
    assert result == {"observations": [{"case_id": "case-1", "retrieved_evidence": [{"source_id": "source-1", "line_range": [2, 3]}]}]}


def test_diagnostic_keeps_filtered_chunks_out_of_production_evidence():
    class FilteredRetriever(Retriever):
        def search(self, *_args, **_kwargs):
            return [{"chunk_id": "chunk-2", "distance": 1.1, "metadata": {"document_id": "doc-2", "source": "source.txt", "line_start": 2, "line_end": 3}}]

    dataset = {"sources": [{"source_id": "source-1", "path": "fixtures/source.txt"}], "cases": [{"case_id": "case-1", "subject_key": "subject", "question": "Question"}]}
    result = collect_observations(dataset, {"subject": "subject-1"}, Embedder(), FilteredRetriever(), diagnostic_include_filtered=True)
    observation = result["observations"][0]
    assert observation["retrieved_evidence"] == []
    assert observation["diagnostic_results"][0]["rank"] == 1
    assert observation["diagnostic_results"][0]["distance"] == 1.1
