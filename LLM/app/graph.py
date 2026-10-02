from langgraph.graph import StateGraph, START, END

from app.state import BusinessState
from app.nodes import (
    classify_question,
    retrieve_data,
    calculate_metrics,
    investigate_findings,
    generate_report,
)


def route_by_intent(state: BusinessState) -> str:
    intent = state.get("intent", "general")

    routes = {
        "total_revenue": "revenue",
        "total_orders": "orders",
        "average_order_value": "average_order",
        "top_country": "country",
        "top_product": "product",
        "top_salesperson": "salesperson",
        "salesperson_monthly": "salesperson_monthly",
        "delivery_success": "delivery",
        "general": "general"
    }

    return routes.get(intent, "general")


# Create the graph
workflow = StateGraph(BusinessState)

# Register nodes
workflow.add_node("classify", classify_question)
workflow.add_node("retrieve", retrieve_data)

workflow.add_node("revenue", calculate_metrics)
workflow.add_node("orders", calculate_metrics)
workflow.add_node("average_order", calculate_metrics)
workflow.add_node("country", calculate_metrics)
workflow.add_node("product", calculate_metrics)
workflow.add_node("delivery", calculate_metrics)
workflow.add_node("salesperson_monthly",calculate_metrics)
workflow.add_node("salesperson", calculate_metrics)
workflow.add_node("general", calculate_metrics)

workflow.add_node("investigate", investigate_findings)
workflow.add_node("report", generate_report)

# Define the main flow
workflow.add_edge(START, "classify")
workflow.add_edge("classify", "retrieve")

# Route to the correct calculation node
workflow.add_conditional_edges(
    "retrieve",
    route_by_intent,
    {
        "revenue": "revenue",
        "orders": "orders",
        "average_order": "average_order",
        "country": "country",
        "product": "product",
        "delivery": "delivery",
        "salesperson": "salesperson",
        "salesperson_monthly": "salesperson_monthly",
        "general": "general"
    },
)

# Connect every calculation path to the investigation node
calculation_nodes = [
    "revenue",
    "orders",
    "average_order",
    "country",
    "product",
    "delivery",
    "salesperson",
    "salesperson_monthly",
    "general",
]

for node in calculation_nodes:
    workflow.add_edge(node, "investigate")

# Generate the final report
workflow.add_edge("investigate", "report")
workflow.add_edge("report", END)

# Compile the graph
business_graph = workflow.compile()


def run_investigation(question: str) -> dict:
    """Run the complete business investigation workflow."""

    initial_state = {
        "question": question
    }

    result = business_graph.invoke(initial_state)

    print("FINAL GRAPH KEYS:", result.keys())
    print("FINAL REPORT:", result.get("final_report"))

    return result

if __name__ == "__main__":
    question = input("Ask your business question: ").strip()

    if not question:
        print("Please enter a business question.")
    else:
        try:
            result = run_investigation(question)

            print("\n--- Business Investigation Report ---\n")

            report = result.get("final_report")

            if report and str(report).strip():
                print(report)
            else:
                print("The workflow completed, but no report was returned.")

                print("\n--- Debug Information ---")
                print("Intent:", result.get("intent"))
                print("Analysis:", result.get("analysis"))
                print("Findings:", result.get("findings"))

        except Exception as error:
            print("\nAn error occurred while running the investigation.")
            print(f"Error: {error}")
            raise