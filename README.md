# Buddy's Brain

Buddy's Brain is an intelligent, AI-powered educational assistant designed to help students quickly and effectively find relevant educational resources. It leverages advanced vector-based semantic search and OpenAI's GPT models to provide clear, concise summaries and explanations. Buddy's Brain also supports voice interactions through text-to-speech (TTS) and speech-to-text (STT), allowing users to engage naturally with the assistant. Users can interact through a friendly React-based frontend, currently deployed at:

[buddys-brain-alpha.vercel.app](https://buddys-brain-alpha.vercel.app/)

## Features

- **Semantic Vector Search**: Quickly retrieves educational resources relevant to the student's query.
- **AI-Generated Summaries**: Uses GPT-6 Luna to provide concise summaries and explanations.
- **Fallback Summaries**: Provides brief, AI-generated summaries from general model knowledge (without live web browsing) when internal resources aren't available.
- **Voice Interaction**: Supports natural voice-based interactions using TTS and STT technologies.
- **Media Uploads**: Allows users to upload different media types such as images, videos, links, and documents to assist future students.

## Tech Stack

- **Frontend**: React
- **Backend**: FastAPI, MongoDB (with vector search capabilities)
- **AI Model**: OpenAI GPT-6 Luna
- **Deployment**: Deployed via Vercel (frontend) and Railway (backend), Docker-friendly and cloud-compatible

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB with vector search indexes
- OpenAI API key

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/HuVddme/Buddys-Brain
cd Buddys-Brain/BuddysBrain-Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Enter your own database, OpenAI and Cloudinary settings in the backend `.env`.
The template lists every variable. Keep the real file private and out of Git.
Hosting environment variables take precedence over this local file.

```
OPENAI_API_KEY=your_openai_api_key
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### AI model configuration

All document, image, article, YouTube and search summaries use the shared Chat
Completions client. Defaults work without adding new variables to an existing
backend `.env`:

```dotenv
OPENAI_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
```

Keep your existing `OPENAI_API_KEY` private on the backend. Your OpenAI project
must have access to Luna and available API quota. A model change alone does not
fix missing credentials, exhausted quota or an unavailable backend.

The default preserves non-reasoning behavior and temperature 0.3. Output budgets
remain 300 tokens for article/video summaries and 500 for documents, images and
answers, now using `max_completion_tokens`. Empty, refused and truncated responses
return errors instead of being stored. For a later reasoning comparison, set
`OPENAI_REASONING_EFFORT=low` and `OPENAI_MAX_COMPLETION_TOKENS=4096`; temperature is
omitted when reasoning is enabled. The override applies to every task and includes
both reasoning and visible output tokens, so raising it can increase cost/latency.
Restart the backend after changing settings. Other model IDs require checking
that model's parameter and image-input compatibility first.

Text prompts, including questions and instructions, are limited to 400,000 UTF-8
bytes. This replaces the old 100,000-token estimate with an application size limit,
not an exact Luna token count; non-English text can reach the limit sooner.
It avoids unsupported tokenizer mappings and tokenizer downloads during requests.
Image data is subject to the existing upload size limit separately.

MongoDB vectors and the `all-MiniLM-L6-v2` embedding model are unchanged; existing
resources need no reindexing. The standalone search utility uses the same client:
run `python -m app.utils.summarization.Search.main` from the backend directory with
its `resources.json` input in that working directory.

Migration references: [Luna model](https://developers.openai.com/api/docs/models/gpt-6-luna),
[parameter compatibility](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra),
and [Chat Completions output limits](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
Mocked tests verify request compatibility and failure handling; live answer quality,
latency and cost still need measurement with your own configured services.

### Starting the Server

From `BuddysBrain-Backend`, with the virtual environment active:

```bash
uvicorn app.main:app --reload --port 8000
```

For the frontend, enter `BuddysBrain-Frontend/my-vite-app`, run `npm ci`, copy
`.env.example` to `.env`, and run `npm run dev`. Set `VITE_API_BASE_URL` to your
backend address. Rebuild the frontend when this value changes. No secret belongs
in a `VITE_*` variable.

### First round of fixes in this fork

- Cloudinary reads your backend environment variables instead of committed credentials.
- Deletion requires `Authorization: Bearer <RESOURCE_ADMIN_TOKEN>`. Generate a long
  random token locally using the command in `.env.example`. Keep it exclusively
  in trusted administrative tooling; never embed it in the frontend. Deletion
  returns 503 when unconfigured and 401 for absent or incorrect credentials.
  This protects an admin operation; individual user accounts/ownership are not implemented yet.
- Article requests allow only public HTTP/HTTPS addresses on ports 80/443, validate
  each redirect, and connect to the validated IP with TLS hostname verification.
  Downloads have connect/read timeouts, a size limit, and a bounded redirect count.
- Blocking summarization, embedding and upload calls run in a thread pool.
  OpenAI uses a 30-second timeout and at most one retry; uploads have a 30-second timeout.
- Failed summaries return errors instead of being stored as content. Unsupported
  uploads are rejected before processing. Supported documents are PDF, DOCX and TXT;
  supported images are PNG, JPEG, WEBP and GIF. Uploads are limited to 10 MB.
- Temporary files are cleaned up on both success and failure. Cloudinary uploads
  begin only after summarization and embedding succeed.
- Questions can be typed without microphone access. Voice users can stop recording,
  review the transcript and select Ask Buddy. Failed questions remain available to retry.

Changing credentials does not migrate existing media. The original Cloudinary
account owner must still rotate the credentials exposed in repository history.
Deploying this fork requires your own services; no changes here update the original site.

### Tests without accounts or API keys

From `BuddysBrain-Backend`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
python -m pytest -q
```

These tests exercise the FastAPI routes with mocked database, AI, storage and
embedding dependencies. They block network access and do not download an embedding
model. Install `requirements.txt` instead when running the actual backend.

From `BuddysBrain-Frontend/my-vite-app`:

```bash
npm ci
npm test
npm run lint
npm run build
```

Frontend tests mock the API and cover typing, duplicate submission prevention,
unavailable speech APIs, missing configuration and retryable errors. Live MongoDB
vector search, OpenAI responses and Cloudinary uploads still require your own
configured services and a separate integration check.

## API Endpoint

**POST** `/search`

**Request Example:**

```json
{
  "query": "Explain the concept of limits in calculus"
}
```

**Response Example:**

```json
{
  "summary": "A limit in calculus describes the value a function approaches as its input approaches some point. Limits form the foundational basis for defining continuity, derivatives, and integrals. They help mathematicians understand function behavior near specific points, even if the function isn't explicitly defined there. Limits are essential in evaluating instantaneous rates of change and the area under curves. Understanding limits is crucial for applications in physics, engineering, economics, and many other fields.",
  "results": [
    {
      "title": "Limits and Continuity",
      "summary": "Detailed explanation of calculus concepts like limits and continuity.",
      "media_link": "https://example.com/limits",
      "media_type": "video",
      "course": "CALC101",
      "score": 0.93
    }
  ]
}
```

## Contributing

Contributions are welcome! Please submit pull requests or open issues for improvements.

## Contributors

This project was developed during the Bison Bytes 2025 hackathon hosted at Howard University by:

- [Robel Kebede](https://github.com/RobelK1738)
- [Abdulmujeeb Lawal](https://github.com/lawal-mj)
- [Valentine Ezikeoha](https://github.com/HuVddme)
- [Kyle Nwosu](https://github.com/KyleNwosu)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
