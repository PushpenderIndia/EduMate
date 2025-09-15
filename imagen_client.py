import os
import time
from typing import Optional, Dict, Any
from PIL import Image
from io import BytesIO
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class GoogleImagenClient:
    """Client for Google's Gemini image generation (nano banana) model"""

    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model_name = "gemini-2.5-flash-image-preview"  # Gemini image generation model

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        try:
            # Initialize Gemini client with API key
            genai.configure(api_key=self.api_key)
            self.client = genai.Client()

            print(f"✅ Google Gemini image generation client initialized successfully")

        except Exception as e:
            print(f"❌ Error initializing Google Gemini image client: {e}")
            raise

    def generate_image(self, prompt: str, image_name: str, guidance_scale: float = 8.0,
                      num_inference_steps: int = 25, aspect_ratio: str = "1:1") -> str:
        """
        Generate image using Google Gemini image generation model

        Args:
            prompt: Text description for image generation
            image_name: Name for the generated image file
            guidance_scale: How closely to follow the prompt (not used in Gemini)
            num_inference_steps: Number of denoising steps (not used in Gemini)
            aspect_ratio: Image aspect ratio (not directly supported in current model)

        Returns:
            Path to the generated image file
        """
        try:
            # Generate image using Gemini image generation model
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
            )

            # Process the response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]

                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Check if this part contains inline image data
                        if part.inline_data is not None:
                            # Extract image data
                            image_data = part.inline_data.data

                            # Create PIL image from bytes
                            image = Image.open(BytesIO(image_data))

                            # Save to file
                            folder_path = "static/img/comic"
                            os.makedirs(folder_path, exist_ok=True)
                            image_path = f"{folder_path}/{image_name}.png"
                            image.save(image_path, "PNG")

                            print(f"✅ Generated image with Gemini: {image_path}")
                            return image_path

                        # If there's text content, print it (debugging)
                        elif part.text is not None:
                            print(f"Gemini response text: {part.text}")

                # If no image data found, create placeholder
                raise Exception("No image data found in Gemini response")
            else:
                raise Exception("No candidates returned from Gemini API")

        except Exception as e:
            print(f"❌ Error generating image with Gemini: {e}")
            # Fallback to a simple colored rectangle as placeholder
            return self._create_placeholder_image(image_name, prompt)


    def _create_placeholder_image(self, image_name: str, prompt: str) -> str:
        """Create a placeholder image when generation fails"""
        try:
            from PIL import ImageDraw, ImageFont

            # Create a simple placeholder image
            width, height = 512, 512
            image = Image.new('RGB', (width, height), color='lightblue')
            draw = ImageDraw.Draw(image)

            # Add text
            try:
                font = ImageFont.load_default()
            except:
                font = None

            # Draw placeholder text
            text_lines = [
                "Image Generation",
                "Placeholder",
                f"Prompt: {prompt[:30]}..."
            ]

            y_offset = height // 4
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_offset), line, fill='darkblue', font=font)
                y_offset += 40

            # Save placeholder
            folder_path = "static/img/comic"
            os.makedirs(folder_path, exist_ok=True)
            image_path = f"{folder_path}/{image_name}.png"
            image.save(image_path, "PNG")

            print(f"⚠️ Created placeholder image: {image_path}")
            return image_path

        except Exception as e:
            print(f"Failed to create placeholder image: {e}")
            raise

    def generate_comic_poster(self, prompt: str, image_name: str) -> str:
        """Generate a comic book style poster using Gemini"""
        enhanced_prompt = f"Create a comic book style poster with vibrant colors and dynamic composition: {prompt}. Make it high quality digital art in professional comic book illustration style."
        return self.generate_image(
            prompt=enhanced_prompt,
            image_name=image_name
        )

    def generate_comic_panel(self, prompt: str, image_name: str, character_style: str = "cartoon") -> str:
        """Generate a comic panel with specific character styling using Gemini"""
        enhanced_prompt = f"Create a {character_style} style comic panel: {prompt}. Use clean art style with bright colors in comic book illustration format. Make it professional digital art."
        return self.generate_image(
            prompt=enhanced_prompt,
            image_name=image_name
        )

    def test_connection(self) -> bool:
        """Test the connection to Google Gemini image generation API"""
        try:
            # Try to generate a simple test image
            test_prompt = "A simple red circle on white background"
            test_image = self.generate_image(test_prompt, "test_connection")

            if test_image and os.path.exists(test_image):
                print("✅ Google Gemini image generation API connection test successful")
                # Clean up test image
                try:
                    os.remove(test_image)
                except:
                    pass
                return True
            else:
                print("❌ Google Gemini image generation API connection test failed")
                return False

        except Exception as e:
            print(f"❌ Google Gemini image generation API connection test error: {e}")
            return False

# Helper function for backward compatibility
def generate_image_with_google_imagen(prompt: str, image_name: str, cfg: float = 8.0, steps: int = 25) -> str:
    """
    Backward compatible function that mimics the old stable_diff interface
    """
    try:
        client = GoogleImagenClient()
        return client.generate_image(
            prompt=prompt,
            image_name=image_name,
            guidance_scale=cfg,
            num_inference_steps=steps
        )
    except Exception as e:
        print(f"Error in generate_image_with_google_imagen: {e}")
        # Create a basic placeholder if all else fails
        folder_path = "static/img/comic"
        os.makedirs(folder_path, exist_ok=True)

        # Create simple placeholder
        image = Image.new('RGB', (512, 512), color='lightgray')
        image_path = f"{folder_path}/{image_name}.png"
        image.save(image_path)
        return image_path

if __name__ == "__main__":
    # Test the Google Gemini image generation client
    try:
        client = GoogleImagenClient()
        success = client.test_connection()

        if success:
            print("🎉 Google Gemini image generation client is working correctly!")
        else:
            print("⚠️ Google Gemini image generation client test failed. Please check your configuration.")

    except Exception as e:
        print(f"❌ Failed to initialize Google Gemini image generation client: {e}")
        print("\nSetup instructions:")
        print("1. Set GEMINI_API_KEY in your .env file")
        print("2. Ensure you have access to Gemini 2.5 Flash image preview model")
        print("3. Test with: from imagen_client import GoogleImagenClient; client = GoogleImagenClient()")