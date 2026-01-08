from openai import OpenAI
from pathlib import Path
from core.models import ContentItem

class ScriptGenerator:
    def __init__(self, api_key: str, prompt_path: Path):
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = prompt_path.read_text()

    def generate(self, item: ContentItem) -> str:
        user_prompt = f"""
HEADLINE: {item.title}

SOURCE: {item.source_name}

ARTICLE:
{item.raw_content[:3000]}

Write a 30-60 second news script for this story.
"""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
