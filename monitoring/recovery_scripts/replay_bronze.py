"""
Bronze Replay Script
Replay events from Bronze layer for recovery.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

BRONZE_PATH = os.getenv('BRONZE_PATH', 'lake/bronze/')
STREAM_ENDPOINT = os.getenv('STREAM_ENDPOINT', '')

class BronzeReplay:
    def __init__(self):
        self.bronze_path = Path(BRONZE_PATH)

    def list_events(
        self, start_time: str, end_time: str = None
    ) -> List[Dict]:
        """List events in time range."""
        start_dt = datetime.fromisoformat(start_time)
        end_dt = (
            datetime.fromisoformat(end_time)
            if end_time
            else datetime.now(datetime.UTC)
        )
        
        events = []
        for file_path in self.bronze_path.rglob('*.json'):
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if start_dt <= file_time <= end_dt:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        events.append(json.loads(line))
        
        return events

    def replay_events(
        self, start_time: str, end_time: str = None, dry_run: bool = True
    ) -> int:
        """Replay events to stream."""
        events = self.list_events(start_time, end_time)
        
        print(f"Found {len(events)} events to replay")
        
        if dry_run:
            print("Dry run mode - not sending to stream")
            return len(events)
        
        if STREAM_ENDPOINT:
            try:
                import requests
                for event in events:
                    response = requests.post(
                        STREAM_ENDPOINT,
                        json=event,
                        timeout=5
                    )
                    response.raise_for_status()
                print(f"Replayed {len(events)} events")
            except Exception as e:
                print(f"Replay error: {e}")
                return 0
        else:
            print("No STREAM_ENDPOINT configured")
        
        return len(events)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Replay Bronze events')
    parser.add_argument('--start-time', required=True, help='Start time')
    parser.add_argument('--end-time', help='End time')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode'
    )
    args = parser.parse_args()
    
    replay = BronzeReplay()
    count = replay.replay_events(
        args.start_time, args.end_time, args.dry_run
    )
    print(f"Total events: {count}")
