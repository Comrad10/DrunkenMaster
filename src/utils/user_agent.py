import random
from src.config import config

class UserAgentRotator:
    def __init__(self):
        self.user_agents = config.USER_AGENTS
        self.current_index = 0
        
    def get_random(self):
        if not config.ROTATE_USER_AGENTS:
            return self.user_agents[0]
        return random.choice(self.user_agents)
    
    def get_next(self):
        if not config.ROTATE_USER_AGENTS:
            return self.user_agents[0]
        
        user_agent = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return user_agent
    
    def add_user_agent(self, user_agent):
        if user_agent not in self.user_agents:
            self.user_agents.append(user_agent)