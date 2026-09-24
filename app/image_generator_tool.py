"""
Tool for generating domain-specific infographics using gemini-3.1-flash-lite-image in the global region.
Saves the artifact in the Playground via ToolContext and uploads to public Cloud Storage.
"""
import uuid
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

BUCKET_NAME = "romanian-tax-advisor-assets-qwiklabs-gcp-01-2576b95a29b1"
PROJECT_ID = "qwiklabs-gcp-01-2576b95a29b1"

def generate_tax_infographic(
    description: str,
    tool_context: ToolContext
) -> str:
    """Generează un infografic sau o reprezentare vizuală pentru un subiect sau o obligație din Codul Fiscal.

    Args:
        description: Descrierea imaginii/infograficului dorit (ex: 'Infografic cota impozit profit 16% vs 1% microîntreprinderi', 'Calendar fiscal ANAF').

    Returns:
        URL-ul public HTTPS al imaginii generate și salvate în Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    prompt = (
        f"A professional, clean fiscal infographic illustrating: {description}. "
        f"Include Romanian tax symbols, document charts, and clear visual layout."
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt
    )

    image_bytes = None
    mime_type = "image/jpeg"

    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

    if not image_bytes:
        return "Nu s-a putut genera imaginea solicitată."

    filename = f"tax_infographic_{uuid.uuid4().hex[:8]}.jpg"

    # 1. Save artifact in Playground's Artifacts panel via tool_context
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes directly to public Cloud Storage bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return (
        f"✅ Infograficul fiscal a fost generat și salvat cu succes!\n"
        f"• Vizualizabil în panoul de Artifacte: {filename}\n"
        f"• URL Public Cloud Storage: {public_url}"
    )
