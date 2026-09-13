import os
from typing import TypedDict, List

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from google import genai

from rag import search_knowledge

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


class AgentState(TypedDict):
    user_request: str
    employee: dict
    policy: str
    plan: List[str]
    response: str


def understand_request(state: AgentState):
    print("\n[1] Understanding request...")

    return state


def find_employee(state: AgentState):
    print("[2] Finding employee...")

    import requests

    response = requests.get(
        "http://127.0.0.1:8000/api/employees"
    )

    employees = response.json()

    request = state["user_request"].lower()

    employee = None

    for candidate in employees:
        name = candidate["name"].lower()

        if name in request:
            employee = candidate
            break

    if not employee:
        raise ValueError("Could not identify employee from request.")

    print(
        f"    Found: {employee['name']} "
        f"({employee['department']} - {employee['role']})"
    )

    state["employee"] = employee

    return state


def retrieve_policy(state: AgentState):
    print("[3] Retrieving enterprise policy...")

    employee = state["employee"]

    query = (
        f"What applications and access policies apply to a "
        f"{employee['role']} in {employee['department']}?"
    )

    results = search_knowledge(query, top_k=2)

    documents = results["documents"][0]

    policy = "\n\n".join(documents)

    state["policy"] = policy

    print("    Policy context retrieved.")

    return state


def create_plan(state: AgentState):
    print("[4] Creating execution plan...")

    employee = state["employee"]
    policy = state["policy"]
    request = state["user_request"]

    prompt = f"""
You are an enterprise IT operations planning agent.

User request:
{request}

Employee:
{employee}

Enterprise policy:
{policy}

Create a safe execution plan.

Rules:
- Follow enterprise policy.
- Do not grant privileged access without approval.
- Do not invent applications.
- Keep the plan concise.
- Return only a numbered list of actions.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    plan = [
        line.strip()
        for line in response.text.splitlines()
        if line.strip()
    ]

    state["plan"] = plan

    print("\n    Plan:")
    for step in plan:
        print(f"    {step}")

    return state


def final_response(state: AgentState):
    employee = state["employee"]

    state["response"] = (
        f"OpsPilot identified {employee['name']} "
        f"as a {employee['role']} in {employee['department']}.\n\n"
        "Execution plan:\n"
        + "\n".join(state["plan"])
    )

    return state


graph = StateGraph(AgentState)

graph.add_node("understand_request", understand_request)
graph.add_node("find_employee", find_employee)
graph.add_node("retrieve_policy", retrieve_policy)
graph.add_node("create_plan", create_plan)
graph.add_node("final_response", final_response)

graph.add_edge(START, "understand_request")
graph.add_edge("understand_request", "find_employee")
graph.add_edge("find_employee", "retrieve_policy")
graph.add_edge("retrieve_policy", "create_plan")
graph.add_edge("create_plan", "final_response")
graph.add_edge("final_response", END)

agent = graph.compile()


if __name__ == "__main__":

    request = (
        "Onboard Sarah Thomas as a Sales employee. "
        "Give her the applications required for her role "
        "and create her IT ticket."
    )

    result = agent.invoke({
        "user_request": request,
        "employee": {},
        "policy": "",
        "plan": [],
        "response": ""
    })

    print("\n" + "=" * 60)
    print("FINAL RESPONSE")
    print("=" * 60)

    print(result["response"])