from flask import Flask, request
import os
import importlib
import inspect
import json

app = Flask(__name__)

class Manager:
    def __init__(self):
        # Dictionary to hold dynamically loaded agents by filename
        self.agents = {}
        self.load_agents()

    def load_agents(self):
        """
        Dynamically loads all agents in the agents folder using the filename as the key,
        and populates the agents dictionary with the agent instances and their descriptions.
        """
        agents_path = os.path.join(os.path.dirname(__file__), 'agents')
        for filename in os.listdir(agents_path):
            if filename.endswith('.py') and filename != '__init__.py':
                agent_name = filename[:-3]  # Remove the '.py' extension
                module_name = f'agents.{agent_name}'
                module = importlib.import_module(module_name)

                # Find the first class in the module to use as the agent
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ == module_name:
                        agent_instance = obj()
                        description = getattr(agent_instance, "description", "No description provided")
                        self.agents[agent_name] = {
                            "instance": agent_instance,
                            "description": description
                        }
                        break

    def get_agents_list(self):
        """
        Returns a list of all loaded agents with their descriptions.
        """
        return [{"name": name, "description": data["description"]} for name, data in self.agents.items()]

    def get_agent_by_name(self, name):
        """
        Retrieves an agent instance by filename-based name if it exists in the loaded agents.
        """
        return self.agents.get(name, {}).get("instance")


manager = Manager()

# System-prompt definition: instructs the AI to interpret user prompts
def generate_system_prompt():
    agents_list = "\n".join([f"{i+1}. {agent['name']} - {agent['description']}" for i, agent in enumerate(manager.get_agents_list())])
    system_prompt = f"""
You are an assistant capable of analyzing news articles for trustworthiness. 
You will use the following agents to evaluate the article based on different criteria:
{agents_list}

Your task is to:
1. Provide the article to all agents.
2. Collect RAG (Retrieval-Augmented Generation) data from each agent.
3. Combine the RAG data and analyze it to generate a trustworthiness score and detailed explanation.

Always ensure the analysis is comprehensive and includes metadata evaluation, factual consistency, bias detection, and linguistic analysis.
"""
    return system_prompt.strip()

SYSTEM_PROMPT = generate_system_prompt()

@app.route("/infogenai", methods=["POST"])
def process_prompt():
    incoming_msg = request.form.get('Body', '').strip()
    response_text = ""

    if incoming_msg == "list_agents":
        agents_list = manager.get_agents_list()
        response_text = "Available agents:\n" + "\n".join([f"{agent['name']} - {agent['description']}" for agent in agents_list])
        return response_text, 200

    elif incoming_msg == "system_prompt":
        return SYSTEM_PROMPT, 200

    else:
        try:
            # Process the article with all agents
            rag_data = {}
            for agent_name, agent_data in manager.agents.items():
                agent = agent_data["instance"]
                if hasattr(agent, "process_article"):
                    rag_data[agent_name] = agent.process_article(incoming_msg)

            # Combine RAG data and analyze
            combined_rag_data = json.dumps(rag_data)
            response_text = f"Combined RAG Data:\n{combined_rag_data}\n\nAnalysis:\nTrustworthiness analysis will be implemented here."
        except Exception as e:
            response_text = f"Error processing your prompt: {str(e)}"

        return response_text, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)