from fastapi import APIRouter
from ..models import SearchQuery
from ..utils.embeddings import get_embedding
from ..database import collection
import tiktoken

from ..utils.processing import get_ai_client, run_processing

MODEL = "gpt-4o"
MAX_INPUT_TOKENS = 100_000
MAX_OUTPUT_TOKENS = 500

router = APIRouter()

def tokenize_count(text: str) -> int:
    enc = tiktoken.encoding_for_model(MODEL)
    return len(enc.encode(text))

def summarize_resources(json_data, query: str) -> str:
    if not json_data:
        prompt = (
            f"Sorry, I don't have any information about '{query}'. However, from what I've gathered from the internet, "
            f"please provide a short summary."
        )
    else:
        summaries = [resource['summary'] for resource in json_data]
        combined_summaries = " ".join(summaries)
        token_count = tokenize_count(combined_summaries)

        if token_count > MAX_INPUT_TOKENS:
            raise ValueError(f"Input data too large to process in one shot (>{MAX_INPUT_TOKENS} tokens).")

        prompt = (
            f"Given the following educational resource summaries:\n{combined_summaries}\n\n"
            f"Provide a concise, short, clear, 3-sentence explanation of '{query}'."
        )

    response = get_ai_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You summarize educational resources concisely and clearly."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=MAX_OUTPUT_TOKENS
    )

    return response.choices[0].message.content.strip()

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
