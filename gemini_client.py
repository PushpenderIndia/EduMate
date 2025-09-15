import os
import google.generativeai as genai
from typing import Dict, List, Optional
import time
from dotenv import load_dotenv

load_dotenv()

class GeminiFlashClient:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=self.api_key)

        # Configure Gemini 2.0 Flash model
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )

    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """Generate text using Gemini 2.0 Flash with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                if response.text:
                    return response.text.strip()
                else:
                    raise Exception("Empty response from Gemini")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to generate text after {max_retries} attempts: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def generate_educational_content(self, topic: str, age_group: str = "child", language: str = "en") -> Dict:
        """Generate educational content structured for comic creation"""
        prompt = f"""
        Create educational content about "{topic}" suitable for {age_group} audience in {language}.

        Requirements:
        1. Create a 6-scene comic story that teaches about the topic
        2. Include 2-3 main characters with distinct personalities
        3. Each scene should have dialogue and educational content
        4. Make it engaging and age-appropriate
        5. Include factual information naturally in the dialogue

        Format your response as:
        CHARACTERS:
        [List each character with name and brief description]

        SCENE 1:
        Character Name: [Dialogue]

        SCENE 2:
        Character Name: [Dialogue]

        [Continue for all 6 scenes]

        EDUCATIONAL_SUMMARY:
        [Key learning points covered]
        """

        return self.generate_text(prompt)

    def generate_visual_prompt(self, character: str, dialogue: str, scene_context: str, visual_style: str) -> str:
        """Generate detailed visual prompt for image generation"""
        prompt = f"""
        Create a detailed visual prompt for generating a {visual_style} style comic panel.

        Scene: {scene_context}
        Character: {character}
        Dialogue: "{dialogue}"

        Generate a 60-word maximum prompt that includes:
        - Character appearance and expression
        - Setting/background details
        - Visual style elements
        - Mood and atmosphere
        - Comic panel composition

        Make it specific enough for stable diffusion image generation.
        """

        return self.generate_text(prompt)

    def analyze_content_quality(self, content: str, topic: str, age_group: str) -> Dict:
        """Analyze content quality and educational value"""
        prompt = f"""
        Analyze this educational content for quality and appropriateness:

        Topic: {topic}
        Target Age Group: {age_group}
        Content: {content}

        Evaluate on:
        1. Educational Value (1-10)
        2. Age Appropriateness (1-10)
        3. Engagement Level (1-10)
        4. Factual Accuracy (1-10)
        5. Cultural Sensitivity (1-10)

        Provide scores and brief explanations.
        Also suggest any improvements needed.

        Format as:
        SCORES:
        Educational Value: X/10 - [explanation]
        Age Appropriateness: X/10 - [explanation]
        Engagement Level: X/10 - [explanation]
        Factual Accuracy: X/10 - [explanation]
        Cultural Sensitivity: X/10 - [explanation]

        IMPROVEMENTS:
        [List specific suggestions if any]

        APPROVAL: [YES/NO - whether content meets standards]
        """

        return self.generate_text(prompt)

    def refine_dialogue(self, original_dialogue: str, character_context: str, educational_goal: str) -> str:
        """Refine dialogue for better educational impact and character consistency"""
        prompt = f"""
        Improve this dialogue to better serve the educational goal while maintaining character consistency:

        Original Dialogue: "{original_dialogue}"
        Character Context: {character_context}
        Educational Goal: {educational_goal}

        Requirements:
        1. Keep the character's personality and speaking style
        2. Enhance educational content delivery
        3. Make it more engaging and natural
        4. Ensure age-appropriate language
        5. Maintain dialogue length (similar word count)

        Provide only the improved dialogue without explanations.
        """

        return self.generate_text(prompt)

    def generate_comic_poster_prompt(self, topic: str, visual_style: str, characters: List[str]) -> str:
        """Generate prompt for comic poster/cover"""
        prompt = f"""
        Create a compelling visual prompt for a {visual_style} style comic book cover about "{topic}".

        Characters to feature: {', '.join(characters)}

        The prompt should describe:
        - Dynamic composition suitable for a cover
        - All main characters in action or characteristic poses
        - Title placement area
        - Background that represents the topic
        - {visual_style} art style elements
        - Exciting, eye-catching design

        Maximum 60 words for stable diffusion generation.
        """

        return self.generate_text(prompt)

    def translate_content(self, content: str, target_language: str) -> str:
        """Translate content to target language while preserving meaning and style"""
        if target_language.lower() == 'en' or target_language.lower() == 'english':
            return content

        prompt = f"""
        Translate the following content to {target_language}, maintaining:
        1. Educational value and accuracy
        2. Character personality in dialogue
        3. Natural flow and readability
        4. Age-appropriate language
        5. Cultural appropriateness

        Content to translate:
        {content}

        Provide only the translated content without explanations.
        """

        return self.generate_text(prompt)

    def extract_character_info(self, content: str) -> Dict[str, str]:
        """Extract character information from generated content"""
        prompt = f"""
        Extract character information from this content:

        {content}

        For each character mentioned, provide:
        - Name
        - Brief personality description
        - Role in the story

        Format as:
        CHARACTER_1:
        Name: [name]
        Personality: [description]
        Role: [role]

        [Continue for all characters]
        """

        response = self.generate_text(prompt)

        # Parse the response into a dictionary
        characters = {}
        lines = response.split('\n')
        current_char = None

        for line in lines:
            if line.startswith('CHARACTER_'):
                current_char = {}
            elif line.startswith('Name:') and current_char is not None:
                name = line.replace('Name:', '').strip()
                current_char['name'] = name
            elif line.startswith('Personality:') and current_char is not None:
                current_char['personality'] = line.replace('Personality:', '').strip()
            elif line.startswith('Role:') and current_char is not None:
                current_char['role'] = line.replace('Role:', '').strip()
                if current_char['name']:
                    characters[current_char['name']] = current_char
                current_char = None

        return characters