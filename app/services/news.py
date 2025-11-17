"""
News Service - Fetches and summarizes news using ChatGPT
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class NewsService:
    """
    Handles news queries using ChatGPT
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def get_news(
        self,
        user_id: str,
        category: str = "general",
        count: int = 5
    ) -> Dict[str, Any]:
        """
        Get news summary using ChatGPT
        
        Args:
            user_id: User identifier
            category: News category (general, tech, sports, business, etc.)
            count: Number of news items
            
        Returns:
            Dict with status and news data
        """
        try:
            logger.info(f"📰 Fetching {category} news for user {user_id}")
            
            # Get current date for context
            today = datetime.now().strftime("%B %d, %Y")
            
            # Create prompt for ChatGPT
            prompt = self._create_news_prompt(category, count, today)
            
            # Call ChatGPT
            response = await self.client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful news assistant. Provide concise, factual news summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            news_summary = response.choices[0].message.content
            
            return {
                "status": "success",
                "category": category,
                "date": today,
                "summary": news_summary,
                "message": news_summary
            }
            
        except Exception as e:
            logger.error(f"❌ News fetch error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "I'm having trouble fetching the news right now. Please try again later."
            }
    
    def _create_news_prompt(self, category: str, count: int, today: str) -> str:
        """Create prompt for ChatGPT to generate news"""
        
        if category == "general" or category == "today":
            prompt = f"""Today is {today}. Please provide a brief summary of the top {count} news headlines for today. 
Include a mix of important global news, technology, and interesting stories. 
Format: Start with a brief overview, then list key headlines.
Keep it conversational and concise (under 300 words)."""
        
        elif category == "tech" or category == "technology":
            prompt = f"""Today is {today}. Please provide a brief summary of the top {count} technology news stories for today.
Focus on: AI developments, tech company news, new products, cybersecurity, and innovation.
Format: Brief overview followed by key headlines.
Keep it conversational and concise (under 300 words)."""
        
        elif category == "sports":
            prompt = f"""Today is {today}. Please provide a brief summary of the top {count} sports news stories for today.
Include: major game results, player news, upcoming matches, and significant sports events.
Format: Brief overview followed by key headlines.
Keep it conversational and concise (under 300 words)."""
        
        elif category == "business" or category == "finance":
            prompt = f"""Today is {today}. Please provide a brief summary of the top {count} business and finance news stories for today.
Include: market updates, company news, economic indicators, and major business developments.
Format: Brief overview followed by key headlines.
Keep it conversational and concise (under 300 words)."""
        
        else:
            prompt = f"""Today is {today}. Please provide a brief summary of the top {count} {category} news headlines for today.
Keep it conversational and concise (under 300 words)."""
        
        return prompt
    
    async def get_news_about_topic(
        self,
        user_id: str,
        topic: str
    ) -> Dict[str, Any]:
        """
        Get news about a specific topic
        
        Args:
            user_id: User identifier
            topic: Specific topic to search for
            
        Returns:
            Dict with status and news data
        """
        try:
            today = datetime.now().strftime("%B %d, %Y")
            
            prompt = f"""Today is {today}. Please provide a brief summary of recent news about: {topic}
Include the most relevant and recent information.
Format: Brief overview followed by key points.
Keep it conversational and concise (under 300 words)."""
            
            response = await self.client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful news assistant. Provide concise, factual information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            news_summary = response.choices[0].message.content
            
            return {
                "status": "success",
                "topic": topic,
                "date": today,
                "summary": news_summary,
                "message": news_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Topic news fetch error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"I'm having trouble finding news about {topic} right now."
            }
