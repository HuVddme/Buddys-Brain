from pathlib import Path
import tempfile

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
import cloudinary.uploader

from ..auth import require_resource_admin
from ..database import collection
from ..models import ResourceModel, ResourceOut
from ..utils.cloudary_config import cloudinary
from ..utils.embeddings import get_embedding
from ..utils.objectid import serialize_mongo_doc
from ..utils.processing import ProcessingError, run_processing
from ..utils.summarization.Document.main import summarize_document
from ..utils.summarization.Image.main import summarize_image
from ..utils.summarization.URL.main import summarize_article, summarize_video

router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def summarize_link(media_type, media_link):
    if media_type == "article":
        summary = summarize_article(media_link)
    elif media_type == "video":
        summary = summarize_video(media_link)
    else:
        raise ProcessingError("Upload documents and images through the file upload form.", 400)
    if not summary or not summary.strip():
        raise ProcessingError("No summary could be generated for this resource.")
    return summary.strip(), get_embedding(summary)


@router.post("/resources", response_model=ResourceOut)
async def create_resource(resource: ResourceModel):
    resource_dict = resource.model_dump()
    summary, embedding = await run_processing(summarize_link, resource.media_type, resource.media_link)
    resource_dict.update(summary=summary, embedding=embedding)
    result = await collection.insert_one(resource_dict)
    created = await collection.find_one({"_id": result.inserted_id})
    return ResourceOut.model_validate(serialize_mongo_doc(created))


@router.post("/resources/bulk", response_model=list[ResourceOut])
async def create_bulk_resources(resources: list[ResourceModel]):
    if not 1 <= len(resources) <= 200:
        raise HTTPException(400, "Provide between 1 and 200 resources per request.")
    resource_dicts = []
    for resource in resources:
        r_dict = resource.model_dump()
        r_dict["embedding"] = await run_processing(get_embedding, resource.summary or resource.description)
        resource_dicts.append(r_dict)
    result = await collection.insert_many(resource_dicts)
    inserted_docs = await collection.find({"_id": {"$in": result.inserted_ids}}).to_list(length=200)
    return [ResourceOut.model_validate(serialize_mongo_doc(doc)) for doc in inserted_docs]


@router.get("/resources", response_model=list[ResourceOut])
async def get_all_resources():
    resources = await collection.find().to_list(500)
    return [ResourceOut.model_validate(serialize_mongo_doc(r)) for r in resources]


@router.get("/numResources", response_model=int)
async def get_resource_count():
    return await collection.count_documents({})


def resource_object_id(resource_id):
    if not ObjectId.is_valid(resource_id):
        raise HTTPException(400, "Invalid resource ID.")
    return ObjectId(resource_id)


@router.get("/resources/{resource_id}", response_model=ResourceOut)
async def get_resource(resource_id: str):
    resource = await collection.find_one({"_id": resource_object_id(resource_id)})
    if not resource:
        raise HTTPException(404, "Resource not found")
    return ResourceOut.model_validate(serialize_mongo_doc(resource))


@router.delete("/resources/{resource_id}", dependencies=[Depends(require_resource_admin)])
async def delete_resource(resource_id: str):
    result = await collection.delete_one({"_id": resource_object_id(resource_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Resource not found")
    return {"message": "Resource deleted"}


def process_upload(contents, suffix, media_type):
    # Cleanup is guaranteed even if parsing, an API call or embedding fails.
    with tempfile.TemporaryDirectory(prefix="buddys-brain-") as directory:
        path = Path(directory) / f"resource{suffix}"
        path.write_bytes(contents)
        summarize = summarize_document if media_type == "document" else summarize_image
        summary = summarize(str(path))
        if not summary or not summary.strip():
            raise ProcessingError("The file has no readable educational content.", 422)
        embedding = get_embedding(summary)
    # Avoid creating a cloud asset when summarization has already failed.
    settings = cloudinary.config()
    if not all((settings.cloud_name, settings.api_key, settings.api_secret)):
        raise ProcessingError("File storage is not configured.", 503)
    uploaded = cloudinary.uploader.upload(
        contents, resource_type="raw" if media_type == "document" else "image", timeout=30,
    )
    return summary, embedding, uploaded["secure_url"]


@router.post("/upload", response_model=ResourceOut)
async def upload_and_create_resource(
    file: UploadFile = File(...), title: str = Form(...),
    description: str = Form(...), course: str = Form(...),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in DOCUMENT_EXTENSIONS:
        media_type = "document"
    elif suffix in IMAGE_EXTENSIONS:
        media_type = "image"
    else:
        raise HTTPException(415, "Supported files: PDF, DOCX, TXT, PNG, JPEG, WEBP and GIF.")
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if not contents:
        raise HTTPException(422, "The uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Files must be 10 MB or smaller.")
    summary, embedding, media_link = await run_processing(process_upload, contents, suffix, media_type)
    resource_doc = ResourceModel(
        title=title, description=description, media_type=media_type,
        media_link=media_link, course=course, summary=summary, embedding=embedding,
    ).model_dump()
    inserted = await collection.insert_one(resource_doc)
    created = await collection.find_one({"_id": inserted.inserted_id})
    return ResourceOut.model_validate(serialize_mongo_doc(created))
