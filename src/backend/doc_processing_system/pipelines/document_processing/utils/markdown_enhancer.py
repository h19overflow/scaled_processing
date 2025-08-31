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
            self.logger.debug("No descriptions provided, returning original content")
            return content
        
        self.logger.debug(f"Enhancing content with {len(descriptions)} descriptions")
        self.logger.debug(f"Image IDs: {list(descriptions.keys())}")
        self.logger.debug(f"Content preview: {content[:200]}...")
            
        enhanced_content = content
        
        # Since Docling uses <!-- image --> comments sequentially, we need to replace them in order
        enhanced_content = self._replace_image_comments_in_order(enhanced_content, descriptions)
        
        enhancements_made = len([d for d in descriptions.values() if d.get('description')])
        self.logger.info(f"Enhanced {enhancements_made} of {len(descriptions)} images in markdown")
        return enhanced_content
    
    def _replace_image_comments_in_order(self, content: str, descriptions: Dict[str, Dict]) -> str:
        """Replace <!-- image --> comments with enhanced markdown in sequential order."""
        
        # Find all <!-- image --> comments
        image_comment_pattern = r'<!--\s*image\s*-->'
        comments = list(re.finditer(image_comment_pattern, content, re.IGNORECASE))
        
        self.logger.debug(f"Found {len(comments)} image comments in content")
        
        if not comments:
            self.logger.warning("No <!-- image --> comments found in content")
            return content
        
        # Sort image IDs numerically since Docling processes them sequentially  
        sorted_image_ids = sorted(descriptions.keys(), key=lambda x: int(x))
        self.logger.debug(f"Processing images in order: {sorted_image_ids}")
        
        # Replace comments in reverse order to avoid offset issues
        enhanced_content = content
        for i in reversed(range(len(comments))):
            if i < len(sorted_image_ids):
                image_id = sorted_image_ids[i]
                desc_data = descriptions[image_id]
                
                comment_match = comments[i]
                original_comment = comment_match.group(0)
                
                # Create enhanced markdown
                enhanced_markdown = self._create_enhanced_markdown_from_comment(
                    image_id, desc_data
                )
                
                # Replace the comment
                start, end = comment_match.span()
                enhanced_content = (
                    enhanced_content[:start] + 
                    enhanced_markdown + 
                    enhanced_content[end:]
                )
                
                self.logger.debug(f"Replaced comment {i} with enhanced content for image {image_id}")
        
        return enhanced_content
    
    def _create_enhanced_markdown_from_comment(self, image_id: str, desc_data: Dict) -> str:
        """Create enhanced markdown to replace <!-- image --> comment."""
        description = desc_data.get('description', '')
        classification = desc_data.get('classification', {})
        image_path = desc_data.get('image_path', f'picture-{image_id}.png')
        
        if not description or "Failed" in description:
            # If no valid description, just return a basic image reference
            return f"![Image {image_id}]({image_path})"
        
        # Create enhanced markdown with AI description
        confidence = classification.get('confidence', 0.0)
        
        enhanced_parts = [
            f"![Image {image_id}]({image_path})",
            "",  # Empty line
            f"**AI Analysis** (confidence: {confidence:.1f}): {description}",
            ""   # Empty line after
        ]
        
        return "\n".join(enhanced_parts)
    
    def _replace_image_reference(self, content: str, image_id: str, desc_data: Dict) -> str:
        """Replace a single image reference with enhanced version."""
        description = desc_data.get('description', '')
        classification = desc_data.get('classification', {})
        
        self.logger.debug(f"Looking for image_id: {image_id}, description: {description[:50] if description else 'None'}...")
        
        # Docling exports images as HTML comments, not markdown image syntax
        # We need to replace <!-- image --> comments with proper markdown + descriptions
        # Pattern to match HTML image comments
        patterns = [
            r'<!--\s*image\s*-->',  # Matches <!-- image -->
            r'<!--\s*Image\s*-->',  # Matches <!-- Image -->
            r'<!--\s*IMAGE\s*-->'   # Matches <!-- IMAGE -->
        ]
        
        matches_found = 0
        for i, pattern in enumerate(patterns):
            self.logger.debug(f"Trying pattern {i}: {pattern}")
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            
            if matches:
                self.logger.debug(f"Pattern {i} found {len(matches)} matches")
                matches_found += len(matches)
                
                for match in matches:
                    original_text = match.group(0)
                    original_caption = match.group(1)
                    
                    self.logger.debug(f"Found match: {original_text}")
                    
                    # Create enhanced version
                    enhanced_text = self._create_enhanced_image_text(
                        original_text,
                        original_caption,
                        description,
                        classification
                    )
                    
                    content = content.replace(original_text, enhanced_text)
            else:
                self.logger.debug(f"Pattern {i} found no matches")
        
        if matches_found == 0:
            self.logger.warning(f"No image references found for image_id: {image_id}")
            # Try to find any image references in the content for debugging
            all_image_refs = re.findall(r'!\[[^\]]*\]\([^)]+\)', content)
            self.logger.debug(f"All image references found in content: {all_image_refs}")
        
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