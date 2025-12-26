# Copyright 2024-2025 ELEVAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Post-Deployment Manual Steps Tracker

Centralized system for tracking and displaying all manual configuration steps
required after Pulumi deployment completes.
"""

from typing import List, Dict
import pulumi


class PostDeploymentStep:
    """Represents a single manual step required after deployment."""
    
    def __init__(self, title: str, doc_link: str, details: Dict[str, str] = None):
        """
        Initialize a post-deployment step.
        
        Args:
            title: Short description of the manual step
            doc_link: Link to documentation (e.g., "docs/POST_DEPLOYMENT_STEPS.md#section")
            details: Optional dictionary of key-value details to display
        """
        self.title = title
        self.doc_link = doc_link
        self.details = details or {}


class PostDeploymentTracker:
    """Singleton class to track all required post-deployment manual steps."""
    
    _instance = None
    _steps: List[PostDeploymentStep] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostDeploymentTracker, cls).__new__(cls)
            cls._steps = []
        return cls._instance
    
    def add_step(self, step: PostDeploymentStep):
        """Add a manual step to the tracker."""
        self._steps.append(step)
    
    def has_steps(self) -> bool:
        """Check if any manual steps are required."""
        return len(self._steps) > 0
    
    def print_summary(self):
        """Print consolidated summary of all required manual steps."""
        if not self.has_steps():
            return
        
        # Build the message
        lines = [
            "",
            "=" * 80,
            "POST-DEPLOYMENT MANUAL ACTIONS REQUIRED",
            "=" * 80,
            "",
            f"{len(self._steps)} manual step(s) must be completed in the AWS Console:",
            ""
        ]
        
        # Add each step
        for i, step in enumerate(self._steps, 1):
            lines.append(f"{i}. {step.title}")
            lines.append(f"   → {step.doc_link}")
            
            # Add details if present
            if step.details:
                for key, value in step.details.items():
                    lines.append(f"   {key}: {value}")
            
            lines.append("")  # Blank line between steps
        
        lines.extend([
            "Complete checklist: docs/POST_DEPLOYMENT_STEPS.md",
            "=" * 80,
            ""
        ])
        
        # Print as info
        pulumi.log.info("\n".join(lines))
    
    def clear(self):
        """Clear all tracked steps (useful for testing)."""
        self._steps = []


# Global instance
_tracker = PostDeploymentTracker()


def add_manual_step(title: str, doc_link: str, details: Dict[str, str] = None):
    """
    Add a manual step to the post-deployment tracker.
    
    Args:
        title: Short description of the manual step
        doc_link: Link to documentation
        details: Optional dictionary of key-value details
    """
    step = PostDeploymentStep(title, doc_link, details)
    _tracker.add_step(step)


def print_manual_steps_summary():
    """Print consolidated summary of all required manual steps."""
    _tracker.print_summary()
