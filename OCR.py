import os
import base64
from io import BytesIO
from pathlib import Path
import zipfile
import streamlit as st
from mistralai import Mistral
from PIL import Image
from dotenv import load_dotenv  # Import dotenv
import json

# Load environment variables from .env
load_dotenv()

# Retrieve your API key from the environment.
api_key = os.environ.get("MISTRAL")
if not api_key:
    st.error("Please set your MISTRAL API Key in your .env file under the key 'MISTRAL'.")
    st.stop()

# Create the Mistral client using the API key.
client = Mistral(api_key=api_key)

# Allowed file extensions.
VALID_DOCUMENT_EXTENSIONS = {".pdf"}
VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def upload_pdf(content, filename):
    uploaded_file = client.files.upload(
        file={"file_name": filename, "content": content},
        purpose="ocr",
    )
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id)
    return signed_url.url


def process_ocr(document_source):
    return client.ocr.process(
        model="mistral-ocr-latest",
        document=document_source,
        include_image_base64=True,
    )


def do_ocr(file):
    file_extension = Path(file.name).suffix.lower()

    if file_extension in VALID_DOCUMENT_EXTENSIONS:
        content = file.read()
        signed_url = upload_pdf(content, Path(file.name).name)
        document_source = {"type": "document_url", "document_url": signed_url}
    elif file_extension in VALID_IMAGE_EXTENSIONS:
        file.seek(0)
        image = Image.open(file)
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        document_source = {"type": "image_url", "image_url": f"data:image/png;base64,{img_str}"}
    else:
        st.error("Error: Unsupported file type. Supported types are: PDF, JPG, JPEG, PNG.")
        return None, None, None

    ocr_response = process_ocr(document_source)
    print("PRINTING OCR RESPONSE :: ",ocr_response)
    markdown_text = "\n\n".join(page.markdown for page in ocr_response.pages)
    extracted_text = markdown_text
    rendered_markdown = markdown_text
    images = []

    for page in ocr_response.pages:
        for img in page.images:
            if img.image_base64:
                base64_str = img.image_base64.split(",")[-1]
                img_bytes = base64.b64decode(base64_str)
                img_pil = Image.open(BytesIO(img_bytes))
                images.append(img_pil)

                img_buffer = BytesIO()
                img_pil.save(img_buffer, format="PNG")
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                data_url = f"data:image/png;base64,{img_base64}"
                rendered_markdown = rendered_markdown.replace(
                    f"![{img.id}]({img.id})", f"![{img.id}]({data_url})"
                )
            else:
                rendered_markdown += f"\n\n[Image Warning: No base64 data for {img.id}]"

    return extracted_text.strip(), rendered_markdown.strip(), images, ocr_response


def create_zip(extracted_text, rendered_markdown, images):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        # Add plain text
        zip_file.writestr("extracted_text.txt", extracted_text)

        # Add markdown
        zip_file.writestr("rendered_markdown.md", rendered_markdown)

        # Add images
        for idx, img in enumerate(images):
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG")
            zip_file.writestr(f"image_{idx+1}.png", img_buffer.getvalue())

    zip_buffer.seek(0)
    return zip_buffer



# Streamlit UI layout
# st.title("Mistral OCR Demo")
st.title("Digitization of Documents 🗃️")
st.markdown("Upload a PDF or an image file to extract text and images using Vision OCR.")

uploaded_file = st.file_uploader("Choose a PDF or Image file", type=["pdf", "jpg", "jpeg", "png"])

if uploaded_file:
    if st.button("Extract OCR"):
        with st.spinner("Processing OCR, please wait..."):
            extracted_text, rendered_markdown, images, ocr_json = do_ocr(uploaded_file)

        if extracted_text:
            st.header("Extracted Plain Text")
            st.text_area("", extracted_text, height=300)

            st.header("Rendered Markdown")
            st.markdown(rendered_markdown)

            zip_data = create_zip(extracted_text, rendered_markdown, images)
            st.download_button(
                label="📦 Download All (ZIP)",
                data=zip_data,
                file_name="ocr_output.zip",
                mime="application/zip"
            )

            with st.expander("Show Raw OCR JSON"):
                st.json(ocr_json.model_dump())

            # Download JSON
            json_data = json.dumps(ocr_json.model_dump(), indent=2).encode('utf-8')
            st.download_button("📥 Download OCR JSON", data=json_data, file_name="ocr_response.json",
                               mime="application/json")

            # if images:
            #     st.header("OCR Extracted Images")
            #     for img in images:
            #         st.image(img, use_column_width=True)
