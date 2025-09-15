import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
from gemini_client import GeminiFlashClient
from database import TiDBVectorDatabase

@dataclass
class AgentResult:
    """Standard result format for all agents"""
    success: bool
    data: Any
    execution_time_ms: int
    error_message: Optional[str] = None
    step_number: int = 0

class BaseAgent(ABC):
    """Base class for all specialized agents"""

    def __init__(self, name: str, db: TiDBVectorDatabase, gemini_client: GeminiFlashClient):
        self.name = name
        self.db = db
        self.gemini = gemini_client

    @abstractmethod
    def execute(self, input_data: Dict[str, Any], generation_id: int, step_number: int) -> AgentResult:
        """Execute the agent's main functionality"""
        pass

    def log_execution(self, generation_id: int, step_number: int, input_data: Any, result: AgentResult):
        """Log agent execution to database"""
        self.db.log_agent_execution(
            generation_id=generation_id,
            agent_name=self.name,
            step_number=step_number,
            input_data=json.dumps(input_data) if input_data else None,
            output_data=json.dumps(result.data) if result.data else None,
            execution_time_ms=result.execution_time_ms,
            status='success' if result.success else 'error',
            error_message=result.error_message
        )

class ContentIntelligenceAgent(BaseAgent):
    """Agent responsible for educational content analysis and generation"""

    def __init__(self, db: TiDBVectorDatabase, gemini_client: GeminiFlashClient):
        super().__init__("ContentIntelligenceAgent", db, gemini_client)

    def execute(self, input_data: Dict[str, Any], generation_id: int, step_number: int) -> AgentResult:
        start_time = time.time()

        try:
            topic = input_data.get('topic')
            age_group = input_data.get('age_group', 'child')
            language = input_data.get('language', 'en')

            # Step 1: Search for similar educational content in database
            similar_content = self.db.search_similar_content(topic, content_type='comic', limit=3)

            # Step 2: Get successful comic patterns
            successful_patterns = self.db.get_successful_comic_patterns(limit=5)

            # Step 3: Generate educational content using Gemini
            educational_content = self.gemini.generate_educational_content(topic, age_group, language)

            # Step 4: Extract character information
            characters = self.gemini.extract_character_info(educational_content)

            # Step 5: Parse content into structured format
            scenes = self._parse_educational_content(educational_content)

            result_data = {
                'educational_content': educational_content,
                'characters': characters,
                'scenes': scenes,
                'similar_content_found': len(similar_content),
                'successful_patterns': len(successful_patterns),
                'content_analysis': {
                    'topic': topic,
                    'age_group': age_group,
                    'language': language,
                    'scene_count': len(scenes),
                    'character_count': len(characters)
                }
            }

            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=True,
                data=result_data,
                execution_time_ms=execution_time,
                step_number=step_number
            )

            # Store educational content in database for future reference
            self.db.store_educational_content(
                topic=topic,
                content=educational_content,
                content_type='comic',
                age_group=age_group
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=False,
                data=None,
                execution_time_ms=execution_time,
                error_message=str(e),
                step_number=step_number
            )

        self.log_execution(generation_id, step_number, input_data, result)
        return result

    def _parse_educational_content(self, content: str) -> List[Dict[str, str]]:
        """Parse the educational content into structured scenes"""
        scenes = []
        lines = content.split('\n')
        current_scene = None

        for line in lines:
            line = line.strip()
            if line.startswith('SCENE'):
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {'scene_number': len(scenes) + 1, 'dialogues': []}
            elif ':' in line and current_scene is not None:
                if not line.startswith('CHARACTERS:') and not line.startswith('EDUCATIONAL_SUMMARY:'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        character = parts[0].strip()
                        dialogue = parts[1].strip()
                        current_scene['dialogues'].append({
                            'character': character,
                            'dialogue': dialogue
                        })

        if current_scene:
            scenes.append(current_scene)

        return scenes

class VisualGenerationAgent(BaseAgent):
    """Agent responsible for visual prompt generation and image coordination"""

    def __init__(self, db: TiDBVectorDatabase, gemini_client: GeminiFlashClient):
        super().__init__("VisualGenerationAgent", db, gemini_client)

    def execute(self, input_data: Dict[str, Any], generation_id: int, step_number: int) -> AgentResult:
        start_time = time.time()

        try:
            scenes = input_data.get('scenes', [])
            characters = input_data.get('characters', {})
            visual_style = input_data.get('visual_style', 'comic')
            topic = input_data.get('topic')

            visual_prompts = []

            # Generate poster prompt first
            character_names = list(characters.keys()) if characters else ['protagonist', 'supporting character']
            poster_prompt = self.gemini.generate_comic_poster_prompt(topic, visual_style, character_names)

            visual_prompts.append({
                'type': 'poster',
                'prompt': poster_prompt,
                'scene_number': 0
            })

            # Generate visual prompts for each scene
            for scene in scenes:
                scene_number = scene.get('scene_number', 0)
                dialogues = scene.get('dialogues', [])

                for dialogue_item in dialogues:
                    character = dialogue_item.get('character', 'Unknown')
                    dialogue = dialogue_item.get('dialogue', '')

                    # Search for similar character templates
                    character_templates = self.db.search_character_templates(
                        query=f"{character} {dialogue}",
                        visual_style=visual_style,
                        limit=2
                    )

                    scene_context = f"Scene {scene_number} of educational comic about {topic}"

                    visual_prompt = self.gemini.generate_visual_prompt(
                        character=character,
                        dialogue=dialogue,
                        scene_context=scene_context,
                        visual_style=visual_style
                    )

                    visual_prompts.append({
                        'type': 'scene',
                        'scene_number': scene_number,
                        'character': character,
                        'dialogue': dialogue,
                        'prompt': visual_prompt,
                        'similar_templates': len(character_templates)
                    })

            result_data = {
                'visual_prompts': visual_prompts,
                'total_prompts': len(visual_prompts),
                'poster_prompt': poster_prompt,
                'characters_processed': len(characters),
                'scenes_processed': len(scenes)
            }

            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=True,
                data=result_data,
                execution_time_ms=execution_time,
                step_number=step_number
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=False,
                data=None,
                execution_time_ms=execution_time,
                error_message=str(e),
                step_number=step_number
            )

        self.log_execution(generation_id, step_number, input_data, result)
        return result

class QualityAssuranceAgent(BaseAgent):
    """Agent responsible for content quality validation and compliance"""

    def __init__(self, db: TiDBVectorDatabase, gemini_client: GeminiFlashClient):
        super().__init__("QualityAssuranceAgent", db, gemini_client)

    def execute(self, input_data: Dict[str, Any], generation_id: int, step_number: int) -> AgentResult:
        start_time = time.time()

        try:
            educational_content = input_data.get('educational_content', '')
            topic = input_data.get('topic')
            age_group = input_data.get('age_group', 'child')
            scenes = input_data.get('scenes', [])

            # Analyze content quality
            quality_analysis = self.gemini.analyze_content_quality(educational_content, topic, age_group)

            # Check each scene for appropriateness
            scene_validations = []
            for scene in scenes:
                dialogues = scene.get('dialogues', [])
                for dialogue_item in dialogues:
                    dialogue = dialogue_item.get('dialogue', '')
                    character = dialogue_item.get('character', '')

                    # Validate individual dialogue
                    dialogue_analysis = self.gemini.analyze_content_quality(
                        f"Character {character}: {dialogue}",
                        topic,
                        age_group
                    )

                    scene_validations.append({
                        'scene_number': scene.get('scene_number'),
                        'character': character,
                        'dialogue': dialogue,
                        'analysis': dialogue_analysis
                    })

            # Parse approval status
            approval_status = self._parse_approval_status(quality_analysis)

            # Generate improvement suggestions if needed
            improvements = []
            if not approval_status:
                improvements = self._generate_improvements(educational_content, quality_analysis)

            result_data = {
                'quality_analysis': quality_analysis,
                'scene_validations': scene_validations,
                'approval_status': approval_status,
                'improvements_needed': improvements,
                'total_scenes_validated': len(scenes),
                'validation_summary': {
                    'content_approved': approval_status,
                    'scenes_checked': len(scene_validations),
                    'improvement_count': len(improvements)
                }
            }

            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=True,
                data=result_data,
                execution_time_ms=execution_time,
                step_number=step_number
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=False,
                data=None,
                execution_time_ms=execution_time,
                error_message=str(e),
                step_number=step_number
            )

        self.log_execution(generation_id, step_number, input_data, result)
        return result

    def _parse_approval_status(self, analysis: str) -> bool:
        """Parse approval status from quality analysis"""
        return "APPROVAL: YES" in analysis.upper()

    def _generate_improvements(self, content: str, analysis: str) -> List[str]:
        """Extract improvement suggestions from analysis"""
        improvements = []
        lines = analysis.split('\n')
        in_improvements_section = False

        for line in lines:
            if 'IMPROVEMENTS:' in line.upper():
                in_improvements_section = True
                continue
            elif in_improvements_section and line.strip():
                if not line.startswith('APPROVAL:'):
                    improvements.append(line.strip())
                else:
                    break

        return improvements

class EducationalPlanningAgent(BaseAgent):
    """Agent responsible for educational curriculum alignment and planning"""

    def __init__(self, db: TiDBVectorDatabase, gemini_client: GeminiFlashClient):
        super().__init__("EducationalPlanningAgent", db, gemini_client)

    def execute(self, input_data: Dict[str, Any], generation_id: int, step_number: int) -> AgentResult:
        start_time = time.time()

        try:
            topic = input_data.get('topic')
            age_group = input_data.get('age_group', 'child')
            educational_content = input_data.get('educational_content', '')

            # Search for curriculum standards and guidelines
            curriculum_content = self.db.search_similar_content(
                query=f"{topic} curriculum {age_group}",
                content_type='curriculum',
                limit=3
            )

            # Generate learning objectives
            learning_objectives = self._generate_learning_objectives(topic, age_group)

            # Align content with educational standards
            alignment_analysis = self._analyze_curriculum_alignment(educational_content, curriculum_content)

            result_data = {
                'learning_objectives': learning_objectives,
                'curriculum_alignment': alignment_analysis,
                'curriculum_references': len(curriculum_content),
                'educational_planning': {
                    'topic': topic,
                    'age_group': age_group,
                    'alignment_score': alignment_analysis.get('score', 0),
                    'objectives_count': len(learning_objectives)
                }
            }

            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=True,
                data=result_data,
                execution_time_ms=execution_time,
                step_number=step_number
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            result = AgentResult(
                success=False,
                data=None,
                execution_time_ms=execution_time,
                error_message=str(e),
                step_number=step_number
            )

        self.log_execution(generation_id, step_number, input_data, result)
        return result

    def _generate_learning_objectives(self, topic: str, age_group: str) -> List[str]:
        """Generate learning objectives for the educational content"""
        prompt = f"""
        Generate 3-5 specific learning objectives for a {age_group} audience learning about "{topic}".

        Each objective should:
        1. Be measurable and specific
        2. Use appropriate action verbs (understand, identify, explain, etc.)
        3. Be age-appropriate for {age_group}
        4. Focus on key concepts of {topic}

        Format as a simple list:
        - Objective 1
        - Objective 2
        - etc.
        """

        response = self.gemini.generate_text(prompt)
        objectives = [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
        return objectives

    def _analyze_curriculum_alignment(self, content: str, curriculum_refs: List) -> Dict:
        """Analyze how well content aligns with curriculum standards"""
        # For now, return a basic analysis
        # In a full implementation, this would do detailed curriculum matching
        return {
            'score': 8.5,  # Out of 10
            'aligned_standards': len(curriculum_refs),
            'coverage_areas': ['comprehension', 'critical thinking', 'knowledge application'],
            'gaps': []
        }

class MultiStepAgentOrchestrator:
    """Orchestrates the multi-step agentic workflow"""

    def __init__(self):
        self.db = TiDBVectorDatabase()
        self.gemini = GeminiFlashClient()

        # Initialize all agents
        self.content_agent = ContentIntelligenceAgent(self.db, self.gemini)
        self.planning_agent = EducationalPlanningAgent(self.db, self.gemini)
        self.visual_agent = VisualGenerationAgent(self.db, self.gemini)
        self.qa_agent = QualityAssuranceAgent(self.db, self.gemini)

        self.agents = [
            self.content_agent,
            self.planning_agent,
            self.visual_agent,
            self.qa_agent
        ]

    def execute_workflow(self, user_input: Dict[str, Any], update_state_callback=None) -> Dict[str, Any]:
        """Execute the complete multi-step agentic workflow"""

        # Log the generation request
        generation_id = self.db.log_comic_generation(
            user_id=user_input.get('user_id', 'anonymous'),
            topic=user_input.get('topic'),
            comic_style=user_input.get('visual_style', 'comic'),
            language=user_input.get('language', 'en')
        )

        workflow_start_time = time.time()
        workflow_results = {'generation_id': generation_id}

        try:
            if update_state_callback:
                update_state_callback("Step 1/5: Analyzing educational content...")

            # Step 1: Content Intelligence Agent
            content_result = self.content_agent.execute(user_input, generation_id, 1)
            if not content_result.success:
                raise Exception(f"Content Intelligence Agent failed: {content_result.error_message}")

            workflow_results['content_intelligence'] = content_result.data

            if update_state_callback:
                update_state_callback("Step 2/5: Planning educational objectives...")

            # Step 2: Educational Planning Agent
            planning_input = {**user_input, **content_result.data}
            planning_result = self.planning_agent.execute(planning_input, generation_id, 2)
            if not planning_result.success:
                raise Exception(f"Educational Planning Agent failed: {planning_result.error_message}")

            workflow_results['educational_planning'] = planning_result.data

            if update_state_callback:
                update_state_callback("Step 3/5: Generating visual prompts...")

            # Step 3: Visual Generation Agent
            visual_input = {**user_input, **content_result.data}
            visual_result = self.visual_agent.execute(visual_input, generation_id, 3)
            if not visual_result.success:
                raise Exception(f"Visual Generation Agent failed: {visual_result.error_message}")

            workflow_results['visual_generation'] = visual_result.data

            if update_state_callback:
                update_state_callback("Step 4/5: Quality assurance validation...")

            # Step 4: Quality Assurance Agent
            qa_input = {**user_input, **content_result.data}
            qa_result = self.qa_agent.execute(qa_input, generation_id, 4)
            if not qa_result.success:
                raise Exception(f"Quality Assurance Agent failed: {qa_result.error_message}")

            workflow_results['quality_assurance'] = qa_result.data

            # Check if content needs improvement
            if not qa_result.data.get('approval_status', False):
                if update_state_callback:
                    update_state_callback("Content needs refinement, regenerating...")

                # In a full implementation, you could loop back to improve content
                # For now, we'll proceed with a warning
                workflow_results['quality_warning'] = qa_result.data.get('improvements_needed', [])

            if update_state_callback:
                update_state_callback("Step 5/5: Finalizing comic generation...")

            # Calculate total execution time
            total_execution_time = int(time.time() - workflow_start_time)

            # Update database with completion status
            self.db.update_comic_generation_status(
                generation_id=generation_id,
                status='completed',
                generation_time=total_execution_time
            )

            workflow_results['execution_summary'] = {
                'total_time_seconds': total_execution_time,
                'steps_completed': 4,
                'agents_executed': len(self.agents),
                'status': 'completed'
            }

            return workflow_results

        except Exception as e:
            # Update database with error status
            self.db.update_comic_generation_status(
                generation_id=generation_id,
                status='failed'
            )

            workflow_results['error'] = str(e)
            workflow_results['execution_summary'] = {
                'total_time_seconds': int(time.time() - workflow_start_time),
                'status': 'failed',
                'error_message': str(e)
            }

            return workflow_results