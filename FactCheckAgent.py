from KnowledgeGraphService import KnowledgeGraphService, Graph
from MongoDBService import MongoDBService
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from TwitterXAPIService import TwitterXAPIService
from langchain_core.prompts import PromptTemplate
from settings import settings
from firecrawl import Firecrawl
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
import json


class Source(BaseModel):
    """Schema for source information."""

    title: str
    ratingStance: str
    snippet: str

class OutputSchema(BaseModel):
    """Schema for response."""

    confidenceScores: float
    reasoning: str
    sources: list[Source]
    justification: str


custom_prompt = PromptTemplate(
    input_variables=["tweet", "context_community", "context_web"],
    template="""
                You are a fact-checking and text-analysis assistant.

                Your task is to evaluate the factuality of the given statement using Community Graph as the primary information source.
                If the Community Graph does not provide enough evidence, you may use other reliable external sources.

                You must return ONLY a single JSON object in the exact structure shown below:

                {{
                    "confidenceScores": number,
                    "reasoning": string,
                "sources": [
                 {{
                    "title": string,
                    "ratingStance": "Mostly Support" | "Partially Support" | "Opposite",
                    "snippet": string
                }}
            ]
            }}

            Input Statement:
            {tweet}
            
            Context from Community Graph (Twitter, Community Notes):
            {context_community}
            
            Context from Web Crawl:
            {context_web}

            Field Requirements:
            - confidenceScores: A number from 0 to 100 indicating your overall confidence in your final fact-checking conclusion.
            - reasoning: A clear explanation describing:
            - How you checked the statement.
            - What the Community Graph provided.
            - When and why you used external sources.
            - Why you concluded the claim is supported, partially supported, or contradicted.
            - sources:
            - title — article source title, if its from the web crawl; otherwise, indicate "Community Graph"
            - ratingStance — your evaluation of whether the source supports or contradicts the claim
            - snippet — a short excerpt from the source that supports your stance

            Do not add extra fields. Do not add text outside the JSON.
    """
)

            
class FactCheckAgent:
    def __init__(self, kg_service: KnowledgeGraphService, mongo_service: MongoDBService, temperature=0, model_name="gpt-4-turbo"):
        self.kg_service = kg_service
        if mongo_service is not None:
            self.mongo_service = mongo_service
        OPENAI_API_KEY = settings.OPENAI_API_KEY
        if OPENAI_API_KEY is None:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY,temperature=temperature, model_name=model_name)
        self.twitter_api_service = TwitterXAPIService(
            api_key=settings.TWITTER_API_KEY,
            api_secret_key=settings.TWITTER_API_SECRET_KEY,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
            bearer_token=settings.TWITTER_ACCESS_BEARER_TOKEN
        )
        
        self.firecrawl = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
        self.parser = PydanticOutputParser(pydantic_object=OutputSchema)
        self.prompt = custom_prompt
        
    def get_context_from_kag(self,statement: str) -> str:
        return self.kg_service.get_context(statement)
            
    
    def crawl_web_for_facts(self,statement: str) -> str:
        results = self.firecrawl.search(
            query=statement,
            sources=["news"],
            limit=3,
            scrape_options={"formats": ["markdown", "links"]}
        )
        
        if not getattr(results, "success", False):
            return "No external information found."
        
        combined_text = ""
        for item in getattr(results, "data", []):
            title = getattr(item, "title", None) if not isinstance(item, dict) else item.get("title")
            snippet = getattr(item, "snippet", None) if not isinstance(item, dict) else item.get("snippet")
            url = getattr(item, "url", None) if not isinstance(item, dict) else item.get("url")

            combined_text += f"Title: {title}\n"
            combined_text += f"Snippet: {snippet}\n"
            combined_text += f"Link: {url}\n\n"

        return combined_text or "No external information found."
    
    def generate_final_response(self,statement: str) -> json:
        
        context_community = self.get_context_from_kag(statement)
        context_web = self.crawl_web_for_facts(statement)
        

        prompt_text = self.prompt.format(
            tweet=statement,
            context_community=context_community,
            context_web=context_web,
        )

        ai_message = self.llm.invoke(prompt_text)
        raw = ai_message.content.strip() 

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError(f"Model did not return valid JSON: {raw}")

        return data

    def invoke(self, twitter_id: str) -> dict:
        
        response = self.twitter_api_service.get_tweet(twitter_id)
        statement = response["data"][0]["text"]
        print(f"Statement: {statement}")
        
        if not statement:
            raise ValueError("No text found in the tweet.")
        result = self.generate_final_response(statement)
        print("Fact-Check Result:", result)

        return result
     
        


