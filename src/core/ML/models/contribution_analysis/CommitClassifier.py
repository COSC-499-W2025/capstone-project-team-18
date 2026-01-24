"""
Classifies commit messages into categories using keyword matching and ML patterns.
"""

import re
from typing import Dict, List, Tuple
from enum import Enum
from collections import Counter


class CommitType(Enum):
    """Types of commits based on their purpose."""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    BUILD = "build"
    CHORE = "chore"
    PERFORMANCE = "performance"
    SECURITY = "security"
    UNKNOWN = "unknown"


class CommitClassifier:
    """
    Classifies commit messages into categories.

    Uses keyword-based classification with support for conventional commit format.
    """

    # Keyword patterns for each commit type
    PATTERNS = {
        CommitType.FEATURE: [
            r'\b(feat|feature|add|implement|new)\b',
            r'\b(create|introduce|initial)\b'
        ],
        CommitType.BUGFIX: [
            r'\b(fix|bug|bugfix|patch|resolve|correct)\b',
            r'\b(issue|error|crash|problem)\b'
        ],
        CommitType.REFACTOR: [
            r'\b(refactor|restructure|reorganize|cleanup|clean up)\b',
            r'\b(improve|optimize|simplify|rewrite)\b'
        ],
        CommitType.DOCUMENTATION: [
            r'\b(doc|docs|documentation|readme|comment)\b',
            r'\b(guide|tutorial|manual)\b'
        ],
        CommitType.TESTING: [
            r'\b(test|tests|testing|spec|specs)\b',
            r'\b(coverage|unittest|integration)\b'
        ],
        CommitType.BUILD: [
            r'\b(build|ci|cd|deploy|release)\b',
            r'\b(package|dependency|dependencies)\b'
        ],
        CommitType.CHORE: [
            r'\b(chore|maintenance|update|upgrade)\b',
            r'\b(version|merge|config)\b'
        ],
        CommitType.PERFORMANCE: [
            r'\b(perf|performance|speed|optimize|optimization)\b',
            r'\b(faster|efficient|cache)\b'
        ],
        CommitType.SECURITY: [
            r'\b(security|secure|vulnerability|cve)\b',
            r'\b(auth|authentication|permission)\b'
        ]
    }

    def classify_commit(self, message: str) -> CommitType:
        """
        Classify a single commit message.

        Args:
            message: The commit message to classify

        Returns:
            CommitType: The classified type
        """
        message_lower = message.lower()

        # Check conventional commit format first (e.g., "feat:", "fix:")
        conventional_match = re.match(r'^(\w+):', message_lower)
        if conventional_match:
            prefix = conventional_match.group(1)
            if prefix in ['feat', 'feature']:
                return CommitType.FEATURE
            elif prefix in ['fix', 'bugfix']:
                return CommitType.BUGFIX
            elif prefix in ['refactor', 'refact']:
                return CommitType.REFACTOR
            elif prefix in ['docs', 'doc']:
                return CommitType.DOCUMENTATION
            elif prefix in ['test', 'tests']:
                return CommitType.TESTING
            elif prefix in ['build', 'ci', 'cd']:
                return CommitType.BUILD
            elif prefix == 'perf':
                return CommitType.PERFORMANCE
            elif prefix in ['security', 'sec']:
                return CommitType.SECURITY
            elif prefix == 'chore':
                return CommitType.CHORE

        # Score each type based on keyword matches
        scores = {}
        for commit_type, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, message_lower, re.IGNORECASE))
                score += matches
            if score > 0:
                scores[commit_type] = score

        # Return the type with highest score, or UNKNOWN if no matches
        if scores:
            return max(scores, key=scores.get)
        return CommitType.UNKNOWN

    def classify_commits(self, messages: List[str]) -> Dict[CommitType, int]:
        """
        Classify multiple commit messages and return distribution.

        Args:
            messages: List of commit messages

        Returns:
            Dictionary mapping CommitType to count
        """
        classifications = [self.classify_commit(msg) for msg in messages]
        return dict(Counter(classifications))

    def get_commit_distribution(self, messages: List[str]) -> Dict[str, float]:
        """
        Get normalized distribution of commit types as percentages.

        Args:
            messages: List of commit messages

        Returns:
            Dictionary mapping commit type name to percentage
        """
        if not messages:
            return {}

        counts = self.classify_commits(messages)
        total = len(messages)

        return {
            commit_type.value: (count / total) * 100
            for commit_type, count in counts.items()
        }