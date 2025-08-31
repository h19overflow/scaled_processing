"""Markdown enhancer for integrating vision descriptions."""

import re
import logging
from typing import Dict, Optional


class MarkdownEnhancer:
    """Enhances markdown content with AI vision descriptions."""
    
    def __init__(self):
        """Initialize markdown enhancer."""
        self.logger = logging.getLogger(__name__)
    
    def enhance_content(self, content: str, descriptions: Dict[str, Dict]) -> str:
        """Enhance markdown content with vision descriptions.
        
        Args:
            content: Original markdown content
            descriptions: Dict of {image_id: {'description': str, 'classification': dict}}
            
        Returns:
            Enhanced markdown content
        """
        if not descriptions:
            return content
            
        enhanced_content = content
        
        # Find and replace image references
        for image_id, desc_data in descriptions.items():
            enhanced_content = self._replace_image_reference(
                enhanced_content, 
                image_id, 
                desc_data
            )
        
        self.logger.info(f"Enhanced {len(descriptions)} images in markdown")
        return enhanced_content
    
    def _replace_image_reference(self, content: str, image_id: str, desc_data: Dict) -> str:
        """Replace a single image reference with enhanced version."""
        description = desc_data.get('description', '')
        classification = desc_data.get('classification', {})
        
        # Pattern to match image references
        # Matches: ![...](image_1), ![...](picture-1.png), etc.
        patterns = [
            rf'!\[([^\]]*)\]\({re.escape(image_id)}[^\)]*\)',
            rf'!\[([^\]]*)\]\(picture-{image_id}\.png\)',
            rf'!\[([^\]]*)\]\(image_{image_id}[^\)]*\)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                original_text = match.group(0)
                original_caption = match.group(1)
                
                # Create enhanced version
                enhanced_text = self._create_enhanced_image_text(
                    original_text,
                    original_caption,
                    description,
                    classification
                )
                
                content = content.replace(original_text, enhanced_text)
        
        return content
    
    def _create_enhanced_image_text(self, original: str, caption: str, 
                                   description: str, classification: Dict) -> str:
        """Create enhanced image text with AI description."""
        parts = [original]
        
        # Add AI description if available
        if description and "Failed" not in description:
            confidence = classification.get('confidence', 0.0)
            parts.append(f"\n\n**AI Description** (confidence: {confidence:.1f}): {description}")
        
        # Add original caption if it exists and is different from description
        if caption and caption.strip() and caption.lower() not in description.lower():
            parts.append(f"\n\n**Caption**: *{caption}*")
        
        return "".join(parts)