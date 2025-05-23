import logging
import psutil

class ResourceManager:
    """
    Monitors and manages system resources for agent stability.
    """
    def __init__(self, cpu_threshold=90, mem_threshold=90):
        self.logger = logging.getLogger("ResourceManager")
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold

    def check_resources(self):
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        if cpu > self.cpu_threshold:
            self.logger.warning(f"High CPU usage: {cpu}%")
        if mem > self.mem_threshold:
            self.logger.warning(f"High memory usage: {mem}%")
        return cpu, mem

    def enforce_limits(self):
        cpu, mem = self.check_resources()
        # Optionally implement throttling or task rejection here
        return cpu < self.cpu_threshold and mem < self.mem_threshold
