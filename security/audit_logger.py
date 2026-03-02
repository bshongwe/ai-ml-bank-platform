"""
Audit Logger
Centralized audit logging across all clouds.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

AUDIT_LOG_PATH = os.getenv('AUDIT_LOG_PATH', 'security/audit_logs/')

class AuditLogger:
    def __init__(self):
        self.log_path = Path(AUDIT_LOG_PATH)
        self.log_path.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        action: str,
        resource: str,
        user: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Log audit event."""
        event = {
            'timestamp': datetime.now(datetime.UTC).isoformat(),
            'action': action,
            'resource': resource,
            'user': user,
            'metadata': metadata or {}
        }
        
        # Write to daily log file
        log_file = self.log_path / f"audit_{
            datetime.now(datetime.UTC).strftime('%Y%m%d')
        }.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + '\n')

    def query_logs(
        self,
        action: str = None,
        resource: str = None,
        user: str = None,
        start_date: str = None
    ) -> List[Dict]:
        """Query audit logs."""
        results = []
        
        # Search through log files
        log_files = sorted(self.log_path.glob('audit_*.jsonl'))
        
        for log_file in log_files:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    event = json.loads(line)
                    
                    # Apply filters
                    if action and event.get('action') != action:
                        continue
                    if resource and event.get('resource') != resource:
                        continue
                    if user and event.get('user') != user:
                        continue
                    if start_date and event.get('timestamp') < start_date:
                        continue
                    
                    results.append(event)
        
        return results

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Query audit logs')
    parser.add_argument('--action', help='Filter by action')
    parser.add_argument('--resource', help='Filter by resource')
    parser.add_argument('--user', help='Filter by user')
    parser.add_argument('--start-date', help='Filter by start date')
    args = parser.parse_args()
    
    logger = AuditLogger()
    results = logger.query_logs(
        action=args.action,
        resource=args.resource,
        user=args.user,
        start_date=args.start_date
    )
    
    print(json.dumps(results, indent=2))
