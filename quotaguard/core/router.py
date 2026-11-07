"""
QuotaGuard Smart Task Classifier, Model Router & Selective Context Engine
========================================================================
Analyzes query intent and complexity, selectively trims non-essential context,
and routes to the optimal model (Flash for fast QA, Pro for deep reasoning,
Qwen Max for code and logic auditing).
"""

import re
from enum import Enum
from typing import List, Dict, Any, Tuple, Optional

class TaskType(str, Enum):
    FAST_QA = "fast_qa"
    REASONING_HEAVY = "reasoning_heavy"
    CODE_AUDIT = "code_audit"

# Default Model Routing Map
MODEL_ROUTING_MAP = {
    TaskType.FAST_QA: "free/deepseek-v4.1-flash",
    TaskType.REASONING_HEAVY: "free/deepseek-v4-pro-0813",
    TaskType.CODE_AUDIT: "free/qwen-3.8-max"
}

class TaskClassifier:
    """Classifies task intent using fast lexical heuristic patterns."""

    CODE_PATTERNS = [
        r"```",
        r"\bdef\s+\w+\s*\(",
        r"\bclass\s+\w+",
        r"\bfunction\b",
        r"\bimport\s+[\w\.]+",
        r"\bfrom\s+[\w\.]+\s+import",
        r"\b(audit|review|debug|bug|traceback|syntax|exception|error|unit\s*test|assert)\b",
        r"\b(csharp|python|javascript|typescript|c\+\+|golang|rust|powershell|sql)\b",
        r"\b(security|vulnerability|injection|bypass|sanitize)\b",
        r"كود|برمجة|ثغرة|تدقيق|تصحيح|فحص|دالة|أمر"
    ]

    REASONING_PATTERNS = [
        r"\b(architecture|design pattern|trade-off|compare|pros and cons|derive|prove)\b",
        r"\b(step[- ]by[- ]step|system design|distributed|consensus|scalability)\b",
        r"\b(mathematical|algorithm|complexity|o\(n\)|dynamic programming)\b",
        r"هندسة|معمارية|خطوة بخطوة|مقارنة|سلبيات|إيجابيات|خوارزمية|استنتاج"
    ]

    @classmethod
    def classify(cls, prompt_or_messages: Any) -> TaskType:
        if isinstance(prompt_or_messages, list):
            text = " ".join(m.get("content", "") for m in prompt_or_messages if isinstance(m, dict))
        elif isinstance(prompt_or_messages, dict):
            text = prompt_or_messages.get("content", "")
        else:
            text = str(prompt_or_messages)

        text_lower = text.lower()

        # Check for Code / Audit intent
        for pat in cls.CODE_PATTERNS:
            if re.search(pat, text_lower, re.IGNORECASE):
                return TaskType.CODE_AUDIT

        # Check for Deep Reasoning intent
        for pat in cls.REASONING_PATTERNS:
            if re.search(pat, text_lower, re.IGNORECASE):
                return TaskType.REASONING_HEAVY

        # Simple factual / Q&A / translation
        return TaskType.FAST_QA

class SelectiveContext:
    """Selective Context Window trimmer: retains only context relevant to the task."""

    @staticmethod
    def filter_context(messages: List[Dict[str, str]], task_type: TaskType, max_turns: int = 6) -> List[Dict[str, str]]:
        if not messages or len(messages) <= 2:
            return messages

        system_msgs = [m for m in messages if m.get("role") == "system"]
        conversation_msgs = [m for m in messages if m.get("role") != "system"]

        if task_type == TaskType.FAST_QA:
            # Fast QA only needs system prompt and last 2 messages
            trimmed = conversation_msgs[-2:] if len(conversation_msgs) >= 2 else conversation_msgs
            return system_msgs + trimmed

        elif task_type == TaskType.CODE_AUDIT:
            # Code Audit: Keep messages containing code blocks or errors, plus recent turns
            relevant = []
            for m in conversation_msgs[:-2]:
                content = m.get("content", "")
                if "```" in content or "def " in content or "class " in content or "error" in content.lower():
                    relevant.append(m)
            relevant.extend(conversation_msgs[-2:])
            return system_msgs + relevant[-max_turns:]

        else: # REASONING_HEAVY
            # Keep up to max_turns of recent conversation history
            return system_msgs + conversation_msgs[-max_turns:]

class SmartRouter:
    """Smart Task Classifier and Model Router with context filtering."""

    def __init__(self, routing_map: Optional[Dict[TaskType, str]] = None):
        self.routing_map = routing_map or MODEL_ROUTING_MAP
        self.classifier = TaskClassifier()
        self.context_filter = SelectiveContext()

    def route(self, prompt_or_messages: Any, requested_model: Optional[str] = None) -> Tuple[str, TaskType]:
        task_type = self.classifier.classify(prompt_or_messages)

        # If user explicitly requested a specific model (other than auto), honor it
        if requested_model and requested_model not in ("auto", "smart", "default", ""):
            return requested_model, task_type

        routed_model = self.routing_map.get(task_type, "free/deepseek-v4-pro-0813")
        return routed_model, task_type

    def prepare_request(self, messages: List[Dict[str, str]], requested_model: Optional[str] = None) -> Tuple[str, List[Dict[str, str]], TaskType]:
        routed_model, task_type = self.route(messages, requested_model)
        optimized_messages = self.context_filter.filter_context(messages, task_type)
        return routed_model, optimized_messages, task_type
