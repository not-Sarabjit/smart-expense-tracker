from dataclasses import dataclass


@dataclass
class PromptTemplate:
    system: str
    user: str

    def render(self, context: dict) -> dict:
        """
        Render the template by substituting context values into both
        system and user strings using str.format_map().

        Returns a dict with 'system' and 'user' keys ready to pass to AIClient.
        """
        return {
            "system": self.system.format_map(context),
            "user": self.user.format_map(context),
        }


# ---------------------------------------------------------------------------
# Starter Templates
# ---------------------------------------------------------------------------

CATEGORIZE_TRANSACTION = PromptTemplate(
    system=(
        "You are a financial categorization assistant. "
        "Your job is to assign a transaction to exactly one category "
        "from the list provided. "
        "Respond ONLY with valid JSON in this exact shape:\n"
        '{{"category_name": "<name>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}\n'
        "Do not include any text outside the JSON object."
    ),
    user=(
        "Transaction description: {description}\n"
        "Amount: {amount} {currency}\n\n"
        "Available categories:\n{categories}\n\n"
        "Pick the single best matching category from the list above. "
        "If none fit well, pick the closest one and set confidence below 0.6."
    ),
)


EXTRACT_TRANSACTION = PromptTemplate(
    system=(
        "You are a transaction data extraction assistant. "
        "Extract structured transaction information from the user's free-text input. "
        "Respond ONLY with valid JSON in this exact shape:\n"
        '{{\n'
        '  "amount": <number or null>,\n'
        '  "currency": "<ISO 4217 code or null>",\n'
        '  "description": "<merchant or purpose or null>",\n'
        '  "date": "<YYYY-MM-DD or null>",\n'
        '  "category_hint": "<best guess category or null>",\n'
        '  "transaction_type": "<One of these exact values =  ("income","expense")'
        '  "confidence": <0.0-1.0>\n'
        '}}\n'
        "Do not include any text outside the JSON object. "
        "Use null for fields you cannot determine."
    ),
    user=(
        "Extract transaction details from this text:\n\n"
        "{text}\n\n"
        "Today's date for reference: {today}"
    ),
)


SPENDING_SUMMARY = PromptTemplate(
    system=(
        "You are a personal finance assistant. "
        "Write a clear, friendly, and concise spending summary for the user "
        "based on the structured data provided. "
        "Use plain language. Highlight notable patterns or outliers. "
        "Do NOT invent numbers — use only the data given to you."
    ),
    user=(
        "Here is the spending data for {period}:\n\n"
        "Total income:   {total_income} {currency}\n"
        "Total expenses: {total_expenses} {currency}\n"
        "Net:            {net} {currency}\n\n"
        "Breakdown by category:\n{category_breakdown}\n\n"
        "Top merchants:\n{top_merchants}\n\n"
        "Write a 2-3 sentence summary, then list 1-2 specific observations."
    ),
)