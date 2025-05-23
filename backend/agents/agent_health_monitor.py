import logging
import threading
import time

class AgentHealthMonitor:
    """
    Monitors the health of agents (including Selenium/browser) and exposes health status.
    """
    def __init__(self, agents, interval=30):
        self.logger = logging.getLogger("AgentHealthMonitor")
        self.agents = agents  # Dict of agent_name: agent_instance
        self.interval = interval
        self.status = {name: True for name in agents}
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            for name, agent in self.agents.items():
                try:
                    if hasattr(agent, "health_check"):
                        self.status[name] = agent.health_check()
                    else:
                        self.status[name] = True  # Assume healthy if no check
                except Exception as e:
                    self.logger.error(f"Health check failed for {name}: {e}")
                    self.status[name] = False
            time.sleep(self.interval)

    def get_status(self):
        return self.status.copy()

    def stop(self):
        self._stop_event.set()
        self.thread.join()
