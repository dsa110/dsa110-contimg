# MCP Server Tools Reference

This document lists all available Model Context Protocol (MCP) server tools
configured for this project.

## Overview

MCP servers provide specialized tools and capabilities that can be accessed
through Cursor. Each server offers a set of tools for specific tasks.

## Quick Reference: All MCP Servers

| #   | Server                       | Purpose                            | Config Location |
| --- | ---------------------------- | ---------------------------------- | --------------- |
| 1   | **Codacy**                   | Code quality & security analysis   | User-level      |
| 2   | **Figma**                    | Design system & UI code generation | User-level      |
| 3   | **Perplexity** (2 instances) | Research & web search              | Project-level   |
| 4   | **Cursor IDE Browser**       | Browser automation & web testing   | Built-in        |
| 5   | **Chrome DevTools**          | DevTools Protocol integration      | Project-level   |
| 6   | **ArXiv**                    | Research paper access              | Project-level   |
| 7   | **Ref**                      | Code reference & documentation     | Project-level   |
| 8   | **Context7**                 | Context management                 | Project-level   |
| 9   | **Graphiti Memory**          | Knowledge graph & agent memory     | Project-level   |
| 10  | **Desktop Commander**        | Desktop automation                 | Project-level   |
| 11  | **Mermaid**                  | Diagram generation                 | Project-level   |
| 12  | **Pexpect**                  | Interactive terminal automation    | Project-level   |
| 13  | **My Graphiti**              | Custom knowledge graph instance    | Project-level   |
| 14  | **Playwright**               | Browser automation & E2E testing   | User-level      |

**Total: 14 MCP servers configured**

## Configured MCP Servers

### 1. Codacy MCP

**Purpose:** Code quality and security analysis

**Tools:**

- `codacy_get_pattern` - Get definition of a specific pattern
- `codacy_list_tools` - List all code analysis tools available
- `codacy_cli_analyze` - Run quality analysis locally using Codacy CLI

**Configuration:** User-level (`~/.cursor/mcp.json`)

- Uses `npx -y @codacy/codacy-mcp@latest`

**Use Cases:**

- Analyzing code quality
- Finding security issues
- Understanding Codacy pattern definitions

**Examples:**

```python
# List available analysis tools
codacy_list_tools()

# Get pattern definition for a specific issue
codacy_get_pattern(toolUuid="eslint", patternId="no-console")

# Analyze codebase for quality issues
codacy_cli_analyze(rootPath="/data/dsa110-contimg", file="src/pipeline/")
```

---

### 2. Figma MCP

**Purpose:** Design system integration and UI code generation

**Tools:**

- `Figma_get_screenshot` - Generate screenshot for a node or selected node
- `Figma_create_design_system_rules` - Generate design system rules prompt
- `Figma_get_design_context` - Generate UI code for a given node
- `Figma_get_metadata` - Get metadata for a node or page (XML format)
- `Figma_get_variable_defs` - Get variable definitions for a node
- `Figma_get_figjam` - Generate UI code for FigJam nodes
- `Figma_get_code_connect_map` - Get Code Connect mapping (nodeId to codebase
  location)
- `Figma_whoami` - Get authenticated user information

**Configuration:** User-level (`~/.cursor/mcp.json`)

- HTTP endpoint: `https://mcp.figma.com/mcp`

**Use Cases:**

- Converting Figma designs to code
- Extracting design tokens and variables
- Generating UI components from designs
- Accessing design system information

**Examples:**

```python
# Get design context for a Figma node (generates React/TypeScript code)
Figma_get_design_context(
    fileKey="abc123",
    nodeId="1:234",
    clientLanguages="typescript,html,css",
    clientFrameworks="react"
)

# Get variable definitions (colors, spacing, etc.)
Figma_get_variable_defs(fileKey="abc123", nodeId="1:234")

# Get screenshot of a design
Figma_get_screenshot(fileKey="abc123", nodeId="1:234")

# Get Code Connect mapping (links Figma to codebase)
Figma_get_code_connect_map(fileKey="abc123", nodeId="1:234")
```

---

### 3. Perplexity MCP (Multiple Instances)

#### Perplexity Ask

**Purpose:** Conversational AI with Sonar API

**Tools:**

- `perplexity_ask` - Engage in conversation using Sonar API
- `perplexity_research` - Perform deep research with citations
- `perplexity_reason` - Perform reasoning tasks using sonar-reasoning-pro model

**Configuration:** Project-level (`.cursor/mcp.json`)

- Docker-based: `mcp/perplexity-ask`
- API Key configured

#### Perplexity Server

**Purpose:** Web search and research with advanced filtering

**Tools:**

- `perplexity-server_search` - Web search via Perplexity AI with automatic model
  selection
- `perplexity-server_domain_filter` - Configure domain filtering (allow/block)
- `perplexity-server_recency_filter` - Control time window for search results
- `perplexity-server_clear_filters` - Remove all domain filters
- `perplexity-server_list_filters` - Display current filter configuration
- `perplexity-server_model_info` - View available models and override selection

**Configuration:** Project-level (`.cursor/mcp.json`)

- Node.js server: `/home/ubuntu/proj/mcps/perplexity-mcp/build/index.js`
- Model: `sonar` (default)

**Use Cases:**

- Research and fact-checking
- Current events and news
- Technical documentation lookup
- Comparative analysis

**Examples:**

```python
# Search for current information
perplexity-server_search(query="React 19 new features 2025")

# Research with citations
perplexity_research(messages=[{
    "role": "user",
    "content": "What are the latest developments in radio astronomy imaging?"
}])

# Reasoning tasks
perplexity_reason(messages=[{
    "role": "user",
    "content": "Compare X11 forwarding vs VNC for remote GUI access"
}])

# Filter by domain (e.g., only docs.python.org)
perplexity-server_domain_filter(domain="docs.python.org", action="allow")

# Filter by recency (last week)
perplexity-server_recency_filter(filter="week")
```

---

### 4. Cursor IDE Browser

**Purpose:** Browser automation and web testing

**Tools:**

- `browser_navigate` - Navigate to a URL
- `browser_snapshot` - Capture accessibility snapshot (better than screenshot)
- `browser_click` - Perform click on web page
- `browser_type` - Type text into editable element
- `browser_hover` - Hover over element
- `browser_select_option` - Select option in dropdown
- `browser_press_key` - Press keyboard key
- `browser_wait_for` - Wait for text to appear/disappear or time to pass
- `browser_navigate_back` - Go back to previous page
- `browser_resize` - Resize browser window
- `browser_console_messages` - Get all console messages
- `browser_network_requests` - Get all network requests
- `browser_take_screenshot` - Take screenshot of current page

**Configuration:** Built-in to Cursor

- Uses native Chrome on Mac (when X11 forwarding is disabled)
- See [Remote Access Tools Guide](../env.md) for setup

**Use Cases:**

- E2E testing
- Web scraping
- UI automation
- Debugging web applications

**Examples:**

```python
# Navigate to a page
browser_navigate(url="http://localhost:5173/dashboard")

# Take accessibility snapshot (better than screenshot for automation)
browser_snapshot()

# Click a button
browser_click(element="Submit button", ref="button[type='submit']")

# Type into a form field
browser_type(element="Search input", ref="input[name='search']", text="test query")

# Wait for content to appear
browser_wait_for(text="Loading complete")

# Get console messages
browser_console_messages()

# Get network requests
browser_network_requests()

# Take screenshot
browser_take_screenshot(filename="dashboard.png", fullPage=True)
```

---

### 5. Chrome DevTools MCP

**Purpose:** Chrome DevTools Protocol integration

**Configuration:** Project-level (`.cursor/mcp.json`)

- Docker-based: `node:22-alpine` with Chromium
- Uses Chrome DevTools Protocol
- Runs headless: `--headless --executablePath=/usr/bin/chromium`

**Use Cases:**

- Browser debugging via DevTools Protocol
- Performance profiling
- Network inspection
- Console access

**Note:** This server runs in Docker and may require X11 forwarding for display.
For most browser automation tasks, use Cursor Browser Tool or Playwright
instead.

---

### 6. ArXiv MCP Server

**Purpose:** Access to arXiv research papers

**Configuration:** Project-level (`.cursor/mcp.json`)

- Docker-based: `mcp/arxiv-mcp-server`
- Storage mounted: `/home/ubuntu/proj/mcps/arxiv-md-mcp:/storage`

**Use Cases:**

- Searching arXiv papers
- Accessing research documentation
- Literature review
- Converting LaTeX papers to Markdown

**Examples:**

```python
# Search for papers (typical tools available)
# - search_papers: Search arXiv by keyword, author, category
# - get_paper: Retrieve full paper content
# - convert_to_markdown: Convert LaTeX to Markdown

# Example workflow:
# 1. Search for papers on "radio astronomy imaging"
# 2. Get full paper content
# 3. Convert to Markdown for easier reading
```

---

### 7. Ref MCP

**Purpose:** Code reference and documentation

**Configuration:** Project-level (`.cursor/mcp.json`)

- HTTP endpoint: `https://api.ref.tools/mcp`
- API Key configured

**Use Cases:**

- Code reference lookup
- Documentation access
- Finding code examples
- API documentation search

**Examples:**

```python
# Typical Ref MCP tools:
# - search_code: Search code repositories
# - get_reference: Get code reference documentation
# - find_examples: Find code examples for a function/class
```

---

### 8. Context7 MCP

**Purpose:** Context management and information retrieval

**Configuration:** Project-level (`.cursor/mcp.json`)

- HTTP endpoint: `https://mcp.context7.com/mcp`
- API Key configured

**Use Cases:**

- Context management
- Information retrieval
- Knowledge base access
- Context-aware responses

**Examples:**

```python
# Typical Context7 tools:
# - store_context: Store context for later retrieval
# - retrieve_context: Retrieve stored context
# - search_context: Search through stored contexts
```

---

### 9. Graphiti Memory MCP

**Purpose:** Knowledge graph and agent memory management

**Configuration:** Project-level (`.cursor/mcp.json`)

- Python-based: `/home/ubuntu/proj/mcps/graphiti/mcp_server/main.py`
- Neo4j backend (bolt://localhost:7687)
- Group ID: `dsa110-contimg`
- Uses Gemini embeddings (Vertex AI)

**Use Cases:**

- Storing project knowledge
- Agent memory management
- Entity extraction and relationships
- Long-term context management

**Examples:**

```python
# Search for existing knowledge
search_nodes(query="calibration procedures", entity="Procedure")

# Add new knowledge
add_episode(
    episode_body="The pipeline uses casa6 Python environment for all CASA operations",
    source_type="text"
)

# Search for facts/relationships
search_facts(query="pipeline dependencies", max_facts=10)

# Add explicit facts
add_triplet(
    subject="Pipeline",
    predicate="DEPENDS_ON",
    object="casa6"
)
```

**Related Documentation:**

- See `.cursor/rules/graphiti/` for Graphiti-specific rules
- Project schema: `.cursor/rules/graphiti/graphiti-dsa110-contimg-schema.mdc`

---

### 10. Desktop Commander

**Purpose:** Desktop automation and system control

**Configuration:** Project-level (`.cursor/mcp.json`)

- Uses `npx -y @wonderwhy-er/desktop-commander@latest`

**Use Cases:**

- Desktop automation
- System control
- GUI automation
- Cross-platform desktop operations

**Examples:**

```python
# Typical Desktop Commander tools:
# - click: Click at coordinates or element
# - type: Type text
# - screenshot: Capture screen
# - get_window_info: Get window information
# - focus_window: Focus a specific window
```

---

### 11. Mermaid MCP

**Purpose:** Mermaid diagram generation and management

**Configuration:** Project-level (`.cursor/mcp.json`)

- HTTP endpoint: `https://mcp.mermaidchart.com/mcp`

**Use Cases:**

- Generating Mermaid diagrams
- Creating flowcharts and diagrams
- Architecture diagrams
- Process flow visualization

**Examples:**

```python
# Typical Mermaid MCP tools:
# - create_diagram: Create a new Mermaid diagram
# - render_diagram: Render diagram to image/SVG
# - list_diagrams: List all diagrams
# - update_diagram: Update existing diagram

# Example: Create a flowchart
# create_diagram(
#     type="flowchart",
#     content="graph TD\n    A[Start] --> B[Process]\n    B --> C[End]"
# )
```

---

### 12. Pexpect MCP

**Purpose:** Interactive terminal automation

**Configuration:** Project-level (`.cursor/mcp.json`)

- Binary: `/home/ubuntu/.local/bin/pexpect-mcp`

**Use Cases:**

- Interactive command execution
- Terminal automation
- Handling prompts and interactive sessions
- Automated CLI interactions

**Examples:**

```python
# Typical Pexpect tools:
# - run_command: Execute command and handle prompts
# - expect: Wait for specific output
# - send: Send input to interactive command

# Example: Handle password prompt
# run_command(
#     command="sudo apt update",
#     expect="password:",
#     send="your_password"
# )
```

---

### 13. My Graphiti

**Purpose:** Custom Graphiti instance (separate from graphiti-memory)

**Configuration:** Project-level (`.cursor/mcp.json`)

- HTTP endpoint: `http://localhost:8002/mcp/`
- API Key configured
- Runs as separate Docker container: `docker-graphiti-mcp-1`

**Use Cases:**

- Custom knowledge graph operations
- Project-specific memory management
- Separate knowledge graph instance
- Testing or staging knowledge graph

**Note:** This is a separate instance from `graphiti-memory`. Use this for
testing or separate knowledge domains.

---

### 14. Playwright MCP

**Purpose:** Browser automation and testing

**Configuration:**

- User-level (`~/.cursor/mcp.json`)
- Uses casa6 conda environment
- Command: `npx -y @playwright/mcp@latest`

**Use Cases:**

- Browser automation
- E2E testing
- Web scraping
- Complex browser interactions
- Multi-page workflows

**Examples:**

```python
# Typical Playwright tools:
# - navigate: Navigate to URL
# - click: Click element
# - fill: Fill form fields
# - screenshot: Take screenshot
# - evaluate: Execute JavaScript in page context

# Example E2E test workflow:
# 1. navigate(url="http://localhost:5173/dashboard")
# 2. click(selector="button[data-testid='submit']")
# 3. fill(selector="input[name='query']", value="test")
# 4. screenshot(path="test-result.png")
```

---

## Configuration Files

### Project-Level Config

Location: `/data/dsa110-contimg/.cursor/mcp.json`

Contains servers specific to this project:

- Ref, Chrome DevTools, ArXiv, Perplexity (both instances)
- Context7, Graphiti Memory, Desktop Commander
- Mermaid, Pexpect, My Graphiti, Playwright

### User-Level Config

Location: `~/.cursor/mcp.json` (on lxd110h17: `/home/ubuntu/.cursor/mcp.json`)

Contains user-specific servers:

- Codacy
- Figma
- Playwright

## Usage Tips

### Browser Tools

- **Cursor Browser Tool**: Best for quick web testing, uses native Chrome on Mac
- **Playwright MCP**: Best for complex browser automation and E2E tests
- **Chrome DevTools MCP**: Best for debugging and DevTools Protocol access

### Research Tools

- **Perplexity**: Best for current information, research, and fact-checking
- **ArXiv MCP**: Best for academic papers and research literature
- **Ref MCP**: Best for code reference and documentation

### Design Tools

- **Figma MCP**: Best for converting designs to code and accessing design
  systems

### Code Quality

- **Codacy MCP**: Best for code analysis and security checks

### Memory & Knowledge

- **Graphiti Memory**: Best for long-term project knowledge and agent memory
- **My Graphiti**: Custom instance for project-specific needs

## Troubleshooting

### Browser Tools Not Working

- Ensure X11 forwarding is **disabled** in SSH config (see
  [Remote Access Tools Guide](../env.md))
- Verify DISPLAY is unset: `echo $DISPLAY` should be empty
- Restart Cursor after changing SSH config

### Docker-Based Servers

- Ensure Docker is running: `docker ps`
- Check Docker logs if servers fail to start
- Some servers require X11 forwarding (Chrome DevTools)

### HTTP-Based Servers

- Verify network connectivity
- Check API keys are valid
- Ensure endpoints are accessible

### Graphiti Memory

- Verify Neo4j is running: `systemctl status neo4j` or check port 7687
- Check Neo4j credentials in config
- Verify Python environment and dependencies

## Tool Selection Guide

### For Code Quality

- **Codacy**: Use for code analysis, security checks, and pattern definitions

### For Design & UI

- **Figma**: Use for converting designs to code and accessing design systems
- **Mermaid**: Use for creating diagrams and flowcharts

### For Research & Information

- **Perplexity**: Use for current information, research, and fact-checking
- **ArXiv**: Use for academic papers and research literature
- **Ref**: Use for code reference and documentation lookup
- **Context7**: Use for context management and knowledge base access

### For Browser Automation

- **Cursor Browser Tool**: Best for quick web testing (uses native Chrome on
  Mac)
- **Playwright**: Best for complex E2E tests and multi-page workflows
- **Chrome DevTools**: Best for DevTools Protocol debugging

### For Knowledge Management

- **Graphiti Memory**: Use for project knowledge and agent memory (main
  instance)
- **My Graphiti**: Use for testing or separate knowledge domains

### For System Automation

- **Desktop Commander**: Use for desktop/GUI automation
- **Pexpect**: Use for interactive terminal automation

## Common Workflows

### E2E Testing Workflow

1. Use **Playwright** or **Cursor Browser Tool** for browser automation
2. Use **browser_snapshot()** for accessibility-aware element selection
3. Use **browser_network_requests()** to verify API calls
4. Use **browser_console_messages()** to check for errors

### Research Workflow

1. Use **Perplexity** for current information and research
2. Use **perplexity-server_domain_filter()** to focus on trusted sources
3. Use **ArXiv** for academic papers
4. Store findings in **Graphiti Memory** for long-term knowledge

### Design-to-Code Workflow

1. Use **Figma_get_design_context()** to generate code from designs
2. Use **Figma_get_variable_defs()** to extract design tokens
3. Use **Figma_get_code_connect_map()** to link designs to codebase

### Code Quality Workflow

1. Use **Codacy** to analyze code
2. Use **codacy_get_pattern()** to understand specific issues
3. Fix issues and re-analyze

## Related Documentation

- [Remote Access Tools Guide](../env.md) - SSH, Chrome
  Remote Desktop, Browser tool setup
- Graphiti Rules: `../../.cursor/rules/graphiti/` (external directory) -
  Knowledge graph maintenance rules
- MCP Configuration: `../../.cursor/mcp.json` (external file) - Full
  configuration file
- User MCP Configuration: `~/.cursor/mcp.json` (external file) - User-level MCP
  config

---

**Last Updated:** 2025-11-11
