"""
ImageSerializer - Advanced image serialization strategies for document processing.
Handles conversion of Docling image objects to various formats.
"""

import logging
from typing import Dict, Any

from docling.datamodel.document import ConversionResult
from .serialization_strategies import SerializationStrategy


class ImageSerializer:
    """Advanced image serialization with multiple strategy support."""
    
    def __init__(self, strategy: SerializationStrategy = SerializationStrategy.DETAILED):
        """Initialize image serializer with specified strategy.
        
        Args:
            strategy: Serialization strategy to use
        """
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
    
    def serialize_image(self, picture, image_id: int, result: ConversionResult) -> Dict[str, Any]:
        """Serialize image using configured strategy.
        
        Args:
            picture: Docling picture object
            image_id: Unique image identifier
            result: Full conversion result for context
            
        Returns:
            Dict containing serialized image data
        """
        base_data = {
            "image_id": image_id,
            "strategy": self.strategy.value
        }
        
        if self.strategy == SerializationStrategy.STRUCTURED:
            base_data.update(self._serialize_structured(picture))
        elif self.strategy == SerializationStrategy.MARKDOWN:
            base_data.update(self._serialize_markdown(picture))
        elif self.strategy == SerializationStrategy.JSON:
            base_data.update(self._serialize_json(picture))
        elif self.strategy == SerializationStrategy.DETAILED:
            base_data.update(self._serialize_detailed(picture, result))
        else:  # DEFAULT
            base_data.update({
                "caption": getattr(picture, 'caption', ''),
                "position": getattr(picture, 'prov', []),
                "size": getattr(picture, 'size', {})
            })
        
        return base_data
    
    def _serialize_structured(self, picture) -> Dict[str, Any]:
        """Structured image serialization."""
        return {
            "caption": getattr(picture, 'caption', ''),
            "description": getattr(picture, 'description', ''),
            "alt_text": getattr(picture, 'alt_text', ''),
            "position": getattr(picture, 'prov', []),
            "dimensions": getattr(picture, 'size', {}),
            "image_type": "structured_metadata"
        }
    
    def _serialize_markdown(self, picture) -> Dict[str, Any]:
        """Markdown image serialization."""
        caption = getattr(picture, 'caption', '')
        alt_text = getattr(picture, 'alt_text', caption)
        description = getattr(picture, 'description', '')
        
        markdown_content = f"![{alt_text}](image_{getattr(picture, 'image_id', 'unknown')})"
        if caption:
            markdown_content += f"\n\n*{caption}*"
        if description:
            markdown_content += f"\n\n{description}"
        
        return {
            "markdown_content": markdown_content,
            "alt_text": alt_text,
            "caption": caption,
            "description": description,
            "image_type": "markdown_formatted"
        }
    
    def _serialize_json(self, picture) -> Dict[str, Any]:
        """JSON image serialization."""
        json_data = {
            "metadata": {
                "caption": getattr(picture, 'caption', ''),
                "description": getattr(picture, 'description', ''),
                "alt_text": getattr(picture, 'alt_text', ''),
                "position": getattr(picture, 'prov', []),
                "dimensions": getattr(picture, 'size', {}),
            },
            "attributes": {}
        }
        
        # Add any available attributes
        for attr in ['format', 'mime_type', 'path', 'uri']:
            if hasattr(picture, attr):
                json_data["attributes"][attr] = getattr(picture, attr)
        
        return {
            "json_representation": json_data,
            "image_type": "json_structured",
            "serializable": True
        }
    
    def _serialize_detailed(self, picture, result: ConversionResult) -> Dict[str, Any]:
        """Detailed image serialization with comprehensive analysis."""
        detailed_data = {
            "image_type": "detailed_analysis",
            "basic_metadata": {
                "caption": getattr(picture, 'caption', ''),
                "description": getattr(picture, 'description', ''),
                "alt_text": getattr(picture, 'alt_text', ''),
            },
            "position_data": {
                "prov": getattr(picture, 'prov', []),
                "bbox": getattr(picture, 'bbox', {}),
                "page_number": getattr(picture, 'page', None)
            },
            "technical_metadata": {
                "dimensions": getattr(picture, 'size', {}),
                "format": getattr(picture, 'format', ''),
                "mime_type": getattr(picture, 'mime_type', ''),
            }
        }
        
        # Extract contextual information
        try:
            # Try to get surrounding text context
            markdown_content = result.document.export_to_markdown()
            image_context = self._extract_image_context(markdown_content, detailed_data["basic_metadata"]["caption"])
            detailed_data["contextual_data"] = image_context
        except Exception as e:
            detailed_data["contextual_data"] = {"error": str(e)}
        
        # Add any other available attributes
        additional_attrs = {}
        for attr in dir(picture):
            if not attr.startswith('_') and attr not in ['caption', 'description', 'alt_text', 'prov', 'size', 'format', 'mime_type']:
                try:
                    value = getattr(picture, attr)
                    if not callable(value):
                        additional_attrs[attr] = str(value) if value is not None else None
                except:
                    pass
        
        if additional_attrs:
            detailed_data["additional_attributes"] = additional_attrs
        
        return detailed_data
    
    def _extract_image_context(self, markdown_content: str, caption: str) -> Dict[str, Any]:
        """Extract contextual information around images from markdown content."""
        try:
            lines = markdown_content.split('\n')
            context_data = {
                "preceding_text": [],
                "following_text": [],
                "section_heading": None,
                "paragraph_context": []
            }
            
            # Look for image references and context
            for i, line in enumerate(lines):
                if '<!-- image -->' in line.lower() or (caption and caption.lower() in line.lower()):
                    # Get preceding context
                    start_idx = max(0, i - 3)
                    context_data["preceding_text"] = [l.strip() for l in lines[start_idx:i] if l.strip()]
                    
                    # Get following context
                    end_idx = min(len(lines), i + 4)
                    context_data["following_text"] = [l.strip() for l in lines[i+1:end_idx] if l.strip()]
                    
                    # Find nearest section heading
                    for j in range(i, -1, -1):
                        if lines[j].strip().startswith('#'):
                            context_data["section_heading"] = lines[j].strip().lstrip('#').strip()
                            break
                    
                    break
            
            return context_data
            
        except Exception as e:
            return {"error": str(e)}
