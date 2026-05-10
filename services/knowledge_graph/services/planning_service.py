import logging
from typing import Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from utils.config import get_llm_config

logger = logging.getLogger(__name__)


class PlanningService:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        llm_config = get_llm_config()
        self.api_key = llm_config.get("google_api_key")
        
        # Use "Genius" model (Gemini 2.5 Pro) for planning
        model_name = self.config.get("planning_model", "gemini-2.5-pro")
        
        if self.api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=self.api_key,
                temperature=0.3,
            )
        else:
            # Fallback or error handling
            logger.warning("Google API key not found for PlanningService.")
            self.llm = None

    def generate_research_questions(self, ticker: str) -> List[str]:
        """
        Generates a list of specific research questions/queries for a given ticker.
        """
        if not self.llm:
            return [f"{ticker} supply chain news", f"{ticker} financial guidance", f"{ticker} production updates"]

        prompt = ChatPromptTemplate.from_template(
            """
            You are a senior financial analyst and supply chain expert.
            You are analyzing the company with ticker symbol: {ticker}.
            
            Generate 3-5 targeted search queries to uncover critical information about:
            1. Supply chain disruptions or major partnerships.
            2. Cash flow status and financial health.
            3. Future guidance and production outlook.
            
            Return ONLY the search queries as a Python list of strings.
            Example format: ["Query 1", "Query 2", "Query 3"]
            Do not include markdown formatting or explanations.
            """
        )
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"ticker": ticker})
            content = response.content.strip()
            
            # Remove markdown code blocks if present
            cleaned_content = content.replace("```python", "").replace("```", "").strip()
            
            # Basic parsing of list-like string
            import ast
            try:
                # Try to parse python list syntax
                queries = ast.literal_eval(cleaned_content)
                if isinstance(queries, list):
                    return queries
            except:
                pass
                
            # Fallback: split by newlines if AST fails
            queries = [q.strip().strip('"').strip('- ') for q in cleaned_content.split('\n') if q.strip()]
            return queries[:5]
                
            return [f"{ticker} news"] # Fallback
            
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return [f"{ticker} supply chain", f"{ticker} financial news"]

