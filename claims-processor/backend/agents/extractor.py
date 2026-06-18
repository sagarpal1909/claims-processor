"""
Extraction Agent

Extracts structured information from uploaded documents.
- In test mode (content already provided): passes through directly.
- In real mode (ANTHROPIC_API_KEY set): calls Claude vision API.
- Fallback (no API key): calls Ollama llava locally (free, requires `ollama serve`).
"""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
from typing import Any, Optional

import anthropic
import ollama as ollama_client

from models.claim import ClaimInput, DocumentInput
from models.decision import TraceStep

OLLAMA_MODEL = "llava"

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _has_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


EXTRACTION_PROMPT = """You are a medical document extraction specialist for Indian health insurance claims.
Extract all relevant information from this document and return it as a JSON object.

Extract as many of the following fields as are present:
- document_type: one of PRESCRIPTION, HOSPITAL_BILL, PHARMACY_BILL, LAB_REPORT, DIAGNOSTIC_REPORT, DISCHARGE_SUMMARY, DENTAL_REPORT
- patient_name
- doctor_name
- doctor_registration
- hospital_name
- date (YYYY-MM-DD if possible)
- diagnosis
- treatment
- medicines (list)
- tests_ordered (list)
- test_name (for lab reports)
- line_items: list of {description, amount}
- total_amount
- any other relevant medical or financial information

Handle handwritten text, rubber stamps, phone photos, and inconsistent formats.
If a field is not present or unclear, omit it.
Return ONLY valid JSON, no explanation."""


class ExtractionAgent:
    """
    Input : ClaimInput
    Output: dict mapping file_id -> extracted content dict, plus trace steps
    """

    def run(self, claim: ClaimInput) -> tuple[dict[str, dict[str, Any]], list[TraceStep]]:
        trace: list[TraceStep] = []
        extracted: dict[str, dict[str, Any]] = {}

        trace.append(TraceStep(
            agent="ExtractionAgent",
            step="start",
            status="INFO",
            detail=f"Extracting data from {len(claim.documents)} document(s)",
        ))

        for doc in claim.documents:
            result, steps = self._extract_document(doc)
            trace.extend(steps)
            extracted[doc.file_id] = result

        trace.append(TraceStep(
            agent="ExtractionAgent",
            step="complete",
            status="PASS",
            detail=f"Extraction complete for {len(extracted)} document(s)",
        ))
        return extracted, trace

    def _extract_document(
        self, doc: DocumentInput
    ) -> tuple[dict[str, Any], list[TraceStep]]:
        trace: list[TraceStep] = []

        # Test mode: content already provided — pass through
        if doc.content is not None:
            content = dict(doc.content)
            if doc.actual_type:
                content.setdefault("document_type", doc.actual_type.value)
            trace.append(TraceStep(
                agent="ExtractionAgent",
                step=f"extract_{doc.file_id}",
                status="PASS",
                detail=f"Used pre-provided content for {doc.file_id} ({doc.actual_type})",
                data=content,
            ))
            return content, trace

        # Real mode: Claude if key available, Ollama llava otherwise
        use_claude = _has_anthropic_key()
        try:
            if use_claude:
                content = self._call_claude_vision(doc)
                engine = "Claude"
            else:
                content = self._call_ollama_vision(doc)
                engine = f"Ollama {OLLAMA_MODEL}"

            if doc.actual_type:
                content.setdefault("document_type", doc.actual_type.value)
            trace.append(TraceStep(
                agent="ExtractionAgent",
                step=f"extract_{doc.file_id}",
                status="PASS",
                detail=f"{engine} extracted content from {doc.file_name or doc.file_id}",
                data=content,
            ))
            return content, trace
        except Exception as e:
            trace.append(TraceStep(
                agent="ExtractionAgent",
                step=f"extract_{doc.file_id}",
                status="ERROR",
                detail=f"Extraction failed for {doc.file_name or doc.file_id}: {e}",
            ))
            fallback: dict[str, Any] = {"extraction_failed": True, "error": str(e)}
            if doc.actual_type:
                fallback["document_type"] = doc.actual_type.value
            return fallback, trace

    def _call_claude_vision(self, doc: DocumentInput) -> dict[str, Any]:
        """Call Claude with the document image to extract structured content."""
        client = _get_client()

        # Prefer inline base64 data sent from the frontend
        if doc.file_data and doc.file_media_type:
            image_data = doc.file_data
            media_type = doc.file_media_type
        else:
            # Fall back to reading from disk
            file_path = Path(doc.file_name) if doc.file_name else None
            if file_path and file_path.exists():
                image_data = base64.standard_b64encode(file_path.read_bytes()).decode("utf-8")
                suffix = file_path.suffix.lower()
                media_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf"}
                media_type = media_type_map.get(suffix, "image/jpeg")
            else:
                image_data = None
                media_type = None

        if image_data and media_type:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }],
            )
        else:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": (
                        f"A medical document named '{doc.file_name}' of type '{doc.actual_type}' "
                        "was uploaded but the image is not available. "
                        "Return a JSON object with document_type set appropriately and extraction_failed: true."
                    ),
                }],
            )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    def _call_ollama_vision(self, doc: DocumentInput) -> dict[str, Any]:
        """Call Ollama llava locally for vision extraction (free, no API key needed)."""
        images: list[str] = []

        if doc.file_data:
            images = [doc.file_data]
        else:
            file_path = Path(doc.file_name) if doc.file_name else None
            if file_path and file_path.exists():
                images = [base64.standard_b64encode(file_path.read_bytes()).decode("utf-8")]

        prompt = EXTRACTION_PROMPT

        if images:
            response = ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": images,
                }],
            )
        else:
            # No image available — text-only extraction based on doc type
            response = ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        f"A medical document of type '{doc.actual_type}' named '{doc.file_name}' "
                        "was uploaded but the image is unavailable. "
                        "Return a JSON object with document_type set appropriately and extraction_failed: true."
                    ),
                }],
            )

        raw = response["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
