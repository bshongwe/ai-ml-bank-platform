"""
Alert Manager
Checks SLI breaches and triggers alerts.
"""
import os
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

SLIS_SLOS_PATH = os.getenv(
    'SLIS_SLOS_PATH', 'monitoring/slis_slos.yaml'
)
METRICS_PATH = os.getenv('METRICS_PATH', 'monitoring/metrics/')
ALERT_WEBHOOK = os.getenv('ALERT_WEBHOOK', '')

class AlertManager:
    def __init__(self):
        self.slos = self.load_slos()
        self.metrics_path = Path(METRICS_PATH)

    def load_slos(self) -> Dict:
        """Load SLO definitions."""
        with open(SLIS_SLOS_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def check_breaches(
        self, metrics: Dict[str, Dict[str, Any]]
    ) -> List[Dict]:
        """Check for SLO breaches."""
        breaches = []
        
        for layer, layer_metrics in metrics.items():
            if layer not in self.slos:
                continue
            
            slo_values = self.slos[layer].get('slo', {})
            
            for metric_name, threshold in slo_values.items():
                if metric_name in layer_metrics:
                    value = layer_metrics[metric_name]
                    
                    # Check if breach (simple comparison)
                    breach = self.is_breach(
                        metric_name, value, threshold
                    )
                    
                    if breach:
                        breaches.append({
                            'layer': layer,
                            'metric': metric_name,
                            'value': value,
                            'threshold': threshold,
                            'timestamp': layer_metrics.get('timestamp'),
                            'severity': self.get_severity(
                                metric_name, value, threshold
                            )
                        })
        
        return breaches

    def is_breach(
        self, metric_name: str, value: float, threshold: float
    ) -> bool:
        """Determine if value breaches threshold."""
        # Metrics where lower is better
        lower_is_better = [
            'event_latency_p99', 'dlq_count', 'data_freshness',
            'schema_drift_count', 'inference_latency_p99',
            'drift_score', 'table_freshness', 'daily_spend',
            'cost_per_prediction'
        ]
        
        if metric_name in lower_is_better:
            return value > threshold
        else:
            return value < threshold

    def get_severity(
        self, metric_name: str, value: float, threshold: float
    ) -> str:
        """Calculate severity of breach."""
        critical_metrics = [
            'delivery_success_rate', 'schema_drift_count',
            'inference_latency_p99'
        ]
        
        if metric_name in critical_metrics:
            return 'critical'
        
        # Calculate % deviation
        if threshold == 0:
            return 'warning'
        
        deviation = abs(value - threshold) / threshold
        
        if deviation > 0.5:
            return 'critical'
        elif deviation > 0.2:
            return 'warning'
        return 'info'

    def send_alert(self, breach: Dict) -> None:
        """Send alert to webhook/PagerDuty."""
        alert_payload = {
            'title': f"SLO Breach: {breach['layer']} - {breach['metric']}",
            'description': (
                f"Value: {breach['value']}, "
                f"Threshold: {breach['threshold']}"
            ),
            'severity': breach['severity'],
            'timestamp': breach['timestamp']
        }
        
        print(f"ALERT: {json.dumps(alert_payload, indent=2)}")
        
        if ALERT_WEBHOOK:
            try:
                import requests
                response = requests.post(
                    ALERT_WEBHOOK,
                    json=alert_payload,
                    timeout=10
                )
                response.raise_for_status()
                print(f"Alert sent to webhook: {response.status_code}")
            except Exception as e:
                print(f"Failed to send alert: {e}")

    def process_alerts(self, metrics: Dict[str, Dict[str, Any]]) -> None:
        """Check breaches and send alerts."""
        breaches = self.check_breaches(metrics)
        
        for breach in breaches:
            self.send_alert(breach)
        
        if not breaches:
            print("No SLO breaches detected.")

if __name__ == '__main__':
    from metrics_collector import MetricsCollector
    
    collector = MetricsCollector()
    metrics = collector.collect_all()
    
    manager = AlertManager()
    manager.process_alerts(metrics)
