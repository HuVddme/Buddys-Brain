"""Run with python -m app.services.cli_search from the backend."""
import json

from .ai import generate_summary

MAX_OUTPUT_TOKENS = 500

def load_json(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def summarize_resources(json_data, query: str) -> str:
    summaries = [resource['summary'] for resource in json_data]
    combined_summaries = " ".join(summaries)
    prompt = (
        f"Given the following educational resource summaries:\n{combined_summaries}\n\n"
        f"Provide a concise, clear, 5-sentence explanation of '{query}'."
    )

    return generate_summary(
        messages=[
            {"role": "system", "content": "You summarize educational resources concisely and clearly."},
            {"role": "user", "content": prompt}
        ],
        max_output_tokens=MAX_OUTPUT_TOKENS
    )

def main():
    json_data = load_json('resources.json')
    query = input("Enter your search query: ")
    summary = summarize_resources(json_data, query)
    print("\nGenerated Summary:")
    print(summary)

if __name__ == "__main__":
    main()
