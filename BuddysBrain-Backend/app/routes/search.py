from fastapi import APIRouter
from ..models import SearchQuery
from ..utils.embeddings import get_embedding
from ..database import collection

from ..utils.processing import run_processing
from ..utils.ai import generate_summary

MAX_OUTPUT_TOKENS = 500

router = APIRouter()

def summarize_resources(json_data, query: str) -> str:
    if not json_data:
        prompt = (
            "No matching resources were found in the library. Clearly state that your answer "
            "comes from general knowledge, not retrieved documents or a live web search. "
            f"Give a short explanation of: {query}"
        )
    else:
        summaries = [resource['summary'] for resource in json_data]
        combined_summaries = " ".join(summaries)
        prompt = (
            f"Given the following educational resource summaries:\n{combined_summaries}\n\n"
            f"Provide a concise, short, clear, 3-sentence explanation of '{query}'."
        )

    return generate_summary(
        messages=[
            {"role": "system", "content": "You summarize educational resources concisely and clearly."},
            {"role": "user", "content": prompt}
        ],
        max_output_tokens=MAX_OUTPUT_TOKENS
    )

@router.post("/search")
async def vector_search_and_summarize(payload: SearchQuery):
    query_vector = await run_processing(get_embedding, payload.query)

    pipeline = [
        {"$vectorSearch": {
            "index": "BuddysBrainIndex",
            "path": "embedding",
            "queryVector": query_vector,
            "numCandidates": 100,
            "limit": 100
        }},
        {"$project": {
            "title": 1,
            "summary": 1,
            "media_link": 1,
            "media_type": 1,
            "course": 1,
            "score": {"$meta": "vectorSearchScore"}
        }},
        {"$match": {"score": {"$gt": 0.7}}},
        {"$sort": {"score": -1}},
        {"$limit": 10}
    ]

    cursor = collection.aggregate(pipeline)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)

    summary = await run_processing(summarize_resources, results, payload.query)

    return {"summary": summary, "results": results}
