SUMMARIZE_MEMORY_SYSTEM = """Goal: Continuously summarize messages using the delimiter: ------------------------- [New Message Starts Here] ------------------------- Retain key history but prioritize:

    Retention Priority:
        Execution Insights (Success & Issues)
        Interpretation (Objectives, Plans)
        Grades Analysis (Scores only, reasons if critical)

    Message Summary:
        Message Order: [Number]
        Execution:
            Status: Success or fail, with results and lessons.
            Issues: Note errors and patterns.
        Interpretation: Objective, plan, reasoning, operations.
        Grades: Completeness, relevance, specificity.

    Execution Insights:
        Note success (metrics/results) and recurring errors.
        Provide improvement suggestions.

    Key Findings:
        What Worked, Issues Identified, Next Steps.

Maintain History:
    Focus on concise, high-priority data.
    Retain and condense earlier summaries as needed.
    Make sure to retain the details of the last 7 significant message summaries even if it is condensed.
    Also make sure to emphasize the details of the current message.
"""