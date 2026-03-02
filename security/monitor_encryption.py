#!/usr/bin/env python3
"""
Encryption migration monitoring dashboard.
Tracks coverage, performance, and issues across all layers.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from security.encryption_migration import EncryptionMigration
from tabulate import tabulate


class MigrationMonitor:
    """Monitor encryption migration progress."""
    
    def __init__(self):
        self.migration = EncryptionMigration()
        self.checkpoint_dir = Path('security/migration_checkpoints')
    
    def get_layer_status(self, layer: str, dataset: str,
                        data_dir: Path) -> dict:
        """Get encryption status for a layer."""
        data_dir = Path(data_dir)
        if not data_dir.exists():
            return {'status': 'not_found', 'coverage': {}}
        
        files = list(data_dir.glob('*.parquet'))
        if not files:
            return {'status': 'empty', 'coverage': {}}
        
        total_records = 0
        encrypted_records = 0
        field_coverage = {}
        
        for file_path in files:
            try:
                df = pd.read_parquet(file_path)
                total_records += len(df)
                
                coverage = self.migration.get_encryption_coverage(
                    df, layer, dataset
                )
                
                for field, stats in coverage.items():
                    if field not in field_coverage:
                        field_coverage[field] = {
                            'encrypted': 0, 'total': 0
                        }
                    field_coverage[field]['encrypted'] += stats['encrypted']
                    field_coverage[field]['total'] += stats['total']
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        for field in field_coverage:
            encrypted_records += field_coverage[field]['encrypted']
        
        overall_pct = (encrypted_records / (total_records * len(field_coverage)) * 100
                      if total_records > 0 else 0)
        
        return {
            'status': 'in_progress' if overall_pct < 100 else 'complete',
            'total_records': total_records,
            'overall_coverage': round(overall_pct, 2),
            'field_coverage': {
                field: round(stats['encrypted'] / stats['total'] * 100, 2)
                for field, stats in field_coverage.items()
            }
        }
    
    def generate_report(self) -> str:
        """Generate migration status report."""
        layers = ['bronze', 'silver', 'gold']
        datasets = ['fraud', 'credit_risk', 'churn']
        
        report = []
        report.append("="*80)
        report.append("ENCRYPTION MIGRATION STATUS")
        report.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        report.append("="*80)
        report.append("")
        
        table_data = []
        for layer in layers:
            for dataset in datasets:
                data_dir = Path(f'lake/{layer}/{dataset}')
                status = self.get_layer_status(layer, dataset, data_dir)
                
                table_data.append([
                    layer.upper(),
                    dataset,
                    status.get('total_records', 0),
                    f"{status.get('overall_coverage', 0)}%",
                    status.get('status', 'unknown')
                ])
        
        report.append(tabulate(
            table_data,
            headers=['Layer', 'Dataset', 'Records', 'Coverage', 'Status'],
            tablefmt='grid'
        ))
        report.append("")
        
        # Field-level details
        report.append("FIELD-LEVEL COVERAGE:")
        report.append("-"*80)
        for layer in layers:
            for dataset in datasets:
                data_dir = Path(f'lake/{layer}/{dataset}')
                status = self.get_layer_status(layer, dataset, data_dir)
                
                if status.get('field_coverage'):
                    report.append(f"\n{layer.upper()}/{dataset}:")
                    for field, pct in status['field_coverage'].items():
                        report.append(f"  {field}: {pct}%")
        
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)
    
    def check_migration_health(self) -> dict:
        """Check for migration issues."""
        issues = []
        
        # Check for stalled migrations
        if self.checkpoint_dir.exists():
            for checkpoint_file in self.checkpoint_dir.glob('*.json'):
                with open(checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                
                if checkpoint:
                    layer, dataset = checkpoint_file.stem.split('_')
                    issues.append({
                        'type': 'incomplete_migration',
                        'layer': layer,
                        'dataset': dataset,
                        'files_remaining': len([
                            k for k, v in checkpoint.items() 
                            if v != 'completed'
                        ])
                    })
        
        return {
            'healthy': len(issues) == 0,
            'issues': issues
        }


def main():
    monitor = MigrationMonitor()
    
    print(monitor.generate_report())
    
    health = monitor.check_migration_health()
    if not health['healthy']:
        print("\n⚠️  MIGRATION ISSUES DETECTED:")
        for issue in health['issues']:
            print(f"  - {issue['type']}: {issue['layer']}/{issue['dataset']}")
    else:
        print("\n✓ All migrations healthy")


if __name__ == '__main__':
    main()
