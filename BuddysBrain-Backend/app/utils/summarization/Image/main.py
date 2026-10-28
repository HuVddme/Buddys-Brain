import os
import base64
import mimetypes

from ...processing import ProcessingError, get_ai_client


def summarize_image(image_path: str) -> str:
    """
    Accepts an image path (whiteboard, handwritten notes, scanned doc, etc.)
    and returns a summary of the **educational content** inside the image.
    """
    # Read image and encode to base64
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None or not mime_type.startswith("image/"):
        raise ValueError("Unsupported or invalid image format.")

    # Create data URL
    data_url = f"data:{mime_type};base64,{base64_image}"

    # GPT-4o Vision API Call
    response = get_ai_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You help students by summarizing the academic or technical content within images."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "The following is an image of a student-uploaded educational resource. "
                            "Please summarize the **subject matter and content** presented within the image. "
                            "This may include explanations, math steps, diagrams, definitions, or bullet points. "
                            "**Do not describe the image layout or style — only focus on the meaning and educational value.** "
                            "Keep it under 200 words and write clearly for a student audience."
                        )
                    },
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        max_tokens=500,
        temperature=0.3
    )

    return response.choices[0].message.content.strip()
