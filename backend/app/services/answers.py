"""Answer generation from retrieved resource summaries."""
from .ai import generate_summary

MAX_OUTPUT_TOKENS = 500


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
