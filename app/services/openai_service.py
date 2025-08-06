import openai
from typing import List, Dict, Any, Optional
from app.config import settings
from app.models.document import Document
from app.models.chat import Chat, Message
from app.models.workspace import AISettings
from app.models.workflow import WorkflowStep, WorkflowAnalysis
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        ai_settings: any,
        context_documents: List[Document] = None,
        workflow_context: Dict[str, Any] = None
    ) -> str:
        """Generate AI response using OpenAI"""
        try:
            # Validate inputs
            if not messages:
                return "I'm here to help! How can I assist you today?"
            
            if not ai_settings:
                ai_settings = {}
            
            # Build system prompt
            system_prompt = self._build_system_prompt(ai_settings, context_documents, workflow_context)
            
            # Prepare conversation history
            conversation = [{"role": "system", "content": system_prompt}]
            
            # Validate and clean messages
            for msg in messages:
                if msg.get("content") and msg.get("role"):
                    conversation.append({
                        "role": msg["role"],
                        "content": str(msg["content"]).strip()
                    })
            
            # Ensure we have at least one user message
            if len(conversation) <= 1:
                return "I'm here to help! How can I assist you today?"
            
            # Log conversation for debugging
            logger.info(f"Generating response for {len(conversation)} messages")
            
            # Generate response
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=conversation,
                max_tokens=ai_settings.get('max_response_tokens', 150),
                temperature=max(0.0, min(1.0, ai_settings.get('temperature', 0.7))),
                presence_penalty=0.1,  # Encourage diverse responses
                frequency_penalty=0.1   # Reduce repetition
            )
            
            generated_response = response.choices[0].message.content
            
            if not generated_response or not generated_response.strip():
                return ai_settings.get('fallback_message', "I'm sorry, I'm having trouble generating a response right now. Please try again.")
            
            # Apply post-processing based on settings
            return self._post_process_response(generated_response, ai_settings)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            fallback = ai_settings.get('fallback_message') if ai_settings else None
            return fallback or "I'm sorry, I'm having trouble generating a response right now. Please try again."
    
    async def analyze_workflow_step_completion(
        self,
        message: str,
        step_data: WorkflowStep,
        chat_history: List[Dict[str, str]],
        all_workflow_steps: List[WorkflowStep]
    ) -> WorkflowAnalysis:
        """Analyze if a message completes a workflow step"""
        try:
            # Build analysis prompt
            analysis_prompt = self._build_workflow_analysis_prompt(
                message, step_data, chat_history, all_workflow_steps
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 for better analysis
                messages=[
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": f"Analyze this message: {message}"}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            return self._parse_workflow_analysis(analysis_text, step_data, all_workflow_steps)
            
        except Exception as e:
            logger.error(f"Workflow analysis error: {e}")
            return WorkflowAnalysis(
                step_completed=False,
                confidence_score=0.0,
                extracted_info={},
                next_step=None,
                needs_clarification=True,
                suggested_response="I need some clarification. Could you please provide more details?"
            )
    
    async def generate_workflow_response(
        self,
        current_step: WorkflowStep,
        user_message: str,
        chat_history: List[Dict[str, str]],
        workflow_progress: Dict[str, Any],
        context_documents: List[Document] = None
    ) -> str:
        """Generate response based on current workflow step"""
        try:
            prompt = f"""
You are an AI assistant helping customers through a structured workflow process.

Current Step: {current_step.step_number} - {current_step.title}
Step Description: {current_step.description}
Step Type: {current_step.step_type}
Required: {current_step.is_required}

Keywords to look for: {', '.join(current_step.keywords)}
Expected response pattern: {current_step.expected_response_pattern or 'Any relevant response'}

Workflow Progress: {json.dumps(workflow_progress, indent=2)}

Context from knowledge base:
{self._format_context_documents(context_documents)}

Instructions:
1. Focus on completing the current workflow step
2. Ask clarifying questions if the user's response is unclear
3. Use the knowledge base context when relevant
4. Be conversational but stay on track with the workflow
5. If the user goes off-topic, gently guide them back to the current step

User's message: {user_message}

Generate a helpful response that moves the workflow forward:
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Workflow response generation error: {e}")
            return "I'm here to help you. Could you please tell me more about what you're looking for?"
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            if not text or len(text.strip()) < 3:
                logger.warning("Text too short for embedding generation")
                return []
                
            # Clean and prepare text
            clean_text = text.strip()
            if len(clean_text) > 8000:  # OpenAI embedding limit
                clean_text = clean_text[:8000]
                logger.info("Truncated text for embedding generation")
            
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=clean_text
            )
            
            embedding = response.data[0].embedding
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return []
    
    async def search_documents(
        self,
        query: str,
        documents: List[Document],
        limit: int = 5
    ) -> List[Document]:
        """Search documents using vector similarity"""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            if not query_embedding:
                return []
            
            # Filter documents with embeddings
            docs_with_embeddings = [doc for doc in documents if doc.embedding]
            
            if not docs_with_embeddings:
                return []
            
            # Calculate similarities
            similarities = []
            for doc in docs_with_embeddings:
                similarity = cosine_similarity(
                    [query_embedding],
                    [doc.embedding]
                )[0][0]
                similarities.append((doc, similarity))
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in similarities[:limit]]
            
        except Exception as e:
            logger.error(f"Document search error: {e}")
            return []
    
    async def generate_chat_summary(self, messages: List[Message]) -> str:
        """Generate summary of chat conversation"""
        try:
            # Prepare messages for summarization
            conversation_text = ""
            for msg in messages[-20:]:  # Last 20 messages
                role = "Customer" if msg.direction == "incoming" else "Agent"
                conversation_text += f"{role}: {msg.content}\n"
            
            # Generate summary
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize the following customer conversation in 2-3 sentences, focusing on key points and customer intent."
                    },
                    {
                        "role": "user",
                        "content": conversation_text
                    }
                ],
                max_tokens=150
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Chat summary error: {e}")
            return "Unable to generate summary."
    
    def _build_system_prompt(
        self,
        ai_settings: any,
        context_documents: List[Document] = None,
        workflow_context: Dict[str, Any] = None
    ) -> str:
        """Build system prompt with context"""
        prompt = ai_settings.get('system_prompt', 'You are a helpful assistant.')
        
        # Add business context
        if ai_settings.get('business_name'):
            prompt += f"\n\nYou work for {ai_settings['business_name']}"
            if ai_settings.get('business_type'):
                prompt += f", a {ai_settings['business_type']} business"
            prompt += "."
        
        if ai_settings.get('business_description'):
            prompt += f"\n\nBusiness description: {ai_settings['business_description']}"
        
        # Add tone instructions
        tone = ai_settings.get('tone', 'polite')
        if tone == "professional":
            prompt += "\n\nMaintain a professional and business-like tone."
        elif tone == "friendly":
            prompt += "\n\nUse a warm, friendly, and approachable tone."
        elif tone == "casual":
            prompt += "\n\nUse a casual and conversational tone."
        elif tone == "polite":
            prompt += "\n\nBe polite, respectful, and courteous in all interactions."
        
        # Add length instructions
        response_length = ai_settings.get('response_length', 'short')
        if response_length == "short":
            prompt += "\n\nKeep responses concise and to the point."
        elif response_length == "medium":
            prompt += "\n\nProvide detailed but not lengthy responses."
        elif response_length == "long":
            prompt += "\n\nProvide comprehensive and detailed responses."
        
        # Add language instructions
        language = ai_settings.get('language', 'english')
        if language != 'english':
            prompt += f"\n\nRespond in {language.title()}."
        
        # Add style preferences
        if ai_settings.get('include_emojis'):
            prompt += "\n\nInclude relevant emojis in your responses to make them more engaging."
        
        if ai_settings.get('formal_style'):
            prompt += "\n\nUse formal language and avoid casual expressions."
        
        if ai_settings.get('friendly_approach'):
            prompt += "\n\nBe warm and friendly in your interactions."
        
        if ai_settings.get('detailed_responses'):
            prompt += "\n\nProvide detailed explanations and comprehensive information."
        
        # Add custom instructions
        if ai_settings.get('custom_instructions'):
            prompt += f"\n\nAdditional instructions: {ai_settings['custom_instructions']}"
        
        # Add workflow context
        if workflow_context:
            prompt += f"\n\nWorkflow Context: {json.dumps(workflow_context, indent=2)}"
            prompt += "\n\nFollow the workflow steps and guide the conversation accordingly."
        
        # Add context from documents
        if context_documents:
            prompt += "\n\nContext from knowledge base:"
            for doc in context_documents:
                prompt += f"\n- {doc.title}: {doc.content[:500]}..."
        
        return prompt
    
    def _post_process_response(self, response: str, ai_settings: any) -> str:
        """Post-process the AI response based on settings"""
        processed_response = response
        
        # Add greeting if it's the first message
        if ai_settings.get('greeting_message') and len(response.strip()) > 0:
            # This would need additional context to determine if it's the first message
            pass
        
        # Add reply suggestions if enabled
        if ai_settings.get('reply_suggestions'):
            # Add suggested replies (this would need more sophisticated logic)
            pass
        
        return processed_response
    
    def _build_workflow_analysis_prompt(
        self,
        message: str,
        step_data: WorkflowStep,
        chat_history: List[Dict[str, str]],
        all_workflow_steps: List[WorkflowStep]
    ) -> str:
        """Build prompt for workflow step analysis"""
        return f"""
You are an expert workflow analyzer. Analyze if a customer message completes a specific workflow step.

Current Workflow Step:
- Step {step_data.step_number}: {step_data.title}
- Description: {step_data.description}
- Type: {step_data.step_type}
- Required: {step_data.is_required}
- Keywords: {', '.join(step_data.keywords)}
- Expected Pattern: {step_data.expected_response_pattern or 'Any relevant response'}

All Workflow Steps:
{chr(10).join([f"Step {s.step_number}: {s.title} ({'Required' if s.is_required else 'Optional'})" for s in all_workflow_steps])}

Recent Chat History:
{chr(10).join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chat_history[-5:]])}

Analyze the message and respond with a JSON object containing:
{{
    "step_completed": boolean,
    "confidence_score": float (0.0 to 1.0),
    "extracted_info": object with key-value pairs of extracted information,
    "next_step": integer or null,
    "needs_clarification": boolean,
    "suggested_response": string or null
}}

Consider:
1. Does the message address the current step's requirements?
2. How confident are you in the completion (0.0 = not at all, 1.0 = completely sure)?
3. What specific information was extracted?
4. What should be the next step number?
5. Does the response need clarification?
6. What response should the AI give?
"""
    
    def _parse_workflow_analysis(
        self,
        analysis_text: str,
        step_data: WorkflowStep,
        all_workflow_steps: List[WorkflowStep]
    ) -> WorkflowAnalysis:
        """Parse workflow analysis response"""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
            else:
                # Fallback parsing
                analysis_data = {
                    "step_completed": "completed" in analysis_text.lower(),
                    "confidence_score": 0.5,
                    "extracted_info": {},
                    "next_step": step_data.step_number + 1 if step_data.step_number < len(all_workflow_steps) else None,
                    "needs_clarification": "clarification" in analysis_text.lower(),
                    "suggested_response": None
                }
            
            return WorkflowAnalysis(
                step_completed=analysis_data.get("step_completed", False),
                confidence_score=max(0.0, min(1.0, analysis_data.get("confidence_score", 0.0))),
                extracted_info=analysis_data.get("extracted_info", {}),
                next_step=analysis_data.get("next_step"),
                needs_clarification=analysis_data.get("needs_clarification", False),
                suggested_response=analysis_data.get("suggested_response")
            )
            
        except Exception as e:
            logger.error(f"Failed to parse workflow analysis: {e}")
            return WorkflowAnalysis(
                step_completed=False,
                confidence_score=0.0,
                extracted_info={},
                next_step=None,
                needs_clarification=True,
                suggested_response="I need some clarification. Could you please provide more details?"
            )
    
    def _format_context_documents(self, documents: List[Document]) -> str:
        """Format context documents for prompt"""
        if not documents:
            return "No relevant documents found."
        
        context = ""
        for doc in documents:
            # Handle Excel documents differently to preserve structure
            if doc.document_type in ["xlsx", "xls"]:
                # For Excel, show more structured preview
                preview = doc.content[:500]
                if "WORKSHEET" in preview:
                    context += f"\n- {doc.title} (Excel): {preview}..."
                else:
                    context += f"\n- {doc.title} (Excel): {doc.content[:300]}..."
            else:
                context += f"\n- {doc.title}: {doc.content[:300]}..."
        return context
    
    def _get_max_tokens(self, response_length: str) -> int:
        """Get max tokens based on response length"""
        if response_length == "short":
            return 100
        elif response_length == "medium":
            return 300
        elif response_length == "long":
            return 500
        return 200

openai_service = OpenAIService()