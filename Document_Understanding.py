#OCR and Document Understanding

from mistralai import Mistral

# Retrieve the API key from environment variables
api_key = "uPfVIl67PTwvqiEFLFFfDjjbXQsCqjLB"

# Specify model
model = "mistral-small-latest"

# Initialize the Mistral client
client = Mistral(api_key=api_key)

# If local document, upload and retrieve the signed url

uploaded_pdf = client.files.upload(
    file={
        "file_name": "United Healthcare.pdf",
        "content": open("United Healthcare.pdf", "rb"),
    },
    purpose="ocr"
)

signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

# Define the messages for the chat
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Provide me full details of Outpatient Diagnostic and Therapeutic Services in Tabular format"
            },
            {
                "type": "document_url",
                "document_url": signed_url.url
            }
        ]
    }
]

# Get the chat response
chat_response = client.chat.complete(
    model=model,
    messages=messages
)

# Print the content of the response
print(chat_response.choices[0].message.content)
