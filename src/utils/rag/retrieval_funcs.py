"""
This script has functions related to:
- keyword search using BM25
- dense/bi-encoder search using Chroma vector store
- Reciprocal Rank Fusion (RRF) to combine results from multiple retrievers
- cross-encoder re-ranking of a small candidate pool
"""


import re
from langchain_core.documents import Document
from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi
from collections import defaultdict
from sentence_transformers import CrossEncoder


def retrieval_pipeline(query: str, vector_store: Chroma, collection_name: str):
    """
    Retrieves relevant documents for a given query using a combination of
    BM25 keyword search, dense vector search, Reciprocal Rank Fusion (RRF),
    and cross-encoder re-ranking.

    Args:
        query (str): The search query.
        vector_store (Chroma): The Chroma vector store instance.
        collection_name (str): The name of the collection in the vector store.
    Returns:
        list[Document]: A list of the top-ranked Document objects.
    """

    # initialize the vector store if not already provided
    if vector_store is None:
        vector_store = get_vector_store(collection_name=collection_name)

    # load all documents from the vector store
    documents = load_documents_from_vector_store(vector_store)
    print(f"Loaded {len(documents)} documents from vector store '{collection_name}' for retrieval.")

    # build the BM25 index and create a lookup dictionary for documents by their IDs
    bm25_index, bm25_doc_ids = build_bm25_index(documents)
    doc_lookup = {doc.id: doc for doc in documents}  # for looking up full Documents by id later

    # run keyword search (BM25) and dense search (bi-encoder) to get candidate pools
    bm25_results = bm25_search(bm25_index, bm25_doc_ids, query, k=10)
    bi_encoder_results = bi_encoder_search(vector_store, query, k=10)
    print("Ran BM25 and bi-encoder searches.")

    # running RRF on the two candidate pools to get a fused top-N list
    fused_results = reciprocal_rank_fusion(
        ranked_lists=[bm25_results, bi_encoder_results],
        list_names=["bm25", "bi_encoder"],
        k=60,
        top_n=10,   # feed the cross-encoder a slightly wider pool than the final answer needs
    )
    print("Fused results with RPF")

    # create a CrossEncoder instance for re-ranking the fused results
    cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    # rerank the fused top-N with the cross-encoder to get the final top-5 results
    ce_ranked_results = cross_encoder_rerank(cross_encoder, query, fused_results, doc_lookup, top_n=5)
    print("Ran cross-encoder re-ranking on fused results.")
    print("\nTotal number of documents retrieved: ", len(ce_ranked_results))

    # retrieve the final top-ranked Document objects based on the cross-encoder's ranking
    final_results = []

    for r in ce_ranked_results:
        doc = doc_lookup[r["doc_id"]]

        enriched_metadata = {
            **doc.metadata
        }

        final_results.append(Document(page_content=doc.page_content, metadata=enriched_metadata, id=doc.id))

    # finally once we have results, we need to format it in a way that can be used by the LLM prompt template
    formatted_context = format_retrieved_context(final_results)

    return formatted_context

def load_documents_from_vector_store(vector_store: Chroma) -> list[Document]:
    """
    Loads all documents from the specified Chroma vector store.

    Args:
        vector_store (Chroma): The Chroma vector store instance to load documents from.
    Returns:
        list[Document]: A list of Document objects reconstructed from the vector store.
    """
    
    raw = vector_store.get(include=["documents", "metadatas"])

    return [
        Document(page_content=text, metadata=metadata, id=doc_id)
        for doc_id, text, metadata in zip(raw["ids"], raw["documents"], raw["metadatas"])
    ]


def format_retrieved_context(documents: list[Document]) -> str:
    """
    Formats a list of retrieved Document chunks into a single block of text
    for the RAG prompt, with each chunk labeled by its source so the LLM can
    cite it and the engineer can trace claims back to the source doc.

    Args:
        documents (list[Document]): retrieved chunks, e.g. the output of
            retrieval_pipeline() — page_content already prefixed with
            "{title} — {section}", metadata carries doc_type/source_file/etc.

    Returns:
        str: a formatted context block, or a clear "no context" message if
             the list is empty (the system prompt's grounding rules tell the
             LLM what to do when it sees that message).
    """
    if not documents:
        return "No relevant runbooks, postmortems, or service docs were retrieved for this query."

    formatted_chunks = []
    for i, doc in enumerate(documents, start=1):
        doc_type = doc.metadata.get("doc_type", "document")
        source_file = doc.metadata.get("source_file", "unknown source")
        formatted_chunks.append(
            f"[Source {i} | type: {doc_type} | file: {source_file}]\n{doc.page_content}"
        )

    return "\n\n".join(formatted_chunks)


# ----------------------- keyword search functions -----------------------

# function to tokenize text into a list of lowercased tokens, keeping certain patterns intact
def tokenize(text: str) -> list[str]:
    """
    Lowercases and splits into tokens, keeping things like 'v2.1.0',
    '#platform-oncall', and 'INC-1001' intact as single tokens instead of
    fragmenting on '.', '-', '#' the way a plain \\w+ regex would.

    Args:
        text (str): The input text to tokenize.
    Returns:
        list[str]: A list of lowercased tokens extracted from the input text.
    """

    # regex pattern to match tokens, allowing for alphanumeric characters, underscores, periods, hyphens, and hash symbols
    TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.#-]*", re.IGNORECASE)

    return [t.lower() for t in TOKEN_PATTERN.findall(text)]


# function to build a BM25 index from a list of Document objects
def build_bm25_index(documents: list[Document]):
    """
    Builds a BM25 index over the corpus of Document chunks.

    Args:
        documents (list[Document]): A list of Document objects to index.
    Returns:
        bm25: the fitted BM25Okapi index
        doc_ids: list of document ids, in the same order as the tokenized
                 corpus fed into BM25 (index i in bm25's scores corresponds
                 to doc_ids[i])
    """

    # tokenize the page content of each document to create a tokenized corpus
    tokenized_corpus = [tokenize(doc.page_content) for doc in documents]

    # create a list of document IDs corresponding to the tokenized corpus
    doc_ids = [doc.id for doc in documents]

    # create a BM25 index using the tokenized corpus
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, doc_ids

# function to perform a BM25 keyword search and return the top-k results
def bm25_search(bm25: BM25Okapi, doc_ids: list[str], query: str, k: int = 10) -> list[dict]:
    """
    Runs a BM25 keyword search and returns the top-k results.
    Higher score = more relevant.

    Returns:
        list[dict]: [{"doc_id": ..., "score": ..., "rank": 1}, ...] best first
    """

    # tokenize the query to prepare it for scoring against the BM25 index
    tokenized_query = tokenize(query)

    # get the BM25 scores for the tokenized query against the indexed documents
    scores = bm25.get_scores(tokenized_query)

    # sort the document indices by their scores in descending order and select the top-k indices
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    # return a list of dictionaries containing the document ID, score, and rank for the top-k results
    return [
        {"doc_id": doc_ids[i], "score": float(scores[i]), "rank": rank}
        for rank, i in enumerate(ranked_indices, start=1)
    ]


# ----------------------- dense/bi-encoder search functions -----------------------

# function to perform a dense/bi-encoder similarity search against the Chroma vector store
def bi_encoder_search(vector_store: Chroma, query: str, k: int = 10) -> list[dict]:
    """
    Runs a dense/bi-encoder similarity search against the Chroma vector store.
    NOTE: Chroma returns a distance, not a similarity — lower score = more
    relevant here, the opposite direction from BM25's score above.

    Args:
        vector_store (Chroma): The Chroma vector store instance to search against.
        query (str): The query string to search for.
        k (int): The number of top results to return. Default is 10.
    Returns:
        list[dict]: [{"doc_id": ..., "score": ..., "rank": 1}, ...] best first
    """

    # run the similarity search with score using the provided query and number of top results (k)
    results = vector_store.similarity_search_with_score(query, k=k)

    # return a list of dictionaries containing the document ID, score, and rank for the top-k results
    return [
        {"doc_id": doc.id, "score": float(score), "rank": rank}
        for rank, (doc, score) in enumerate(results, start=1)
    ]


# ----------------------- Reciprocal Rank Fusion (RRF) -----------------------

# function to perform Reciprocal Rank Fusion (RRF) on multiple ranked result lists
def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    list_names: list[str] = ["bm25", "bi_encoder"],
    k: int = 60,
    top_n: int = 10,
) -> list[dict]:
    """
    Fuses multiple ranked result lists into one ranking using Reciprocal
    Rank Fusion (RRF). Uses only each list's RANK, never its raw score.

    RRF score for a doc = sum over every list it appears in of 1 / (k + rank)

    Args:
        ranked_lists: e.g. [bm25_results, bi_encoder_results], each a list
                      of {"doc_id", "score", "rank"} dicts, best first.
        list_names: optional labels per list (e.g. ["bm25", "bi_encoder"]),
                    used to record which retriever(s) surfaced each doc.
        k: RRF constant — dampens how much a #1 rank dominates over a #2.
              60 is the standard default from the original RRF paper.
        top_n: how many fused results to return.

    Returns:
        list[dict]: [{"doc_id", "rrf_score", "rank", "found_in": [...]}]
                    sorted best first.
    """

    # dict to hold the summed RRF scores for each document ID
    fused_scores: dict[str, float] = defaultdict(float)   # doc_id -> summed RRF score
    
    # dict to hold which lists/ranks each document ID was found in
    found_in: dict[str, list[str]] = defaultdict(list) 

    # iterate through each ranked list and accumulate RRF scores for each document
    for list_name, ranked_list in zip(list_names, ranked_lists):
        for item in ranked_list:
            doc_id = item["doc_id"]
            rank = item["rank"]
            fused_scores[doc_id] += 1 / (k + rank)         # accumulate — a doc in both lists gets both contributions
            found_in[doc_id].append(f"{list_name}#{rank}")  # e.g. "bm25#2"

    # sort all doc_ids that appeared in ANY list by their fused score, best first
    ranked_doc_ids = sorted(fused_scores.keys(), key=lambda d: fused_scores[d], reverse=True)[:top_n]

    return [
        {
            "doc_id": doc_id,
            "rrf_score": fused_scores[doc_id],
            "rank": rank,
            "found_in": found_in[doc_id],
        }
        for rank, doc_id in enumerate(ranked_doc_ids, start=1)
    ]


# ----------------------- cross-encoder re-ranking -----------------------

# function to rerank a small candidate pool using a cross-encoder model
def cross_encoder_rerank(
    cross_encoder: CrossEncoder,
    query: str,
    candidates: list[dict],
    doc_lookup: dict,
    top_n: int = 5,
) -> list[dict]:
    """
    Reranks a small candidate pool (e.g. RRF's fused top-10/15) using a
    cross-encoder, which scores each (query, doc) pair jointly instead of
    comparing pre-computed vectors. Only ever call this on a short list —
    it does NOT scale to running over the whole corpus.

    Args:
        cross_encoder: a sentence-transformers CrossEncoder instance
        query: the original user query string
        candidates: a list of {"doc_id", "score", "rank", ...} dicts to rerank
        doc_lookup: a dict mapping doc_id -> Document, used to get the text for each candidate
        top_n: how many reranked results to return

    Returns:
        list[dict]: candidates enriched with cross_encoder_score, re-sorted,
                    re-ranked, keeping the RRF/found_in history for traceability.
    """
    # build (query, chunk_text) pairs — one per candidate
    pairs = [(query, doc_lookup[c["doc_id"]].page_content) for c in candidates]

    # score all pairs in one batched call — higher score = more relevant
    scores = cross_encoder.predict(pairs)

    # attach each candidate's cross-encoder score to its existing dict
    # (keeps rrf_score/found_in around so you can see how the ranking moved)
    scored_candidates = [
        {**candidate, "cross_encoder_score": float(score)}
        for candidate, score in zip(candidates, scores)
    ]

    # re-sort by the cross-encoder's opinion, highest first
    reranked = sorted(scored_candidates, key=lambda c: c["cross_encoder_score"], reverse=True)[:top_n]

    # re-number rank 1..top_n based on the NEW order
    for rank, c in enumerate(reranked, start=1):
        c["rank"] = rank

    return reranked
