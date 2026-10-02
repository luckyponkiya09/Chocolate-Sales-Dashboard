from typing import TypedDict, Any

class BusinessState(TypedDict, total=False):
    question: str
    intent: str
    selected_datasets: list
    sales_data: dict
    analysis: dict
    findings: list
    final_report: str