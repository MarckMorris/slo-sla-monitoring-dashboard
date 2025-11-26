#!/usr/bin/env python3
"""
SLO/SLA Monitoring Dashboard
Tracks service level objectives with error budgets
"""

import psycopg2
import time
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SLOMonitor:
    
    def __init__(self):
        self.conn = None
        self.slos = {}
        
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host='localhost',
                port=5450,
                dbname='slo_db',
                user='postgres',
                password='postgres'
            )
            self.conn.autocommit = True
            logger.info("Connected to database")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def setup(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slo_definitions (
                slo_id VARCHAR(50) PRIMARY KEY,
                service_name VARCHAR(100),
                slo_type VARCHAR(50),
                target_percentage DECIMAL(5,2),
                measurement_window_hours INT,
                description TEXT
            );
            
            CREATE TABLE IF NOT EXISTS slo_measurements (
                measurement_id SERIAL PRIMARY KEY,
                slo_id VARCHAR(50) REFERENCES slo_definitions(slo_id),
                timestamp TIMESTAMP DEFAULT NOW(),
                success_count INT,
                total_count INT,
                current_slo DECIMAL(5,2),
                error_budget_remaining DECIMAL(10,2)
            );
            
            CREATE TABLE IF NOT EXISTS slo_alerts (
                alert_id SERIAL PRIMARY KEY,
                slo_id VARCHAR(50),
                triggered_at TIMESTAMP DEFAULT NOW(),
                severity VARCHAR(20),
                message TEXT,
                burn_rate DECIMAL(10,2)
            );
        """)
        cursor.close()
        logger.info("SLO tables initialized")
    
    def define_slos(self):
        """Define SLOs for different services"""
        cursor = self.conn.cursor()
        
        slos = [
            {
                'slo_id': 'db-availability',
                'service_name': 'database',
                'slo_type': 'availability',
                'target': 99.9,
                'window': 720,  # 30 days
                'description': 'Database must be available 99.9% of time'
            },
            {
                'slo_id': 'query-latency',
                'service_name': 'database',
                'slo_type': 'latency',
                'target': 95.0,
                'window': 168,  # 7 days
                'description': '95% of queries must complete in < 100ms'
            },
            {
                'slo_id': 'api-success-rate',
                'service_name': 'api',
                'slo_type': 'success_rate',
                'target': 99.5,
                'window': 168,
                'description': '99.5% of API requests must succeed'
            }
        ]
        
        for slo in slos:
            cursor.execute("""
                INSERT INTO slo_definitions 
                (slo_id, service_name, slo_type, target_percentage, 
                 measurement_window_hours, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (slo_id) DO NOTHING
            """, (slo['slo_id'], slo['service_name'], slo['slo_type'],
                  slo['target'], slo['window'], slo['description']))
            
            self.slos[slo['slo_id']] = slo
        
        cursor.close()
        logger.info(f"Defined {len(slos)} SLOs")
    
    def simulate_measurements(self, slo_id: str, success_rate: float):
        """Simulate measurements for an SLO"""
        
        total = 1000
        successes = int(total * (success_rate / 100))
        
        cursor = self.conn.cursor()
        
        # Get SLO target
        cursor.execute("""
            SELECT target_percentage, measurement_window_hours
            FROM slo_definitions
            WHERE slo_id = %s
        """, (slo_id,))
        
        target, window = cursor.fetchone()
        
        # Calculate current SLO
        current_slo = (successes / total) * 100
        
        # Calculate error budget
        allowed_errors = total * (1 - target / 100)
        actual_errors = total - successes
        error_budget_remaining = ((allowed_errors - actual_errors) / allowed_errors) * 100
        
        # Record measurement
        cursor.execute("""
            INSERT INTO slo_measurements
            (slo_id, success_count, total_count, current_slo, error_budget_remaining)
            VALUES (%s, %s, %s, %s, %s)
        """, (slo_id, successes, total, current_slo, error_budget_remaining))
        
        cursor.close()
        
        return {
            'slo_id': slo_id,
            'current_slo': current_slo,
            'target': target,
            'error_budget': error_budget_remaining,
            'success_count': successes,
            'total_count': total
        }
    
    def calculate_burn_rate(self, slo_id: str) -> float:
        """Calculate error budget burn rate"""
        
        cursor = self.conn.cursor()
        
        # Get measurements from last hour
        cursor.execute("""
            SELECT error_budget_remaining
            FROM slo_measurements
            WHERE slo_id = %s
            AND timestamp > NOW() - INTERVAL '1 hour'
            ORDER BY timestamp
        """, (slo_id,))
        
        measurements = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        if len(measurements) < 2:
            return 0.0
        
        # Calculate burn rate (how fast we're consuming error budget)
        budget_change = measurements[0] - measurements[-1]
        burn_rate = budget_change / len(measurements)
        
        return burn_rate
    
    def check_slo_alerts(self, measurement: dict):
        """Check if SLO violation alerts should be triggered"""
        
        slo_id = measurement['slo_id']
        current = measurement['current_slo']
        target = measurement['target']
        error_budget = measurement['error_budget']
        
        cursor = self.conn.cursor()
        
        # Alert 1: SLO below target
        if current < target:
            cursor.execute("""
                INSERT INTO slo_alerts (slo_id, severity, message, burn_rate)
                VALUES (%s, %s, %s, %s)
            """, (slo_id, 'high', 
                  f'SLO below target: {current:.2f}% < {target:.2f}%', 0))
            logger.warning(f"ALERT: {slo_id} SLO violation")
        
        # Alert 2: Error budget low
        if error_budget < 20:
            severity = 'critical' if error_budget < 10 else 'high'
            cursor.execute("""
                INSERT INTO slo_alerts (slo_id, severity, message, burn_rate)
                VALUES (%s, %s, %s, %s)
            """, (slo_id, severity,
                  f'Error budget low: {error_budget:.1f}% remaining', 0))
            logger.warning(f"ALERT: {slo_id} error budget low")
        
        # Alert 3: High burn rate
        burn_rate = self.calculate_burn_rate(slo_id)
        if burn_rate > 5:
            cursor.execute("""
                INSERT INTO slo_alerts (slo_id, severity, message, burn_rate)
                VALUES (%s, %s, %s, %s)
            """, (slo_id, 'critical',
                  f'High error budget burn rate: {burn_rate:.2f}%/hr', burn_rate))
            logger.warning(f"ALERT: {slo_id} high burn rate")
        
        cursor.close()
    
    def print_slo_dashboard(self):
        """Print SLO dashboard"""
        
        cursor = self.conn.cursor()
        
        print("\n" + "=" * 80)
        print(f"SLO/SLA MONITORING DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        for slo_id in self.slos.keys():
            # Get latest measurement
            cursor.execute("""
                SELECT current_slo, error_budget_remaining, 
                       success_count, total_count, timestamp
                FROM slo_measurements
                WHERE slo_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (slo_id,))
            
            result = cursor.fetchone()
            
            if not result:
                continue
            
            current_slo, error_budget, success, total, ts = result
            slo_def = self.slos[slo_id]
            target = slo_def['target']
            
            # Status indicator
            if current_slo >= target and error_budget > 50:
                status = "HEALTHY"
                symbol = "✓"
            elif current_slo >= target and error_budget > 20:
                status = "WARNING"
                symbol = "⚠"
            else:
                status = "CRITICAL"
                symbol = "✗"
            
            print(f"\n{symbol} {slo_def['service_name'].upper()} - {slo_def['slo_type'].upper()}")
            print(f"  Description: {slo_def['description']}")
            print(f"  Status: {status}")
            print(f"  Current SLO: {current_slo:.3f}% (Target: {target}%)")
            print(f"  Error Budget: {error_budget:.1f}% remaining")
            print(f"  Success Rate: {success}/{total} ({(success/total*100):.2f}%)")
            print(f"  Last Updated: {ts}")
        
        # Recent alerts
        cursor.execute("""
            SELECT slo_id, severity, message, triggered_at
            FROM slo_alerts
            WHERE triggered_at > NOW() - INTERVAL '1 hour'
            ORDER BY triggered_at DESC
            LIMIT 5
        """)
        
        alerts = cursor.fetchall()
        
        if alerts:
            print("\n" + "=" * 80)
            print("RECENT ALERTS (Last Hour)")
            print("=" * 80)
            
            for alert in alerts:
                slo_id, severity, message, triggered = alert
                print(f"\n  [{severity.upper()}] {slo_id}")
                print(f"  {message}")
                print(f"  Time: {triggered}")
        
        cursor.close()
        print("=" * 80)
    
    def print_summary_report(self):
        """Print summary report"""
        
        cursor = self.conn.cursor()
        
        print("\n" + "=" * 80)
        print("SLO COMPLIANCE SUMMARY")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                d.slo_id,
                d.service_name,
                d.target_percentage,
                AVG(m.current_slo) as avg_slo,
                AVG(m.error_budget_remaining) as avg_budget,
                COUNT(*) as measurement_count
            FROM slo_definitions d
            JOIN slo_measurements m ON d.slo_id = m.slo_id
            GROUP BY d.slo_id, d.service_name, d.target_percentage
        """)
        
        for row in cursor.fetchall():
            slo_id, service, target, avg_slo, avg_budget, count = row
            
            compliance = "COMPLIANT" if avg_slo >= target else "NON-COMPLIANT"
            
            print(f"\n{slo_id}:")
            print(f"  Service: {service}")
            print(f"  Target: {target}%")
            print(f"  Average SLO: {avg_slo:.3f}%")
            print(f"  Average Budget: {avg_budget:.1f}%")
            print(f"  Compliance: {compliance}")
            print(f"  Measurements: {count}")
        
        # Total alerts
        cursor.execute("SELECT COUNT(*) FROM slo_alerts")
        total_alerts = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT severity, COUNT(*) 
            FROM slo_alerts 
            GROUP BY severity
        """)
        
        print(f"\n" + "=" * 80)
        print(f"Total Alerts: {total_alerts}")
        
        for row in cursor.fetchall():
            severity, count = row
            print(f"  {severity.upper()}: {count}")
        
        cursor.close()
        print("=" * 80)
    
    def run_monitoring(self, duration: int = 30):
        """Run SLO monitoring"""
        
        print("\n" + "=" * 80)
        print("SLO/SLA MONITORING DASHBOARD")
        print("=" * 80)
        
        if not self.connect():
            return
        
        self.setup()
        self.define_slos()
        
        logger.info(f"Starting SLO monitoring for {duration} seconds...")
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < duration:
            iteration += 1
            
            # Simulate measurements with varying success rates
            # Database availability - usually high
            measurement = self.simulate_measurements('db-availability', random.uniform(99.85, 99.95))
            self.check_slo_alerts(measurement)
            
            # Query latency - sometimes degrades
            latency_rate = random.uniform(93, 97) if iteration % 5 != 0 else random.uniform(88, 92)
            measurement = self.simulate_measurements('query-latency', latency_rate)
            self.check_slo_alerts(measurement)
            
            # API success rate - generally good
            api_rate = random.uniform(99.3, 99.7)
            measurement = self.simulate_measurements('api-success-rate', api_rate)
            self.check_slo_alerts(measurement)
            
            # Print dashboard every 10 seconds
            if iteration % 2 == 0:
                self.print_slo_dashboard()
            
            time.sleep(5)
        
        # Final report
        self.print_summary_report()
        
        print("\n" + "=" * 80)
        print("Key Features:")
        print("  - Real-time SLO tracking")
        print("  - Error budget monitoring")
        print("  - Burn rate alerting")
        print("  - Compliance reporting")
        print("=" * 80)


def main():
    monitor = SLOMonitor()
    monitor.run_monitoring(duration=30)


if __name__ == "__main__":
    main()
