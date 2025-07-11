"""
Grounding loader utilities for loading examples from files or requests.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from doorbeen.core.assistants.grounding.models import AnalysisExample


def load_examples_from_file(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load examples from JSON file."""
    
    if file_path is None:
        # Default to examples.json in the same directory
        current_dir = Path(__file__).parent
        file_path = current_dir / "examples.json"
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                examples_data = json.load(f)
                return examples_data if isinstance(examples_data, list) else []
        else:
            return []
    except Exception:
        return []


def load_examples_from_request(request_examples: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Load examples from request, with validation."""
    
    if not request_examples:
        return []
    
    validated_examples = []
    for example in request_examples:
        if isinstance(example, dict) and "question" in example:
            # Ensure required fields with defaults
            validated_example = {
                "question": example.get("question", ""),
                "instructions": example.get("instructions", ""),
                "expected_output": example.get("expected_output", ""),
                "tags": example.get("tags", []),
                "priority": example.get("priority", 1)
            }
            validated_examples.append(validated_example)
    
    return validated_examples


def merge_examples(file_examples: List[Dict[str, Any]], request_examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge file examples with request examples, prioritizing request examples."""
    
    # Start with file examples
    merged = file_examples.copy()
    
    # Add request examples (they take priority)
    merged.extend(request_examples)
    
    # Sort by priority (higher priority first)
    merged.sort(key=lambda x: x.get("priority", 1), reverse=True)
    
    return merged


def prepare_examples_for_state(request_examples: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Prepare examples for state initialization."""
    
    # Load from file
    file_examples = load_examples_from_file()
    
    # Load from request
    request_examples = load_examples_from_request(request_examples)
    
    # Merge and return
    return merge_examples(file_examples, request_examples) 