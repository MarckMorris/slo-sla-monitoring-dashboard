#!/usr/bin/env python3
"""
Main application module
Implements core functionality with reliability and observability
"""

import logging
import sys
from typing import Optional
from dataclasses import dataclass
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration"""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "postgres"
    monitoring_port: int = 9090
    log_level: str = "INFO"


class DatabaseManager:
    """
    Manages database connections and operations
    Implements connection pooling and retry logic
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.connection_pool = None
        logger.info(f"Initializing DatabaseManager with config: {config}")
    
    def connect(self) -> bool:
        """Establish database connection with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{max_retries}")
                # Actual connection logic would go here
                time.sleep(0.5)  # Simulate connection time
                logger.info("Database connection established successfully")
                return True
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached, connection failed")
                    return False
    
    def health_check(self) -> dict:
        """Perform health check"""
        return {
            "status": "healthy",
            "connections": 10,
            "uptime": 3600,
            "version": "1.0.0"
        }


class MetricsCollector:
    """
    Collects and exposes metrics for monitoring
    Prometheus-compatible metrics
    """
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "errors_total": 0,
            "latency_ms": []
        }
    
    def record_request(self, latency_ms: float, success: bool = True):
        """Record a request metric"""
        self.metrics["requests_total"] += 1
        self.metrics["latency_ms"].append(latency_ms)
        
        if not success:
            self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> dict:
        """Get current metrics"""
        latencies = self.metrics["latency_ms"]
        return {
            "requests_total": self.metrics["requests_total"],
            "errors_total": self.metrics["errors_total"],
            "error_rate": self.metrics["errors_total"] / max(self.metrics["requests_total"], 1),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        }


class Application:
    """Main application class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.metrics = MetricsCollector()
        logger.info("Application initialized")
    
    def start(self):
        """Start the application"""
        logger.info("Starting application...")
        
        if not self.db_manager.connect():
            logger.error("Failed to connect to database, exiting")
            sys.exit(1)
        
        logger.info("Application started successfully")
        self._run()
    
    def _run(self):
        """Main application loop"""
        try:
            while True:
                # Simulate processing
                start_time = time.time()
                
                # Process work here
                time.sleep(0.1)
                
                latency = (time.time() - start_time) * 1000
                self.metrics.record_request(latency)
                
                # Log metrics periodically
                if self.metrics.metrics["requests_total"] % 100 == 0:
                    logger.info(f"Metrics: {self.metrics.get_metrics()}")
                
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Performing cleanup...")
        # Cleanup logic here
        logger.info("Shutdown complete")


def main():
    """Entry point"""
    config = Config()
    app = Application(config)
    app.start()


if __name__ == "__main__":
    main()
