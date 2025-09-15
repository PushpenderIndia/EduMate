import os
import io
import time
import base64
from PIL import Image, ImageDraw, ImageFont
import cv2
import random
import string
import concurrent.futures
from PIL import Image
from easygoogletranslate import EasyGoogleTranslate
import requests, json
from dotenv import load_dotenv
from agents import MultiStepAgentOrchestrator
from database import TiDBVectorDatabase
from gemini_client import GeminiFlashClient
from imagen_client import GoogleImagenClient

# Load environment variables
load_dotenv()

class GenerateComicAgentic:
    def __init__(self, update_state=None, lang_code="en"):
        self.update_state = update_state
        self.lang_code = lang_code
        self.generated_images_paths = {}

        # Initialize the multi-step agentic system
        self.orchestrator = MultiStepAgentOrchestrator()
        self.db = TiDBVectorDatabase()
        self.gemini = GeminiFlashClient()

        # Initialize Google Imagen client for image generation
        try:
            self.imagen_client = GoogleImagenClient()
            self.printer("✅ Google Imagen client initialized successfully")
        except Exception as e:
            self.printer(f"⚠️ Google Imagen client initialization failed: {e}")
            self.imagen_client = None

        # Initialize translator for legacy support
        self.translator = EasyGoogleTranslate(
            source_language="en",
            target_language=self.lang_code,
            timeout=10
        )

    def printer(self, text):
        """Print status updates"""
        if self.update_state != None:
            self.update_state(state='PROGRESS', meta={'progress': text})
            print(text)
        else:
            print(text)

    def lang_translate(self, text):
        """Translate text to target language"""
        if self.lang_code == "en":
            return text
        else:
            return self.translator.translate(text)

    def generate_image_with_google_imagen(self, image_prompt, image_name, cfg, step):
        """Generate image using Google Imagen (nano banana) model"""
        try:
            if self.imagen_client:
                # Use Google Imagen for image generation
                image_path = self.imagen_client.generate_image(
                    prompt=image_prompt,
                    image_name=image_name,
                    guidance_scale=float(cfg),
                    num_inference_steps=int(step)
                )
                return image_path
            else:
                # Fallback to placeholder if Imagen client is not available
                self.printer("⚠️ Google Imagen not available, creating placeholder image...")
                return self._create_fallback_image(image_name, image_prompt)

        except Exception as e:
            error_message = f"Google Imagen generation failed: {str(e)}"
            self.printer(error_message)
            # Create fallback image
            return self._create_fallback_image(image_name, image_prompt)

    def _create_fallback_image(self, image_name, prompt):
        """Create a fallback image when Google Imagen is unavailable"""
        try:
            folder_path = "static/img/comic"
            os.makedirs(folder_path, exist_ok=True)

            # Create a simple colored image with text
            image = Image.new('RGB', (512, 512), color='lightblue')
            draw = ImageDraw.Draw(image)

            # Add prompt text
            try:
                font = ImageFont.load_default()
            except:
                font = None

            # Wrap text
            words = prompt.split()
            lines = []
            current_line = []
            max_width = 45  # Characters per line

            for word in words:
                if len(' '.join(current_line + [word])) <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(' '.join(current_line))

            # Draw text lines
            y_offset = 100
            for line in lines[:8]:  # Limit to 8 lines
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (512 - text_width) // 2
                draw.text((x, y_offset), line, fill='darkblue', font=font)
                y_offset += 30

            image_path = f"{folder_path}/{image_name}.png"
            image.save(image_path)
            return image_path

        except Exception as e:
            raise Exception(f"Failed to create fallback image: {e}")

    # Legacy method name for backward compatibility
    def stable_diff(self, image_prompt, image_name, cfg, step):
        """Legacy method name - redirects to Google Imagen"""
        return self.generate_image_with_google_imagen(image_prompt, image_name, cfg, step)

    def convert_images_to_pdf(self, images, output_path):
        """Convert list of images to PDF"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            images = [
                Image.open(f)
                for f in images
            ]

            images[0].save(
                output_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:]
            )
        except Exception as e:
            raise Exception(f"Error occurred during image to PDF conversion: {e}")

    def add_line_breaks(self, text):
        """Add line breaks to text for better display"""
        try:
            # Split the text into a list of words
            words = text.split()
            new_text = ''
            for i, word in enumerate(words):
                new_text += word
                if (i+1) % 7 == 0:
                    new_text += '\n'
                else:
                    new_text += ' '

            return new_text
        except AttributeError as e:
            raise Exception(f"Error occurred during line break addition: {e}")

    def add_text_to_image(self, image_path, text_from_prompt, image_name):
        """Add text overlay to image"""
        try:
            image = Image.open(image_path)
            right_pad = 0
            left_pad = 0
            top_pad = 50
            bottom_pad = 0
            width, height = image.size

            new_width = width + right_pad + left_pad
            new_height = height + top_pad + bottom_pad

            result = Image.new(image.mode, (new_width, new_height), (255, 255, 255))
            result.paste(image, (left_pad, top_pad))

            # Check if font file exists, fallback to default if not
            font_path = "static/font/animeace2_reg.ttf"
            if os.path.exists(font_path):
                font_type = ImageFont.truetype(font_path, 12)
            else:
                font_type = ImageFont.load_default()

            draw = ImageDraw.Draw(result)
            draw.text((10, 0), text_from_prompt, fill='black', font=font_type)
            result.save(f"static/img/comic/{image_name}.png")

            border_img = cv2.imread(f"static/img/comic/{image_name}.png")

            borderoutput = cv2.copyMakeBorder(
                border_img, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=[0, 0, 0])

            cv2.imwrite(f"static/img/comic/{image_name}.png", borderoutput)
        except Exception as e:
            raise Exception(f"Error occurred during text addition: {e}")

    def generate_random_alpha_string(self, length):
        """Generate random alphanumeric string"""
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(length))
        return random_string

    def process_comic_page(self, scene_data, visual_prompt, customisation, cfg, step):
        """Process individual comic page with new agentic system and Google Imagen"""
        try:
            image_name = self.generate_random_alpha_string(10)

            # Use Google Imagen's comic panel method for better comic-style results
            if self.imagen_client:
                try:
                    image_path = self.imagen_client.generate_comic_panel(
                        prompt=visual_prompt,
                        image_name=image_name,
                        character_style=customisation
                    )
                    self.printer(f"✅ Generated comic panel with Google Imagen: {image_name}")
                except Exception as e:
                    self.printer(f"⚠️ Google Imagen panel generation failed, using fallback: {e}")
                    image_path = self.stable_diff(visual_prompt, image_name, cfg, step)
            else:
                # Use fallback method
                image_path = self.stable_diff(visual_prompt, image_name, cfg, step)

            print(f"Generated image: {image_path}")

            scene_number = scene_data.get('scene_number', 0)
            self.generated_images_paths[scene_number] = image_path

            # Get dialogue for text overlay
            dialogues = scene_data.get('dialogues', [])
            if dialogues:
                # Combine all dialogues for this scene
                combined_text = " ".join([
                    f"{d.get('character', '')}: {d.get('dialogue', '')}"
                    for d in dialogues
                ])
                text = self.add_line_breaks(combined_text)
                self.add_text_to_image(f"static/img/comic/{image_name}.png", text, image_name)

            return image_path

        except Exception as e:
            print("Error [process_comic_page()]: ", e)
            return None

    def start(self, user_input, customisation, cfg, step, output_path):
        """Start the agentic comic generation process"""
        try:
            workflow_start_time = time.time()

            # Prepare input for the agentic system
            agentic_input = {
                'topic': user_input,
                'visual_style': customisation,
                'age_group': 'child',  # Can be made configurable
                'language': self.lang_code,
                'user_id': 'system'  # Can be made dynamic
            }

            self.printer("🤖 Starting Multi-Agent Comic Generation System...")

            # Execute the multi-step agentic workflow
            workflow_results = self.orchestrator.execute_workflow(
                agentic_input,
                update_state_callback=self.printer
            )

            if 'error' in workflow_results:
                raise Exception(f"Agentic workflow failed: {workflow_results['error']}")

            self.printer("✅ Multi-Agent Analysis Complete!")

            # Extract results from the agentic system
            content_results = workflow_results.get('content_intelligence', {})
            visual_results = workflow_results.get('visual_generation', {})
            qa_results = workflow_results.get('quality_assurance', {})

            scenes = content_results.get('scenes', [])
            visual_prompts = visual_results.get('visual_prompts', [])

            # Check quality assurance
            if not qa_results.get('approval_status', True):
                self.printer("⚠️ Quality assurance detected issues, but proceeding with generation...")
                improvements = qa_results.get('improvements_needed', [])
                for improvement in improvements:
                    print(f"Suggested improvement: {improvement}")

            self.printer(f"📊 Generated {len(scenes)} scenes with {len(visual_prompts)} visual prompts")

            # Generate poster image first
            poster_prompts = [vp for vp in visual_prompts if vp.get('type') == 'poster']
            if poster_prompts:
                self.printer("🎨 Generating Comic Poster with Google Imagen...")
                poster_prompt = poster_prompts[0]['prompt']
                image_name = self.generate_random_alpha_string(10)

                # Use Google Imagen's comic poster method for better results
                if self.imagen_client:
                    try:
                        poster_path = self.imagen_client.generate_comic_poster(poster_prompt, image_name)
                    except Exception as e:
                        self.printer(f"⚠️ Poster generation with Imagen failed, using fallback: {e}")
                        poster_path = self.stable_diff(poster_prompt, image_name, cfg, step)
                else:
                    poster_path = self.stable_diff(poster_prompt, image_name, cfg, step)

                self.generated_images_paths[0] = poster_path
                self.printer("✅ Poster Generated Successfully")

            # Generate scene images
            self.printer("🎬 Generating Comic Scenes...")
            scene_prompts = [vp for vp in visual_prompts if vp.get('type') == 'scene']

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []

                # Group prompts by scene
                scene_prompt_map = {}
                for prompt_data in scene_prompts:
                    scene_num = prompt_data.get('scene_number', 0)
                    if scene_num not in scene_prompt_map:
                        scene_prompt_map[scene_num] = []
                    scene_prompt_map[scene_num].append(prompt_data)

                # Process each scene
                for scene_num, scene_prompts_list in scene_prompt_map.items():
                    if scene_prompts_list:
                        # Use the first prompt for the scene (or combine multiple if needed)
                        main_prompt = scene_prompts_list[0]['prompt']
                        scene_data = next((s for s in scenes if s.get('scene_number') == scene_num), {})

                        future = executor.submit(
                            self.process_comic_page,
                            scene_data,
                            main_prompt,
                            customisation,
                            cfg,
                            step
                        )
                        futures.append(future)

                # Wait for all scenes to complete
                concurrent.futures.wait(futures)

            self.printer("✅ Comic Scenes Generated Successfully")

            # Convert to PDF
            self.printer("📚 Generating PDF Comic...")
            generated_images_paths_new = dict(sorted(self.generated_images_paths.items()))
            generated_images_paths = list(generated_images_paths_new.values())

            # Filter out None values
            generated_images_paths = [path for path in generated_images_paths if path is not None]

            if generated_images_paths:
                self.convert_images_to_pdf(generated_images_paths, output_path)
                self.printer("✅ Comic Generated Successfully!")

                # Update database with final status
                generation_id = workflow_results.get('generation_id')
                if generation_id:
                    total_time = int(time.time() - workflow_start_time)
                    self.db.update_comic_generation_status(
                        generation_id=generation_id,
                        status='completed',
                        output_path=output_path,
                        generation_time=total_time
                    )

                return generated_images_paths
            else:
                raise Exception("No images were generated successfully")

        except Exception as e:
            self.printer(f"❌ Error: {e}")
            return f"Error: {e}"

    # Legacy compatibility methods
    def convert_text_to_conversation(self, text):
        """Legacy method for backward compatibility"""
        try:
            # Use Gemini for text generation
            response = self.gemini.generate_educational_content(text, 'child', self.lang_code)
            speech, person = self.generate_map_from_text(response)

            self.printer(f"[+] Translating dialogues into {self.lang_code} ...")
            final_speech = {}
            for key, value in speech.items():
                final_speech[key] = self.lang_translate(value)

            return (final_speech, person)
        except Exception as e:
            print("Error: ", e)

    def generate_map_from_text(self, text):
        """Legacy method for parsing dialogue"""
        try:
            d = {}
            who_spoke = {}
            dialogue = []
            speak = []

            l = text.split("\n")

            for word in l:
                i = 0
                if 'Scene' not in word and 'Act' not in word:
                    if ':' in word:
                        dialogue.append((word.split(':')[1]))
                        speak.append((word.split(':')[0]))

                for i in range(len(dialogue)):
                    d[i] = dialogue[i]
                    who_spoke[i] = speak[i]

            return (d, who_spoke)
        except Exception as e:
            raise Exception(f"Error occurred during map generation: {e}")

if __name__ == "__main__":
    test = GenerateComicAgentic(lang_code="en")

    user_input = "Solar System and Planets"
    customisation = "superhero"  # Enter your favourite comic style
    cfg = 8   # 0-10
    step = 25 # 0-100
    output_path = f"static/pdfs/{user_input[:30].lower().replace(' ', '_').replace('-', '_')}.pdf"

    result = test.start(user_input, customisation, cfg, step, output_path)
    print(f"Comic generation result: {result}")