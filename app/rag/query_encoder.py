from sentence_transformers import SentenceTransformer


class QueryEncoder:

    def __init__(self):

        self.model = SentenceTransformer(
            "BAAI/bge-m3"
        )


    def encode(
        self,
        query: str
    ):

        return self.model.encode(query)