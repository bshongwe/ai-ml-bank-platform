"""
Archive Bronze Data
Move old Bronze data to cold storage for cost savings.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

BRONZE_PATH = os.getenv('BRONZE_PATH', 'lake/bronze/')
ARCHIVE_DAYS = int(os.getenv('ARCHIVE_DAYS', '90'))

class BronzeArchiver:
    def __init__(self):
        self.bronze_path = Path(BRONZE_PATH)
        self.archive_days = ARCHIVE_DAYS

    def list_old_files(self, days_old: int = None) -> List[Path]:
        """List files older than threshold."""
        if days_old is None:
            days_old = self.archive_days
        
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days_old)
        old_files = []
        
        for file_path in self.bronze_path.rglob('*.json'):
            file_time = datetime.fromtimestamp(
                file_path.stat().st_mtime
            )
            if file_time < cutoff_date:
                old_files.append(file_path)
        
        return old_files

    def archive_files(
        self, days_old: int = None, dry_run: bool = True
    ) -> int:
        """Archive old Bronze files to cold storage."""
        old_files = self.list_old_files(days_old)
        
        print(f"Found {len(old_files)} files to archive")
        
        if dry_run:
            print("Dry run mode - not archiving")
            return len(old_files)
        
        try:
            import boto3
            s3 = boto3.client('s3')
            bucket = os.getenv('BRONZE_BUCKET', 'ml-platform-bronze')
            
            for file_path in old_files:
                key = str(file_path.relative_to(self.bronze_path))
                s3.upload_file(
                    str(file_path),
                    bucket,
                    key,
                    ExtraArgs={'StorageClass': 'GLACIER'}
                )
                file_path.unlink()
            
            print(f"Archived {len(old_files)} files to Glacier")
        except Exception as e:
            print(f"Archive error: {e}")
            return 0
        
        return len(old_files)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Archive Bronze data')
    parser.add_argument(
        '--days-old',
        type=int,
        default=90,
        help='Archive files older than N days'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode'
    )
    args = parser.parse_args()
    
    archiver = BronzeArchiver()
    count = archiver.archive_files(args.days_old, args.dry_run)
    print(f"Total files: {count}")
