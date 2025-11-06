#!/usr/bin/env python3
"""
Sync TODO.md items to Linear issues.

This script parses TODO.md and creates/updates Linear issues based on the TODO items.
Supports both creating new issues and updating existing ones based on IDs stored in TODO.md.
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: 'requests' library required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
TODO_FILE = PROJECT_ROOT / "TODO.md"
CONFIG_FILE = PROJECT_ROOT / ".linear_config.json"

# Linear API endpoint
LINEAR_API_URL = "https://api.linear.app/graphql"


class LinearClient:
    """Client for Linear GraphQL API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Linear API expects Bearer token format
        self.headers = {
            "Authorization": f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key,
            "Content-Type": "application/json",
        }
    
    def _query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = requests.post(
            LINEAR_API_URL,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        if "errors" in result:
            raise RuntimeError(f"Linear API errors: {result['errors']}")
        
        return result.get("data", {})
    
    def get_team_id(self, team_key: str) -> Optional[str]:
        """Get team ID from team key."""
        query = """
        query GetTeam($filter: TeamFilter) {
          teams(filter: $filter) {
            nodes {
              id
              key
              name
            }
          }
        }
        """
        variables = {
            "filter": {
                "key": {"eq": team_key}
            }
        }
        result = self._query(query, variables)
        teams = result.get("teams", {}).get("nodes", [])
        if teams:
            return teams[0]["id"]
        return None
    
    def create_issue(self, team_id: str, title: str, description: str = "",
                     priority: int = 3, state_id: Optional[str] = None) -> Dict:
        """Create a new Linear issue."""
        query = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              title
              url
            }
          }
        }
        """
        input_data = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority,
        }
        if state_id:
            input_data["stateId"] = state_id
        
        variables = {"input": input_data}
        result = self._query(query, variables)
        
        issue_create = result.get("issueCreate", {})
        if not issue_create.get("success"):
            raise RuntimeError("Failed to create Linear issue")
        
        return issue_create.get("issue", {})
    
    def update_issue(self, issue_id: str, title: Optional[str] = None,
                     description: Optional[str] = None, state_id: Optional[str] = None) -> Dict:
        """Update an existing Linear issue."""
        query = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              identifier
              title
              url
            }
          }
        }
        """
        input_data = {}
        if title is not None:
            input_data["title"] = title
        if description is not None:
            input_data["description"] = description
        if state_id is not None:
            input_data["stateId"] = state_id
        
        variables = {"id": issue_id, "input": input_data}
        result = self._query(query, variables)
        
        issue_update = result.get("issueUpdate", {})
        if not issue_update.get("success"):
            raise RuntimeError("Failed to update Linear issue")
        
        return issue_update.get("issue", {})
    
    def get_issue(self, issue_id: str) -> Optional[Dict]:
        """Get an issue by ID (can use either internal ID or identifier like ENG-123)."""
        query = """
        query GetIssue($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
            description
            state {
              id
              name
            }
          }
        }
        """
        variables = {"id": issue_id}
        result = self._query(query, variables)
        return result.get("issue")
    
    def get_issue_by_identifier(self, identifier: str) -> Optional[Dict]:
        """Get an issue by public identifier (e.g., ENG-123)."""
        query = """
        query GetIssueByIdentifier($identifier: String!) {
          issue(id: $identifier) {
            id
            identifier
            title
            description
            state {
              id
              name
            }
          }
        }
        """
        variables = {"identifier": identifier}
        result = self._query(query, variables)
        return result.get("issue")


class TODOParser:
    """Parse TODO.md and extract items."""
    
    def __init__(self, todo_file: Path):
        self.todo_file = todo_file
        self.content = todo_file.read_text(encoding="utf-8")
    
    def parse_items(self) -> List[Dict]:
        """Parse TODO items from markdown."""
        items = []
        
        # Pattern to match TODO items with optional Linear issue ID
        # Format: - [ ] **Title** (Linear: ISSUE_ID) or - [ ] **Title**
        item_pattern = r'^- \[([ x])\] \*\*(.+?)\*\*(?: \(Linear: ([A-Z]+-\d+)\))?'
        
        current_section = None
        current_priority = None
        
        for line in self.content.split('\n'):
            # Detect priority sections
            if '## 🔴 High Priority' in line:
                current_priority = 0  # Linear priority 0 = Urgent
            elif '## 🟡 Medium Priority' in line:
                current_priority = 1  # Linear priority 1 = High
            elif '## 🟢 Low Priority' in line:
                current_priority = 2  # Linear priority 2 = Medium
            elif '## 📋 Separate Projects' in line:
                current_priority = 3  # Linear priority 3 = Low
            
            # Detect subsections
            if line.startswith('### '):
                current_section = line.replace('### ', '').strip()
            
            # Match TODO items
            match = re.match(item_pattern, line)
            if match:
                checked = match.group(1) == 'x'
                title = match.group(2).strip()
                linear_id = match.group(3) if match.group(3) else None
                
                # Extract time estimate if present
                time_match = re.search(r'\((\d+-\d+ hours?|\d+ minutes?)\)', title)
                time_estimate = time_match.group(1) if time_match else None
                
                # Clean title (remove time estimate from title)
                if time_match:
                    title = title.replace(f"({time_match.group(1)})", "").strip()
                
                items.append({
                    'checked': checked,
                    'title': title,
                    'linear_id': linear_id,
                    'priority': current_priority if current_priority is not None else 3,
                    'section': current_section,
                    'time_estimate': time_estimate,
                    'line': line,
                })
        
        return items
    
    def update_item_with_linear_id(self, title: str, linear_id: str) -> bool:
        """Update TODO.md to add Linear issue ID to an item."""
        # Pattern to match the specific item
        pattern = rf'^(- \[[ x]\] \*\*{re.escape(title)}\*\*)(.*)$'
        
        def replace_line(match):
            prefix = match.group(1)
            suffix = match.group(2)
            # Add Linear ID if not already present
            if f"Linear: {linear_id}" not in suffix:
                if suffix.strip():
                    return f"{prefix} ({suffix.strip()}, Linear: {linear_id})"
                else:
                    return f"{prefix} (Linear: {linear_id})"
            return match.group(0)
        
        new_content = re.sub(pattern, replace_line, self.content, flags=re.MULTILINE)
        
        if new_content != self.content:
            self.todo_file.write_text(new_content, encoding="utf-8")
            return True
        return False


def load_config() -> Dict:
    """Load Linear configuration."""
    if not CONFIG_FILE.exists():
        print(f"Error: Config file not found: {CONFIG_FILE}", file=sys.stderr)
        print("Create .linear_config.json with:", file=sys.stderr)
        print('  {"api_key": "your-api-key", "team_key": "your-team-key"}', file=sys.stderr)
        sys.exit(1)
    
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def sync_to_linear(dry_run: bool = False, only_unchecked: bool = True):
    """Sync TODO.md items to Linear."""
    config = load_config()
    api_key = config.get("api_key")
    team_key = config.get("team_key")
    
    if not api_key or not team_key:
        print("Error: api_key and team_key required in config", file=sys.stderr)
        sys.exit(1)
    
    # Initialize client
    client = LinearClient(api_key)
    team_id = client.get_team_id(team_key)
    
    if not team_id:
        print(f"Error: Team '{team_key}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Parse TODO items
    parser = TODOParser(TODO_FILE)
    items = parser.parse_items()
    
    if only_unchecked:
        items = [item for item in items if not item['checked']]
    
    print(f"Found {len(items)} items to sync")
    
    for item in items:
        title = item['title']
        linear_id = item['linear_id']
        description = f"Section: {item['section']}\n"
        if item['time_estimate']:
            description += f"Time estimate: {item['time_estimate']}\n"
        description += f"\nSource: TODO.md"
        
        if dry_run:
            if linear_id:
                print(f"  [DRY RUN] Would update: {title} (Linear: {linear_id})")
            else:
                print(f"  [DRY RUN] Would create: {title}")
        else:
            if linear_id:
                # Update existing issue
                try:
                    issue = client.update_issue(linear_id, title=title, description=description)
                    print(f"  ✓ Updated: {title} -> {issue.get('identifier', linear_id)}")
                except Exception as e:
                    print(f"  ✗ Failed to update {title}: {e}", file=sys.stderr)
            else:
                # Create new issue
                try:
                    issue = client.create_issue(
                        team_id=team_id,
                        title=title,
                        description=description,
                        priority=item['priority']
                    )
                    linear_id = issue.get('id')
                    identifier = issue.get('identifier', '')
                    
                    # Update TODO.md with Linear ID
                    parser.update_item_with_linear_id(title, identifier)
                    print(f"  ✓ Created: {title} -> {identifier} ({issue.get('url', '')})")
                except Exception as e:
                    print(f"  ✗ Failed to create {title}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Sync TODO.md items to Linear")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Sync all items (including checked ones)"
    )
    
    args = parser.parse_args()
    
    try:
        sync_to_linear(dry_run=args.dry_run, only_unchecked=not args.all)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

