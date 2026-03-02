"""
Model Rollback Script
Rollback ML model to previous stable version.
"""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List

MODEL_REGISTRY = os.getenv('MODEL_REGISTRY', 'common/model_registry/')

class ModelRollback:
    def __init__(self):
        self.registry_path = Path(MODEL_REGISTRY)

    def list_versions(self, model_name: str) -> List[str]:
        """List all versions of a model."""
        versions = []
        for model_dir in self.registry_path.glob(f"{model_name}_*"):
            if model_dir.is_dir():
                versions.append(model_dir.name)
        return sorted(versions, reverse=True)

    def get_current_version(self, model_name: str) -> str:
        """Get current active version."""
        link_path = self.registry_path / f"{model_name}_latest"
        if link_path.exists() and link_path.is_symlink():
            return link_path.readlink().name
        return None

    def rollback(
        self, model_name: str, target_version: str = None
    ) -> Dict:
        """Rollback model to target version."""
        versions = self.list_versions(model_name)
        current = self.get_current_version(model_name)
        
        if not versions:
            return {
                'status': 'error',
                'message': f'No versions found for {model_name}'
            }
        
        # Default to previous version
        if target_version is None:
            if len(versions) < 2:
                return {
                    'status': 'error',
                    'message': 'No previous version available'
                }
            target_version = versions[1]
        
        target_path = self.registry_path / target_version
        if not target_path.exists():
            return {
                'status': 'error',
                'message': f'Version {target_version} not found'
            }
        
        # Update symlink
        link_path = self.registry_path / f"{model_name}_latest"
        if link_path.exists():
            link_path.unlink()
        link_path.symlink_to(target_path)
        
        return {
            'status': 'success',
            'model': model_name,
            'previous_version': current,
            'new_version': target_version
        }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Rollback ML model')
    parser.add_argument('--model', required=True, help='Model name')
    parser.add_argument('--version', help='Target version (default: previous)')
    args = parser.parse_args()
    
    rollback = ModelRollback()
    result = rollback.rollback(args.model, args.version)
    print(json.dumps(result, indent=2))
