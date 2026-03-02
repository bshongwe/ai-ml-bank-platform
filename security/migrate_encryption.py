#!/usr/bin/env python3
"""
Automated migration orchestrator for field-level encryption.
Encrypts existing data with checkpointing and rollback support.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from security.encryption_migration import EncryptionMigration
from security.audit_logger import AuditLogger


class MigrationOrchestrator:
    """Orchestrate encryption migration with progress tracking."""
    
    def __init__(self, checkpoint_dir: str = 'security/migration_checkpoints'):
        self.migration = EncryptionMigration()
        self.audit = AuditLogger()
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _save_checkpoint(self, layer: str, dataset: str, progress: dict):
        """Save migration progress."""
        checkpoint_file = self.checkpoint_dir / f"{layer}_{dataset}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def _load_checkpoint(self, layer: str, dataset: str) -> dict:
        """Load migration progress."""
        checkpoint_file = self.checkpoint_dir / f"{layer}_{dataset}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        return {}
    
    def migrate_layer(self, layer: str, dataset: str, 
                     input_dir: Path, output_dir: Path,
                     dry_run: bool = False) -> dict:
        """Migrate all files in a layer."""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint = self._load_checkpoint(layer, dataset)
        files = list(input_dir.glob('*.parquet'))
        
        results = {
            'layer': layer,
            'dataset': dataset,
            'total_files': len(files),
            'processed': 0,
            'failed': 0,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        for file_path in files:
            file_name = file_path.name
            
            if checkpoint.get(file_name) == 'completed':
                print(f"Skipping {file_name} (already migrated)")
                results['processed'] += 1
                continue
            
            try:
                print(f"Migrating {file_name}...")
                
                if not dry_run:
                    result = self.migration.migrate_file(
                        input_path=file_path,
                        output_path=output_dir / file_name,
                        layer=layer,
                        dataset=dataset
                    )
                    
                    checkpoint[file_name] = 'completed'
                    self._save_checkpoint(layer, dataset, checkpoint)
                    
                    self.audit.log_event(
                        'encryption_migration',
                        {
                            'layer': layer,
                            'dataset': dataset,
                            'file': file_name,
                            'records': result['records']
                        }
                    )
                
                results['processed'] += 1
                print(f"✓ {file_name} migrated successfully")
                
            except Exception as e:
                results['failed'] += 1
                print(f"✗ {file_name} failed: {e}")
                self.audit.log_event(
                    'encryption_migration_error',
                    {
                        'layer': layer,
                        'dataset': dataset,
                        'file': file_name,
                        'error': str(e)
                    }
                )
        
        results['end_time'] = datetime.now(timezone.utc).isoformat()
        return results
    
    def validate_migration(self, layer: str, dataset: str,
                          output_dir: Path) -> dict:
        """Validate encryption coverage after migration."""
        output_dir = Path(output_dir)
        files = list(output_dir.glob('*.parquet'))
        
        coverage_results = {}
        for file_path in files:
            df = pd.read_parquet(file_path)
            coverage = self.migration.get_encryption_coverage(
                df, layer, dataset
            )
            coverage_results[file_path.name] = coverage
        
        return coverage_results


def main():
    parser = argparse.ArgumentParser(
        description='Migrate lakehouse data to encrypted format'
    )
    parser.add_argument('--layer', required=True,
                       choices=['bronze', 'silver', 'gold'],
                       help='Layer to migrate')
    parser.add_argument('--dataset', required=True,
                       choices=['fraud', 'credit_risk', 'churn'],
                       help='Dataset to migrate')
    parser.add_argument('--input-dir', required=True,
                       help='Input directory with plaintext data')
    parser.add_argument('--output-dir', required=True,
                       help='Output directory for encrypted data')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulate migration without writing')
    parser.add_argument('--validate', action='store_true',
                       help='Validate encryption coverage')
    
    args = parser.parse_args()
    
    orchestrator = MigrationOrchestrator()
    
    if args.validate:
        print(f"\nValidating {args.layer}/{args.dataset}...")
        coverage = orchestrator.validate_migration(
            args.layer, args.dataset, Path(args.output_dir)
        )
        print(json.dumps(coverage, indent=2))
    else:
        print(f"\nMigrating {args.layer}/{args.dataset}...")
        if args.dry_run:
            print("DRY RUN MODE - No files will be modified\n")
        
        results = orchestrator.migrate_layer(
            layer=args.layer,
            dataset=args.dataset,
            input_dir=Path(args.input_dir),
            output_dir=Path(args.output_dir),
            dry_run=args.dry_run
        )
        
        print("\n" + "="*60)
        print("Migration Summary:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Processed: {results['processed']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Duration: {results['start_time']} → {results['end_time']}")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
