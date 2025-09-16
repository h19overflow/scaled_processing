"""
Table configuration manager for loading and caching table extraction configurations.
Handles JSON config files and converts them to TableExtractionConfig objects.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional,List

from datetime import datetime

from src.backend.doc_processing_system.data_models.table_extraction import (
    TableExtractionConfig,
    TableFieldMapping
)


class TableConfigManager:
    """Manages loading and caching of table extraction configurations."""

    def __init__(self, config_dir: str = "data/extraction_schema_TNB"):
        """Initialize table config manager.

        Args:
            config_dir: Directory containing table extraction configurations
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self._cached_configs: Dict[str, TableExtractionConfig] = {}

    def load_table_config(self, doc_type: str) -> Optional[TableExtractionConfig]:
        """Load table extraction configuration for document type.

        Args:
            doc_type: Document type to load config for

        Returns:
            TableExtractionConfig object or None if not found
        """
        # Return cached config if available
        if doc_type in self._cached_configs:
            self.logger.debug(f"Returning cached config for {doc_type}")
            return self._cached_configs[doc_type]

        # Try to load from file
        config = self._load_config_from_file(doc_type)

        if config:
            # Cache the loaded config
            self._cached_configs[doc_type] = config
            self.logger.info(f"Loaded and cached config for {doc_type}")

        return config

    def _load_config_from_file(self, doc_type: str) -> Optional[TableExtractionConfig]:
        """Load configuration from JSON file."""
        config_file = self.config_dir / f"{doc_type}_table_config.json"

        # Try specific config first
        if not config_file.exists():
            # Try fallback to general config
            config_file = self.config_dir / "general_table_config.json"
            if not config_file.exists():
                self.logger.warning(f"No config file found for {doc_type}")
                return None

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            return self._parse_config_data(config_data, doc_type)

        except Exception as e:
            self.logger.error(f"Failed to load config from {config_file}: {e}")
            return None

    def _parse_config_data(self, config_data: Dict, doc_type: str) -> TableExtractionConfig:
        """Parse JSON config data into TableExtractionConfig object."""
        # Convert field mappings
        field_mappings = [
            TableFieldMapping(**mapping)
            for mapping in config_data.get('field_mappings', [])
        ]

        # Create config object
        config = TableExtractionConfig(
            document_type=config_data.get('document_type', doc_type),
            description=config_data.get('description', ''),
            field_mappings=field_mappings,
            validation_rules=config_data.get('validation_rules', {}),
            created_by=config_data.get('created_by', 'system'),
            created_at=datetime.now()
        )

        return config

    def create_sample_config(self, doc_type: str = "tnb_utilities") -> bool:
        """Create a sample configuration file for testing.

        Args:
            doc_type: Document type to create config for

        Returns:
            True if config created successfully, False otherwise
        """
        try:
            sample_mappings = self._get_sample_mappings(doc_type)

            config_data = {
                "document_type": doc_type,
                "description": f"Table extraction configuration for {doc_type} documents",
                "field_mappings": sample_mappings,
                "validation_rules": {},
                "created_by": "system"
            }

            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            config_file = self.config_dir / f"{doc_type}_table_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Created sample config: {config_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create sample config: {e}")
            return False

    def _get_sample_mappings(self, doc_type: str) -> List[Dict]:
        """Get sample field mappings for document type."""
        if doc_type == "gspp_billing":
            return [
                {
                    "field_name": "puncak_penggunaan",
                    "english_translation": "Peak usage (kWh)",
                    "table_id": 0,
                    "extraction_path": "data[0]['Penggunaan']",
                    "example_value": "12345.67",
                    "field_type": "float",
                    "is_required": True
                },
                {
                    "field_name": "luar_puncak_penggunaan",
                    "english_translation": "Off-peak usage (kWh)",
                    "table_id": 0,
                    "extraction_path": "data[1]['Penggunaan']",
                    "example_value": "23456.78",
                    "field_type": "float",
                    "is_required": True
                }
            ]
        else:
            return [
                {
                    "field_name": "beban_diisytiharkan_kW",
                    "english_translation": "Declared load in kW",
                    "table_id": 1,
                    "extraction_path": "data[0]['Value']",
                    "example_value": "950.00kW",
                    "field_type": "float",
                    "is_required": True
                },
                {
                    "field_name": "jumlah_penggunaan",
                    "english_translation": "Total usage (in kWh)",
                    "table_id": 3,
                    "extraction_path": "data[4]['Amaun (RM)']",
                    "example_value": "277,411.00",
                    "field_type": "float",
                    "is_required": True
                }
            ]

    def clear_cache(self):
        """Clear all cached configurations."""
        self._cached_configs.clear()
        self.logger.info("Configuration cache cleared")

    def get_cached_config_types(self) -> List[str]:
        """Get list of document types with cached configurations."""
        return list(self._cached_configs.keys())