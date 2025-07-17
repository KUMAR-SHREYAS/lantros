from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Request
from typing import List
import shutil
from pathlib import Path
import json

from .file_utils import extract_text_from_pdf, extract_text_from_docx, get_text_chunks
from .embeddings import encode_chunks, EMBEDDING_MODEL
from .qdrant_utils import ensure_collection, upsert_embeddings, qdrant
from qdrant_client.http import models as rest
from retrieve.llm_utils import personalize_with_llm
from retrieve.llm_utils import list_groq_models, list_gemini_models

DATASETS_DIR = Path("datasets")
DATASETS_DIR.mkdir(exist_ok=True)

router = APIRouter()

@router.post("/upload_dataset")
async def upload_dataset(dataset_name: str = Form(...), files: List[UploadFile] = File(...)):
    dataset_path = DATASETS_DIR / dataset_name
    dataset_path.mkdir(parents=True, exist_ok=True)
    try:
        for file in files:
            file_path = dataset_path / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save files: {e}")
    return {"message": "Upload successful."}

@router.post("/train_dataset")
def train_dataset(dataset_name: str = Form(...)):
    dataset_path = DATASETS_DIR / dataset_name
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    
    # Gather all text from files
    all_chunks = []
    for file_path in dataset_path.iterdir():
        if file_path.suffix.lower() == ".pdf":
            text = extract_text_from_pdf(file_path)
        elif file_path.suffix.lower() in [".docx", ".doc"]:
            text = extract_text_from_docx(file_path)
        else:
            continue  # skip unsupported files
        chunks = get_text_chunks(text)
        all_chunks.extend(chunks)
    if not all_chunks:
        raise HTTPException(status_code=400, detail="No valid text found in dataset.")
    
    # Generate embeddings
    embeddings = encode_chunks(all_chunks)
    
    # Create Qdrant collection if not exists
    collection_name = dataset_name
    ensure_collection(collection_name, embeddings.shape[1])
    upsert_embeddings(collection_name, embeddings, all_chunks)
    return {"message": "Training and embedding storage successful."} 

@router.post("/query")
def query_dataset(dataset_name: str = Form(...), query: str = Form(...), top_k: int = 5):
    # Generate embedding for the query
    query_embedding = EMBEDDING_MODEL.encode([query])[0]
    collection_name = dataset_name
    # Search Qdrant collection
    search_result = qdrant.search(
        collection_name=collection_name,
        query_vector=query_embedding.tolist(),
        limit=top_k
    )
    # Prepare response
    results = [
        {
            "score": hit.score,
            "text": hit.payload.get("text", "")
        }
        for hit in search_result
    ]
    return {"results": results} 

@router.post("/chat_llm")
def chat_llm(
    dataset_name: str = Form(...),
    query: str = Form(...),
    llm: str = Form(...),  # 'groq', 'gemini', or 'openai'
    model: str = Form("gpt-3.5-turbo"),
    top_k: int = Form(5),
    history: str = Form(None)
):
    # Generate embedding for the query
    query_embedding = EMBEDDING_MODEL.encode([query])[0]
    collection_name = dataset_name
    # Search Qdrant collection
    search_result = qdrant.search(
        collection_name=collection_name,
        query_vector=query_embedding.tolist(),
        limit=top_k
    )
    # Concatenate retrieved texts
    retrieved_content = "\n---\n".join([hit.payload.get("text", "") for hit in search_result])
    if not retrieved_content:
        return {"result": "No relevant content found in dataset."}
    # Parse history if provided
    chat_history = []
    if history:
        try:
            chat_history = json.loads(history)
        except Exception:
            chat_history = []
    # Use LLM to personalize response with memory
    try:
        if llm == "groq":
            # Build messages: system, then up to 10 previous, then current user
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Use the following context to answer the user's question."}
            ]
            for msg in chat_history[-10:]:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": f"Context: {retrieved_content}\n\nQuestion: {query}"})
            llm_response = personalize_with_llm(llm, query, retrieved_content, model, messages=messages)
        elif llm == "gemini":
            # Prepend chat history to the prompt
            history_text = ""
            for msg in chat_history[-10:]:
                if msg["role"] == "user":
                    history_text += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    history_text += f"Assistant: {msg['content']}\n"
            prompt = f"{history_text}Context: {retrieved_content}\n\nQuestion: {query}\n\nAnswer as helpfully as possible."
            llm_response = personalize_with_llm(llm, query, retrieved_content, model, prompt_override=prompt)
        else:
            llm_response = personalize_with_llm(llm, query, retrieved_content, model)
    except Exception as e:
        return {"result": f"LLM error: {str(e)}"}
    return {"result": llm_response} 

@router.post("/summarize_content")
def summarize_content(
    content: str = Form(...),
    llm: str = Form(...),
    model: str = Form("")
):
    """
    Summarize the provided content using the selected LLM (Groq or Gemini).
    """
    try:
        if llm == "groq":
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Summarize the following content as clearly and concisely as possible."},
                {"role": "user", "content": content}
            ]
            summary = personalize_with_llm(llm, "Summarize the following content.", content, model, messages=messages)
        elif llm == "gemini":
            prompt = f"Summarize the following content as clearly and concisely as possible.\n\nContent:\n{content}"
            summary = personalize_with_llm(llm, "Summarize the following content.", content, model, prompt_override=prompt)
        else:
            return {"result": "Invalid LLM selection."}
    except Exception as e:
        return {"result": f"LLM error: {str(e)}"}
    return {"result": summary}

@router.get("/list_datasets")
def list_datasets():
    """Return all available Qdrant collection names (datasets)."""
    collections = qdrant.get_collections()
    collection_names = [col.name for col in collections.collections]
    return {"datasets": collection_names} 

@router.get("/list_groq_models")
def get_groq_models():
    return {"models": list_groq_models()}

@router.get("/list_gemini_models")
def get_gemini_models():
    return {"models": list_gemini_models()} 