"""
Agent selection logic for determining relevant participants.
"""
import anthropic
from typing import Dict, List

from ..models import Agent


class AgentSelector:
    """Handles intelligent agent selection based on message relevance"""
    
    def __init__(self, client: anthropic.Anthropic, agents: Dict[str, Agent]):
        self.client = client
        self.agents = agents
    
    def detect_relevant_agents(self, message: str) -> List[str]:
        """Detect which agents should be involved based on natural relevance (1-3 agents)"""
        message_lower = message.lower()
        
        # Calculate relevance scores for each agent
        agent_scores = {}
        
        for agent_id, agent in self.agents.items():
            score = 0.0
            
            # Keyword matching with weighted scoring
            trigger_matches = sum(1 for trigger in agent.triggers if trigger in message_lower)
            if trigger_matches > 0:
                score += trigger_matches * 2.0
            
            # Role-based relevance
            role_keywords = {
                'infrastructure': ['deploy', 'server', 'cloud', 'aws', 'scale', 'performance'],
                'devops': ['ci/cd', 'pipeline', 'docker', 'kubernetes', 'build', 'deploy'],
                'backend': ['api', 'database', 'service', 'logic', 'algorithm', 'data'],
                'frontend': ['ui', 'user', 'interface', 'design', 'component', 'react'],
                'security': ['security', 'auth', 'vulnerability', 'hack', 'breach', 'encrypt'],
                'project': ['deadline', 'timeline', 'budget', 'client', 'planning', 'meeting']
            }
            
            for role, keywords in role_keywords.items():
                if role in agent.role.lower():
                    role_matches = sum(1 for kw in keywords if kw in message_lower)
                    score += role_matches * 1.5
            
            # Apply agent-specific weight
            score *= agent.relevance_weight
            
            agent_scores[agent_id] = score
        
        # Sort by relevance
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Natural selection logic
        relevant = []
        
        # Always include the most relevant if score > 0
        if sorted_agents and sorted_agents[0][1] > 0:
            relevant.append(sorted_agents[0][0])
        
        # Add second agent if significantly relevant (score >= 1.0)
        if len(sorted_agents) > 1 and sorted_agents[1][1] >= 1.0:
            relevant.append(sorted_agents[1][0])
        
        # Add third agent only if highly relevant (score >= 2.0)
        if len(sorted_agents) > 2 and sorted_agents[2][1] >= 2.0:
            relevant.append(sorted_agents[2][0])
        
        # Fallback: if no clear relevance, use intelligent selection
        if not relevant:
            agent_descriptions = "\n".join([
                f"- {a.name} ({a.role}): {', '.join(a.triggers[:3])}"
                for a in self.agents.values()
            ])

            prompt = f"""Given this message: "{message}"

            Available specialists:
            {agent_descriptions}

            Who would be MOST relevant? Consider:
            - Primary expertise match
            - Actual value they could provide
            - Whether 1 expert is enough or multiple needed
            
            Return 1-2 names maximum, comma-separated: Rick,Wednesday
            Or just: Rick (if one expert is sufficient)
            """

            try:
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=30,
                    messages=[{"role": "user", "content": prompt}]
                )
                names = response.content[0].text.strip().split(',')
                name_to_id = {a.name: aid for aid, a in self.agents.items()}
                relevant = [name_to_id[name.strip()] for name in names 
                          if name.strip() in name_to_id][:2]  # Max 2 from fallback
            except:
                # Last resort: default to Saul
                relevant = ["saul"]

        return relevant
    
    def should_agent_interject(self, agent_id: str, conversation: str, active_agents: set) -> bool:
        """Determine if an agent should jump into ongoing conversation based on contextual relevance"""
        agent = self.agents[agent_id]

        # Don't interrupt if already active
        if agent_id in active_agents:
            return False

        # Extract last few messages for context analysis
        recent_lines = conversation.split('\n')[-10:]  # Last 10 lines
        recent_context = '\n'.join(recent_lines)
        
        # Check for specific expertise triggers in recent context
        expertise_mentioned = any(
            trigger in recent_context.lower() 
            for trigger in agent.triggers
        )
        
        # Look for questions or problems in agent's domain
        problem_indicators = ['how', 'why', 'what', 'issue', 'problem', 'error', 'help', '?']
        has_relevant_question = (
            expertise_mentioned and 
            any(indicator in recent_context.lower() for indicator in problem_indicators)
        )
        
        # High priority interjection conditions
        if has_relevant_question:
            return True
        
        # Look for contradictions or errors in agent's expertise area
        if expertise_mentioned:
            prompt = f"""Recent conversation:
            {recent_context}

            As {agent.name} ({agent.role}), do you see any technical errors, 
            missed opportunities, or important additions needed in your area of expertise?
            
            Consider only if you have something VALUABLE and SPECIFIC to contribute.
            
            Respond: INTERJECT (with brief reason) or SKIP
            Example: "INTERJECT - security vulnerability overlooked" or "SKIP"
            """

            try:
                response = self.client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=30,
                    system=agent.personality,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                result = response.content[0].text.lower()
                return "interject" in result
                
            except:
                return False
        
        return False