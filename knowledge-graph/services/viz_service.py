import logging
import time
import re
import os
import json
from typing import Any, List, Optional

from google import genai
from google.genai import types
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from graph.models import Edge, Entity
from graph.store.base import GraphStore
from utils.config import get_llm_config
from services.chart_registry import ChartRegistry
from services.svg_layout_engine import SVGLayoutEngine

logger = logging.getLogger(__name__)


class VisualizationService:
    def __init__(self, graph_store: GraphStore | None = None, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.graph_store = graph_store
        llm_config = get_llm_config()
        self.api_key = llm_config.get("google_api_key")
        
        self.language = self.config.get("language", "en")
        
        # Initialize Unified Client for Image Generation
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
        
        # Prompt generator model (Text) using LangChain
        prompt_model_name = self.config.get("prompt_model", "gemini-3-pro")
        self.text_model = ChatGoogleGenerativeAI(
            model=prompt_model_name,
            google_api_key=self.api_key,
            temperature=0.7,
        )

        # Image generation model name
        self.image_model_name = self.config.get("image_model", "gemini-3-pro-image")

    def generate_infographic(self, entities: List[Entity], edges: List[Edge], context: str) -> str:
        """
        Generates an infographic based on the provided graph data.
        Returns the path to the generated file (SVG or Image).
        """
        if not self.api_key or not self.client:
            logger.warning("Google API key missing. Cannot generate visualization.")
            return ""

        # 1. Generate Article (if supported language)
        article_headline = ""
        article_text = ""
        if self.language == "zh-TW":
            try:
                article_headline, article_text = self.generate_article(entities, edges, context)
                logger.info(f"Generated Article: {article_headline}")
            except Exception as e:
                logger.error(f"Article generation failed: {e}")

        # 2. Determine if "Highly Concerned" (Dynamic)
        # Check if we should use high-quality image generation
        try:
            is_concerned = self._is_highly_concerned(context, entities)
        except Exception as e:
            logger.error(f"Failed to determine concern level: {e}")
            is_concerned = False

        output_path = ""
        image_prompt = ""

        if is_concerned:
            logger.info(f"Entity deemed 'Highly Concerned'. Using Gemini 3 Image Generation for: {context}")
            try:
                output_path = self._generate_image_infographic(entities, edges, context)
                image_prompt = "Gemini 3 Image Generation" # Placeholder or actual prompt if available
            except Exception as e:
                logger.error(f"Image generation failed, falling back to SVG: {e}")
                # Fallback to SVG
                output_path = self._generate_svg_infographic(entities, edges, context)
        else:
            logger.info(f"Standard entity. Using SVG Generation for: {context}")
            output_path = self._generate_svg_infographic(entities, edges, context)

        # 3. Save Article to file (alongside SVG)
        article_path = ""
        if article_text and output_path:
            article_path = output_path.replace(".svg", "_article.md").replace(".png", "_article.md")
            try:
                with open(article_path, "w", encoding="utf-8") as f:
                    f.write(f"# {article_headline}\n\n")
                    f.write(article_text)
                logger.info(f"Article saved to {article_path}")
            except Exception as e:
                logger.error(f"Failed to save article: {e}")

        # 4. Save to Graph Store
        if self.graph_store and output_path and (os.path.exists(output_path) or article_text):
            self._save_to_graph_store(entities, context, image_prompt, output_path, article_text, article_headline)

        return output_path

    def _is_highly_concerned(self, context: str, entities: List[Entity]) -> bool:
        """
        Uses LLM to determine if the subject is a 'highly concerned' stock or supply chain
        that warrants premium image generation.
        """
        prompt = ChatPromptTemplate.from_template(
            """
            Analyze the following context and entities.
            Determine if this is a "highly concerned" or "major" technology company/stock 
            (e.g., TSMC, Nvidia, Apple, Google, Microsoft, Tesla, or major supply chain hubs).
            
            Context: {context}
            Entities: {entities}
            
            Return ONLY "TRUE" or "FALSE".
            """
        )
        entity_names = ", ".join([e.props.get('name', e.id) for e in entities[:10]])
        chain = prompt | self.text_model
        result = chain.invoke({"context": context, "entities": entity_names})
        return "TRUE" in result.content.strip().upper()

    def _determine_chart_style(self, context: str, entities: List[Entity], edges: List[Edge]) -> str:
        """
        Uses LLM to select the best chart style from the ChartRegistry.
        """
        styles_list = ChartRegistry.list_styles()
        graph_summary = self._summarize_graph(entities, edges, context)
        
        prompt = ChatPromptTemplate.from_template(
            """
            You are an expert data visualization specialist.
            Select the MOST suitable chart style from the list below for the given supply chain data.
            
            Available Styles:
            {styles_list}
            
            Data Summary:
            {graph_summary}
            
            Consider:
            - Use "Structure & Hierarchy" for composition or ownership.
            - Use "Flow & Process" for movement of goods/data.
            - Use "Network & Relationship Topology" for complex webs.
            - Use "Spatial & Physical Layout" for maps or floor plans.
            
            Return ONLY the Style ID (e.g., "ORG_CHART").
            """
        )
        
        chain = prompt | self.text_model
        result = chain.invoke({"styles_list": styles_list, "graph_summary": graph_summary})
        style_id = result.content.strip().upper()
        
        # Validate
        if style_id in ChartRegistry.STYLES:
            return style_id
        else:
            logger.warning(f"LLM suggested invalid style {style_id}, defaulting to FORCE_DIRECTED")
            return "FORCE_DIRECTED"

    def _generate_svg_infographic(self, entities: List[Entity], edges: List[Edge], context: str) -> str:
        clean_context = context.replace(" ", "_").replace("/", "_")[:30]
        output_path = f"infographic_{clean_context}.svg"

        # Use programmatic layout engine (primary method)
        try:
            svg_code = self._generate_svg_with_layout_engine(entities, edges, context)
            if svg_code:
                with open(output_path, "w") as f:
                    f.write(svg_code)
                logger.info(f"SVG saved to {output_path} (layout engine)")
                return output_path
        except Exception as e:
            logger.warning(f"Layout engine failed, falling back to LLM: {e}")

        # Fallback to LLM generation
        style_id = self._determine_chart_style(context, entities, edges)
        style = ChartRegistry.get_style(style_id)
        logger.info(f"Selected Chart Style: {style.name} ({style_id})")

        max_retries = 2
        for i in range(max_retries):
            try:
                svg_prompt = self._create_svg_prompt(entities, edges, context, style)
                logger.info(f"Generating SVG code with LLM (Attempt {i+1}/{max_retries})...")

                result = self.text_model.invoke(svg_prompt)
                svg_code = result.content

                # Extract SVG
                if "```svg" in svg_code:
                    svg_code = svg_code.split("```svg")[1].split("```")[0].strip()
                elif "```xml" in svg_code:
                    svg_code = svg_code.split("```xml")[1].split("```")[0].strip()
                elif "```" in svg_code:
                    svg_code = svg_code.split("```")[1].split("```")[0].strip()

                if "<svg" not in svg_code:
                    raise ValueError("No SVG tag found in output")

                with open(output_path, "w") as f:
                    f.write(svg_code)

                logger.info(f"SVG saved to {output_path} (LLM)")
                return output_path

            except Exception as e:
                logger.error(f"LLM SVG generation failed: {e}")
                if i == max_retries - 1:
                    return ""
                time.sleep(2)
        return ""

    def _generate_svg_with_layout_engine(self, entities: List[Entity], edges: List[Edge], context: str) -> str:
        """Generate SVG using programmatic layout engine for consistent quality."""
        if not entities:
            return ""

        engine = SVGLayoutEngine(width=1440, height=900, max_nodes=20, language=self.language)

        # Find center entity (usually the main ticker/company)
        center_entity = None
        for e in entities:
            name_lower = (e.props.get("name", "") or e.id).lower()
            if any(kw in context.lower() for kw in [name_lower, e.id.lower()]):
                center_entity = {"id": e.id, "name": e.props.get("name", e.id), "type": e.type}
                break
        if not center_entity and entities:
            center_entity = {"id": entities[0].id, "name": entities[0].props.get("name", entities[0].id), "type": entities[0].type}

        # Prepare related entities
        related = []
        for e in entities:
            if e.id != center_entity["id"]:
                related.append({
                    "id": e.id,
                    "name": e.props.get("name", e.id),
                    "type": e.type,
                })

        # Prepare edges
        edge_data = []
        for e in edges:
            edge_data.append({
                "src": e.src,
                "dst": e.dst,
                "rel": e.rel,
            })

        # Extract ticker from context for title
        ticker = center_entity.get("name", center_entity.get("id", ""))
        title = f"供應鏈分析: {ticker.upper()}"

        # Generate layout
        layout = engine.layout_tiered(center_entity, related, edge_data, title=title)

        # Render to SVG
        return engine.render_svg(layout)

    def _generate_image_infographic(self, entities: List[Entity], edges: List[Edge], context: str) -> str:
        """
        Generates a high-quality image using Gemini 3 (Imagen/feature).
        """
        clean_context = context.replace(" ", "_").replace("/", "_")[:30]
        output_path = f"infographic_{clean_context}.png"
        
        graph_summary = self._summarize_graph(entities, edges, context)
        
        prompt = f"""
        Create a professional, high-detail supply chain infographic.
        Context: {context}
        Data: {graph_summary}
        
        Style: Modern, corporate, clean lines, professional color palette (Blues, Greys).
        Language: Traditional Chinese (繁體中文) labels where appropriate.
        """
        
        logger.info(f"Generating Image with {self.image_model_name}...")
        
        # Using google-genai client
        response = self.client.models.generate_image(
            model=self.image_model_name,
            prompt=prompt,
            config=types.GenerateImageConfig(
                number_of_images=1,
            )
        )
        
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"Image saved to {output_path}")
            return output_path
        else:
            raise ValueError("No image generated")

    def _create_svg_prompt(self, entities: List[Entity], edges: List[Edge], context: str, style) -> str:
        graph_summary = self._summarize_graph(entities, edges, context)
        
        language_instruction = ""
        if self.language == "zh-TW":
            language_instruction = "All text labels MUST be in Traditional Chinese (繁體中文). Tickers can remain in English."

        return f"""
            You are an expert data visualization designer and frontend developer.
            Create a PREMIUM, professional standalone SVG infographic for the following supply chain data.
            
            Chart Style: {style.name}
            Style Description: {style.description}
            Specific Instructions: {style.svg_instructions}
            
            Data:
            {graph_summary}
            
            Requirements:
            - Output ONLY valid raw SVG XML code starting with <svg and ending with </svg>.
            - Do NOT output markdown blocks.
            - SIZE: viewBox="0 0 1440 900" (MUST be exactly this)
            - TITLE: Include "供應鏈分析: [TICKER]" at top center (y=55, font-size 32px bold)
            - NODES: 
              - Large professional rounded rectangles (220x100 px, rx=15)
              - Two-line text: type label (14px) and name (18px bold)
              - Shadow filter effect
              - Stroke border 1.5px
            - EDGES: 
              - Cubic bezier curves with dashed stroke (dasharray="8,4")
              - White rectangle backgrounds behind edge labels
              - Arrow markers at end
            - FONTS: 'PingFang TC', 'Microsoft JhengHei', sans-serif
            - {language_instruction}
            - Professional color palette matching MCK/Tesla style
            
            Return ONLY the SVG code.
        """

    def generate_article(self, entities: List[Entity], edges: List[Edge], context: str) -> tuple[str, str]:
        graph_summary = self._summarize_graph(entities, edges, context)
        
        prompt_template = ChatPromptTemplate.from_template(
            """
            You are an expert supply chain analyst writing for a Taiwanese audience.
            Based on the following data, write a professional news article in Traditional Chinese (繁體中文).
            
            Data:
            {graph_data}
            
            Requirements:
            - Headline: Catchy and professional.
            - Body: Analyze the relationships, risks, and opportunities. Include specific tickers and company names.
            - Format: Markdown.
            - Language: Traditional Chinese (Taiwan).
            
            Output format:
            Headline: [Headline]
            
            [Article Body]
            """
        )
        chain = prompt_template | self.text_model
        result = chain.invoke({"graph_data": graph_summary})
        content = result.content
        
        parts = content.split("\n", 1)
        headline = parts[0].replace("Headline:", "").strip()
        body = parts[1].strip() if len(parts) > 1 else ""
        
        return headline, body

    def _summarize_graph(self, entities: List[Entity], edges: List[Edge], context: str) -> str:
        graph_summary = f"Context: {context}\n"
        graph_summary += "Entities:\n" + "\n".join([f"- {e.props.get('name', e.id)} ({e.type})" for e in entities])
        graph_summary += "\nRelationships:\n" + "\n".join([f"- {e.src} -> {e.dst}: {e.rel} ({e.props.get('status', '')})" for e in edges])
        return graph_summary

    def _save_to_graph_store(self, entities, context, image_prompt, output_path, article_text, article_headline):
        entity_id = entities[0].id if entities else "unknown"
        match = re.search(r"analysis for (\w+)", context)
        if match:
            ticker = match.group(1)
            for e in entities:
                if e.id == ticker or e.props.get("ticker") == ticker:
                    entity_id = e.id
                    break

        try:
            self.graph_store.upsert_infographic(
                entity_id=entity_id,
                context=context,
                image_prompt=image_prompt,
                image_path=output_path,
                article_text=article_text,
                article_headline=article_headline
            )
            logger.info("Infographic metadata saved to Graph Store.")
        except Exception as e:
            logger.error(f"Failed to save infographic to Graph Store: {e}")
