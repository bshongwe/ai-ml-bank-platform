"""
Model Registry
Version control, lineage tracking, approval workflow.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

REGISTRY_PATH = Path('common/model_registry')

class ModelRegistry:
    def __init__(self, registry_path: str = None):
        self.registry_path = Path(
            registry_path or REGISTRY_PATH
        ).resolve()
        self.registry_path.mkdir(parents=True, exist_ok=True)

    def register_model(
        self, model_version: str, metadata: Dict[str, Any]
    ) -> None:
        """Register new model version with metadata."""
        model_path = self.registry_path / model_version
        model_path.mkdir(parents=True, exist_ok=True)
        metadata['registered_at'] = datetime.utcnow().isoformat()
        metadata['status'] = 'pending_approval'
        with open(
            model_path / 'metadata.json', 'w', encoding='utf-8'
        ) as f:
            json.dump(metadata, f, indent=2)

    def approve_model(self, model_version: str) -> None:
        """Approve model for production deployment."""
        metadata = self.get_metadata(model_version)
        metadata['status'] = 'approved'
        metadata['approved_at'] = datetime.utcnow().isoformat()
        model_path = self.registry_path / model_version
        with open(
            model_path / 'metadata.json', 'w', encoding='utf-8'
        ) as f:
            json.dump(metadata, f, indent=2)

    def get_metadata(self, model_version: str) -> Dict[str, Any]:
        """Retrieve model metadata."""
        model_path = self.registry_path / model_version
        with open(model_path / 'metadata.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_models(self, status: Optional[str] = None) -> list:
        """List all registered models, optionally filtered by status."""
        models = []
        for model_dir in self.registry_path.iterdir():
            if model_dir.is_dir():
                try:
                    metadata = self.get_metadata(model_dir.name)
                    if status is None or metadata.get('status') == status:
                        models.append({
                            'version': model_dir.name,
                            'status': metadata.get('status'),
                            'registered_at': metadata.get('registered_at')
                        })
                except FileNotFoundError:
                    continue
        return sorted(models, key=lambda x: x['registered_at'], reverse=True)

if __name__ == '__main__':
    registry = ModelRegistry()
    print("Approved models:")
    for model in registry.list_models(status='approved'):
        print(f"  {model['version']} - {model['registered_at']}")
