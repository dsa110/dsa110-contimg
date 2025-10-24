# GitHub Webhooks Setup Guide

## Overview

GitHub webhooks allow you to receive HTTP POST payloads whenever certain events happen in your repository. This guide explains how to add webhooks to your GitHub repository for the DSA-110 Continuum Imaging Pipeline.

## What are Webhooks?

Webhooks are automated messages sent from GitHub to external services when specific events occur in your repository. Common uses include:
- Triggering CI/CD pipelines
- Sending notifications to chat platforms (Slack, Discord, etc.)
- Automating deployments
- Synchronizing with external tools
- Monitoring repository activity

## Prerequisites

- Repository admin or owner permissions
- A publicly accessible URL endpoint to receive webhook payloads
- (Optional) A secret token for webhook security

## Adding a Webhook to Your Repository

### Step 1: Access Repository Settings

1. Navigate to your GitHub repository: `https://github.com/dsa110/dsa110-contimg`
2. Click on **Settings** tab (requires admin permissions)
3. In the left sidebar, click **Webhooks**
4. Click the **Add webhook** button

### Step 2: Configure Webhook Settings

#### Payload URL
- Enter the URL where GitHub should send webhook payloads
- Example: `https://your-domain.com/webhook`
- Must be publicly accessible via HTTPS (recommended) or HTTP

#### Content Type
Choose the format for webhook payloads:
- **application/json** (recommended): JSON payload in request body
- **application/x-www-form-urlencoded**: JSON payload as form parameter

#### Secret (Optional but Recommended)
- Enter a secret token to validate webhook authenticity
- GitHub will use this to create an HMAC signature in the `X-Hub-Signature-256` header
- Store this securely and use it to verify webhook requests in your application

#### SSL Verification
- **Enable SSL verification** (recommended for production)
- Disable only for testing with self-signed certificates

### Step 3: Select Events

Choose which events should trigger the webhook:

#### Option 1: Just the push event (default)
- Triggers only when code is pushed to the repository

#### Option 2: Send me everything
- Triggers for all repository events
- Results in high webhook volume

#### Option 3: Let me select individual events
Recommended for most use cases. Common events include:

**Code Changes:**
- `push` - Code pushed to any branch
- `pull_request` - Pull request opened, closed, merged, etc.
- `pull_request_review` - Pull request review submitted
- `pull_request_review_comment` - Comment on pull request review

**Issues & Projects:**
- `issues` - Issue opened, edited, closed, etc.
- `issue_comment` - Comment added to issue or pull request
- `project` - Project created, updated, deleted
- `project_card` - Project card created, moved, deleted

**Releases & Deployments:**
- `release` - Release published, updated, deleted
- `deployment` - Deployment created
- `deployment_status` - Deployment status updated

**Repository:**
- `create` - Branch or tag created
- `delete` - Branch or tag deleted
- `star` - Repository starred or unstarred
- `fork` - Repository forked
- `watch` - User watches repository

**Workflow & CI:**
- `workflow_run` - GitHub Actions workflow run completed
- `workflow_job` - GitHub Actions workflow job queued, started, completed
- `check_run` - Check run created, completed, rerequested
- `check_suite` - Check suite requested, completed, rerequested

### Step 4: Activate and Save

1. Check **Active** to enable the webhook immediately
2. Click **Add webhook**
3. GitHub will send a test `ping` event to verify connectivity

## Webhook Payload Structure

### Common Payload Fields

All webhook payloads include:
```json
{
  "action": "opened",
  "repository": {
    "id": 123456789,
    "name": "dsa110-contimg",
    "full_name": "dsa110/dsa110-contimg",
    "owner": {
      "login": "dsa110",
      "type": "Organization"
    },
    "html_url": "https://github.com/dsa110/dsa110-contimg",
    "description": "DSA-110 Continuum Imaging Pipeline"
  },
  "sender": {
    "login": "username",
    "type": "User"
  }
}
```

### Event-Specific Payloads

#### Push Event
```json
{
  "ref": "refs/heads/main",
  "before": "abc123...",
  "after": "def456...",
  "commits": [
    {
      "id": "def456...",
      "message": "Update pipeline configuration",
      "author": {
        "name": "Developer Name",
        "email": "dev@example.com"
      },
      "added": ["config/new_file.yaml"],
      "modified": ["core/pipeline/orchestrator.py"],
      "removed": []
    }
  ]
}
```

#### Pull Request Event
```json
{
  "action": "opened",
  "number": 42,
  "pull_request": {
    "id": 987654321,
    "number": 42,
    "state": "open",
    "title": "Add webhook documentation",
    "body": "This PR adds documentation for GitHub webhooks",
    "user": {
      "login": "contributor"
    },
    "base": {
      "ref": "main",
      "sha": "abc123..."
    },
    "head": {
      "ref": "feature/webhooks",
      "sha": "def456..."
    }
  }
}
```

## Verifying Webhook Signatures

For security, verify webhook signatures using the secret token:

### Python Example
```python
import hmac
import hashlib

def verify_signature(payload_body, signature_header, secret):
    """Verify GitHub webhook signature."""
    hash_object = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

# Usage
payload = request.get_data()
signature = request.headers.get('X-Hub-Signature-256')
if verify_signature(payload, signature, WEBHOOK_SECRET):
    # Process webhook
    pass
else:
    # Reject unauthorized request
    abort(401)
```

### Node.js Example
```javascript
const crypto = require('crypto');

function verifySignature(payload, signature, secret) {
  const hmac = crypto.createHmac('sha256', secret);
  const digest = 'sha256=' + hmac.update(payload).digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(digest)
  );
}
```

## Common Use Cases for DSA-110 Pipeline

### 1. Automated Testing on Push
Trigger automated tests when code is pushed:
- Event: `push`
- Filter: `refs/heads/main` or specific branches
- Action: Run test suite, validation checks

### 2. Deployment on Release
Deploy new versions when releases are published:
- Event: `release`
- Action: `published`
- Trigger: Production deployment pipeline

### 3. Notification Integration
Send notifications to team communication channels:
- Events: `pull_request`, `issues`, `workflow_run`
- Platforms: Slack, Discord, Microsoft Teams
- Content: PR reviews needed, build failures, etc.

### 4. Continuous Integration
Integrate with CI/CD platforms:
- Events: `push`, `pull_request`
- Platforms: Jenkins, GitLab CI, custom pipelines
- Actions: Build, test, deploy

### 5. Documentation Updates
Automatically rebuild documentation:
- Event: `push`
- Filter: Changes to `docs/**` or README files
- Action: Regenerate and deploy documentation

## Managing Webhooks

### View Webhook Deliveries
1. Go to **Settings** → **Webhooks**
2. Click on the webhook URL
3. Click **Recent Deliveries** tab
4. View request/response details, payload, and status codes

### Redeliver a Webhook
1. In Recent Deliveries, find the delivery
2. Click the **...** menu
3. Select **Redeliver**

### Edit or Delete Webhook
1. Go to **Settings** → **Webhooks**
2. Click on the webhook URL
3. Click **Edit** to modify settings
4. Click **Delete webhook** to remove (cannot be undone)

## Troubleshooting

### Webhook Not Triggering
- Verify the webhook is **Active**
- Check that the selected events match your needs
- Review Recent Deliveries for error messages

### Connection Errors
- Ensure payload URL is publicly accessible
- Verify firewall rules allow GitHub's IP ranges
- Check SSL/TLS certificate validity

### Authentication Failures
- Verify secret token matches in both GitHub and your application
- Use `X-Hub-Signature-256` header (not deprecated `X-Hub-Signature`)
- Ensure signature verification algorithm is correct

### Timeout Issues
- Webhook endpoints should respond within 10 seconds
- For long-running tasks, respond immediately and process asynchronously
- Queue webhooks for background processing

## Security Best Practices

1. **Always use HTTPS** for webhook URLs
2. **Validate webhook signatures** using the secret token
3. **Implement rate limiting** to prevent abuse
4. **Log webhook activity** for auditing
5. **Use dedicated service accounts** for webhook authentication
6. **Rotate secrets periodically**
7. **Whitelist GitHub IP ranges** (optional but recommended)
8. **Validate payload structure** before processing
9. **Implement idempotency** to handle duplicate deliveries
10. **Monitor webhook failures** and set up alerts

## GitHub IP Ranges

For additional security, whitelist GitHub's webhook IPs:
```
https://api.github.com/meta
```

This endpoint returns current IP ranges in JSON format:
```json
{
  "hooks": [
    "192.30.252.0/22",
    "185.199.108.0/22",
    "140.82.112.0/20"
  ]
}
```

## Additional Resources

- [GitHub Webhooks Documentation](https://docs.github.com/en/webhooks)
- [Webhook Events and Payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads)
- [Securing Webhooks](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
- [Webhook Best Practices](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks)

## Example: Simple Webhook Server

Here's a minimal Flask server to receive webhooks:

```python
from flask import Flask, request, abort
import hmac
import hashlib
import os

app = Flask(__name__)
WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET')

@app.route('/webhook', methods=['POST'])
def github_webhook():
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature, WEBHOOK_SECRET):
        abort(401, 'Invalid signature')
    
    # Get event type
    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    
    # Process event
    if event == 'push':
        handle_push(payload)
    elif event == 'pull_request':
        handle_pull_request(payload)
    
    return {'status': 'success'}, 200

def verify_signature(payload_body, signature_header, secret):
    if not signature_header or not secret:
        return False
    hash_object = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

def handle_push(payload):
    ref = payload.get('ref')
    commits = payload.get('commits', [])
    print(f"Push to {ref} with {len(commits)} commits")
    # Add your processing logic here

def handle_pull_request(payload):
    action = payload.get('action')
    pr_number = payload['pull_request']['number']
    print(f"Pull request #{pr_number} {action}")
    # Add your processing logic here

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Support

For questions or issues with webhooks in the DSA-110 pipeline:
1. Check this documentation first
2. Review GitHub's webhook documentation
3. Check webhook delivery logs in GitHub settings
4. Contact the pipeline development team
