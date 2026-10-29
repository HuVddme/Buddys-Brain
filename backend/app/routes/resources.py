from pathlib import Path
import os

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..auth import require_resource_admin
from ..usage import limiter, reserve_request
from ..database import collection
from ..models import ResourceModel, ResourceOut
from ..services.embeddings import get_embedding
from ..utils.objectid import serialize_mongo_doc
from ..services.processing import run_processing
from ..services.ingestion import process_upload, summarize_link

router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@router.post("/resources", response_model=ResourceOut, dependencies=[Depends(reserve_request)])
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
    await limiter.reserve(cost=len(resources))
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


@router.post("/upload", response_model=ResourceOut, dependencies=[Depends(reserve_request)])
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
    max_bytes = 4_000_000 if os.getenv("VERCEL") == "1" else MAX_UPLOAD_BYTES
    contents = await file.read(max_bytes + 1)
    if not contents:
        raise HTTPException(422, "The uploaded file is empty.")
    if len(contents) > max_bytes:
        limit = "4" if os.getenv("VERCEL") == "1" else "10"
        raise HTTPException(413, f"Files must be {limit} MB or smaller on this deployment.")
    summary, embedding, media_link = await run_processing(process_upload, contents, suffix, media_type)
    resource_doc = ResourceModel(
        title=title, description=description, media_type=media_type,
        media_link=media_link, course=course, summary=summary, embedding=embedding,
    ).model_dump()
    inserted = await collection.insert_one(resource_doc)
    created = await collection.find_one({"_id": inserted.inserted_id})
    return ResourceOut.model_validate(serialize_mongo_doc(created))
