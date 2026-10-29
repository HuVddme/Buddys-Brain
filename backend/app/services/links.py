import re
from urllib.parse import parse_qs, urlsplit

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from .processing import ProcessingError
from .ai import generate_summary
from ..utils.safe_fetch import fetch_article_text

TRUNCATE_LIMIT = 30000


def get_chat_summary(messages, max_tokens):
    return generate_summary(messages, max_output_tokens=max_tokens)


def summarize_article(url, max_tokens=300):
    content = fetch_article_text(url)[:TRUNCATE_LIMIT]
    if not content.strip():
        raise ProcessingError("The article is empty.", 422)
    return get_chat_summary([
        {"role": "system", "content": "Summarize the educational content of web pages for university students. Ignore formatting and unrelated content."},
        {"role": "user", "content": f"Summarize the key ideas in under 200 words:\n\n{content}"},
    ], max_tokens)


def extract_video_id(video_url):
    try:
        parts = urlsplit(video_url)
        if parts.scheme not in {"http", "https"} or parts.username or parts.password:
            raise ValueError
        if parts.hostname in {"youtu.be", "www.youtu.be"}:
            video_id = parts.path.lstrip("/")
        elif parts.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parts.path == "/watch":
                video_id = parse_qs(parts.query).get("v", [""])[0]
            elif parts.path.startswith(("/shorts/", "/embed/")):
                video_id = parts.path.split("/")[2]
            else:
                raise ValueError
        else:
            raise ValueError
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError
        return video_id
    except ValueError as exc:
        raise ProcessingError("Provide a valid YouTube video URL.", 400) from exc


class TimeoutSession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (5, 15))
        return super().request(method, url, **kwargs)


def summarize_video(video_url, max_tokens=300):
    video_id = extract_video_id(video_url)
    try:
        with TimeoutSession() as session:
            transcript = YouTubeTranscriptApi(http_client=session).fetch(video_id)
        text = " ".join(item.text for item in transcript)[:TRUNCATE_LIMIT]
    except Exception as exc:
        raise ProcessingError("The YouTube transcript is unavailable. Try another video.") from exc
    if not text.strip():
        raise ProcessingError("The video transcript is empty.", 422)
    return get_chat_summary([
        {"role": "system", "content": "Summarize the educational content of YouTube transcripts for students. Focus on concepts and explanations."},
        {"role": "user", "content": f"Summarize the key educational ideas in under 200 words:\n\n{text}"},
    ], max_tokens)
