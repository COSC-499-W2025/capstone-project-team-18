"""
Analyzes collaboration dynamics to infer user roles.
"""

from typing import List, Dict, Optional
from enum import Enum
from .CommitClassifier import CommitType


class CollaborationRole(Enum):
    """Roles in a collaborative project."""
    LEADER = "leader"
    CORE_CONTRIBUTOR = "core_contributor"
    CONTRIBUTOR = "contributor"
    REVIEWER = "reviewer"
    OCCASIONAL = "occasional"
    UNKNOWN = "unknown"


class RoleAnalyzer:
    """
    Infers collaboration roles based on commit patterns and project statistics.
    """

    def infer_role(
        self,
        user_commit_percentage: Optional[float],
        total_authors: int,
        commit_distribution: Dict[CommitType, int],
        is_group_project: bool
    ) -> CollaborationRole:
        """
        Infer the user's role in the project.

        Args:
            user_commit_percentage: Percentage of commits by user (0-100)
            total_authors: Total number of authors in project
            commit_distribution: Distribution of commit types
            is_group_project: Whether this is a group project

        Returns:
            CollaborationRole: The inferred role
        """
        if not is_group_project or total_authors <= 1:
            # Solo project
            return CollaborationRole.LEADER

        if user_commit_percentage is None:
            return CollaborationRole.UNKNOWN

        total_commits = sum(commit_distribution.values())

        # Calculate diversity score (how many different types of commits)
        commit_types_used = len([c for c in commit_distribution.values() if c > 0])

        # Role inference logic
        # Leader: high commit percentage, diverse contributions
        if user_commit_percentage >= 40 and commit_types_used >= 3:
            return CollaborationRole.LEADER

        # Core contributor: significant commits, diverse work
        if user_commit_percentage >= 20 and commit_types_used >= 2:
            return CollaborationRole.CORE_CONTRIBUTOR

        # Reviewer: lower commits but presence across codebase
        # (This is a heuristic; we'd need PR data for true reviewer role)
        if 10 <= user_commit_percentage < 20:
            return CollaborationRole.REVIEWER

        # Contributor: moderate involvement
        if 5 <= user_commit_percentage < 20:
            return CollaborationRole.CONTRIBUTOR

        # Occasional: minimal involvement
        if user_commit_percentage < 5:
            return CollaborationRole.OCCASIONAL

        return CollaborationRole.CONTRIBUTOR

    def generate_role_description(
        self,
        role: CollaborationRole,
        commit_distribution: Dict[CommitType, int],
        user_commit_percentage: Optional[float]
    ) -> str:
        """
        Generate a human-readable description of the role.

        Args:
            role: The inferred role
            commit_distribution: Distribution of commit types
            user_commit_percentage: User's commit percentage

        Returns:
            Description string suitable for resume
        """
        total_commits = sum(commit_distribution.values())

        # Find dominant commit types (top 2)
        sorted_types = sorted(
            commit_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_types = [t[0].value for t in sorted_types[:2] if t[1] > 0]

        descriptions = {
            CollaborationRole.LEADER: f"Led project development with {user_commit_percentage:.0f}% of commits, focusing on {', '.join(top_types)}",
            CollaborationRole.CORE_CONTRIBUTOR: f"Core contributor responsible for {user_commit_percentage:.0f}% of commits, primarily {', '.join(top_types)}",
            CollaborationRole.CONTRIBUTOR: f"Contributed {user_commit_percentage:.0f}% of commits, focusing on {', '.join(top_types)}",
            CollaborationRole.REVIEWER: f"Reviewed and contributed {user_commit_percentage:.0f}% of commits across the codebase",
            CollaborationRole.OCCASIONAL: f"Contributed {total_commits} commits to the project",
        }

        return descriptions.get(role, f"Contributed to the project with {total_commits} commits")