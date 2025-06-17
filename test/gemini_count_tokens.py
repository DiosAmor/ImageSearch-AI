from google import genai
import pathlib
import os
from dotenv import load_dotenv

media = pathlib.Path(__file__).parents[0]

load_dotenv()
client = genai.Client(api_key=os.getenv("api_key"))

prompt = "Tell me about this image"
your_image_file = client.files.upload(file=media / "images/matter.png")

print(
    client.models.count_tokens(
        model="gemini-2.0-flash", contents=[prompt, your_image_file]
    )
)
# ( e.g., total_tokens: 263 )

response = client.models.generate_content(
    model="gemini-2.0-flash", contents=[prompt, your_image_file]
)
print(response.usage_metadata)
print(response.text)
# ( e.g., prompt_token_count: 264, candidates_token_count: 80, total_token_count: 345 )
