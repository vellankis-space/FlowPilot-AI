import networkx as nx

# Configuration for graph layout and rendering
DEFAULT_CHAR_WIDTH_ESTIMATE = 35  # Average pixels per character for node width calculation
DEFAULT_LINE_HEIGHT_ESTIMATE = 50  # Pixels per line for node height calculation
DEFAULT_VIEWBOX_WIDTH = 1400      # Width for the SVG viewbox

# Padding for node dimensions
PADDING_WIDTH = 200
PADDING_HEIGHT = 120

# Safety factor for calculated node dimensions to ensure text fits
SAFETY_FACTOR_WIDTH = 1.5
SAFETY_FACTOR_HEIGHT = 1.5

# Maximum characters per line before inserting <br/>
MAX_CHARS_PER_LINE = 30

def wrap_text_with_br(text: str, max_chars: int) -> str:
    """Wraps text by inserting <br/> tags if a line exceeds max_chars."""
    wrapped_lines = []
    for line in text.split('<br/>'):
        if len(line) > max_chars:
            words = line.split()
            current_line = []
            current_length = 0

            for word in words:
                if current_length + len(word) + 1 <= max_chars:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)

            if current_line:
                wrapped_lines.append(' '.join(current_line))
        else:
            wrapped_lines.append(line)

    return '<br/>'.join(wrapped_lines)

def layout_graph(nodes, edges):
    """Calculate layout positions for nodes in the graph."""
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node["id"])
    for edge in edges:
        G.add_edge(edge["source"], edge["target"])

    # Calculate ranks
    ranks = {node_id: 0 for node_id in G.nodes()}
    sources = [node for node, degree in G.in_degree() if degree == 0]

    queue = [(node, 0) for node in sources]
    visited = set(sources)

    while queue:
        current_node, current_rank = queue.pop(0)
        ranks[current_node] = max(ranks[current_node], current_rank)

        for successor in G.successors(current_node):
            if successor not in visited:
                visited.add(successor)
                queue.append((successor, current_rank + 1))
            else:
                ranks[successor] = max(ranks[successor], current_rank + 1)

    for node_id in G.nodes():
        if node_id not in ranks:
            ranks[node_id] = 0

    # Group nodes by rank
    nodes_by_rank = {}
    for node_id, rank in ranks.items():
        if rank not in nodes_by_rank:
            nodes_by_rank[rank] = []
        nodes_by_rank[rank].append(node_id)

    sorted_ranks = sorted(nodes_by_rank.keys())

    # Calculate node dimensions
    for node in nodes:
        node_label = node["data"]["label"]
        lines = node_label.split('<br/>')

        current_node_text_width = 0
        for line in lines:
            current_node_text_width = max(current_node_text_width, len(line) * DEFAULT_CHAR_WIDTH_ESTIMATE)

        node_calculated_width = (current_node_text_width + PADDING_WIDTH) * SAFETY_FACTOR_WIDTH
        node_calculated_height = (len(lines) * DEFAULT_LINE_HEIGHT_ESTIMATE + PADDING_HEIGHT) * SAFETY_FACTOR_HEIGHT

        node["calculated_width"] = node_calculated_width
        node["calculated_height"] = node_calculated_height

    # Layout nodes
    x_spacing = 80
    y_spacing = 150

    for rank in sorted_ranks:
        current_rank_nodes = nodes_by_rank[rank]
        current_rank_nodes.sort()

        current_rank_total_width = sum(next((n["calculated_width"] for n in nodes if n["id"] == node_id), 0) for node_id in current_rank_nodes) + (len(current_rank_nodes) - 1) * x_spacing
        current_rank_start_x_offset = (DEFAULT_VIEWBOX_WIDTH - current_rank_total_width) / 2 if current_rank_total_width < DEFAULT_VIEWBOX_WIDTH else 0

        current_x_position = current_rank_start_x_offset
        for node_id in current_rank_nodes:
            node = next((n for n in nodes if n["id"] == node_id), None)
            if node:
                node["position"] = {
                    "x": current_x_position,
                    "y": rank * (max(next((n["calculated_height"] for n in nodes if n["id"] == node_id), 0) for node_id in current_rank_nodes) + y_spacing),
                    "width": node["calculated_width"],
                    "height": node["calculated_height"]
                }
                current_x_position += node["calculated_width"] + x_spacing

    max_y = 0
    for node in nodes:
        if "position" in node and node["position"]["y"] + node["position"]["height"] > max_y:
            max_y = node["position"]["y"] + node["position"]["height"]

    max_y += y_spacing
    return nodes, max_y

def generate_mermaid_diagram(nodes, edges):
    """Generate Mermaid diagram syntax from nodes and edges."""
    mermaid_syntax = "graph TD\n"
    style = "padding: 15px; white-space: pre-wrap; text-align: center; font-weight: bold; font-size: 16px; line-height: 1.5; word-wrap: break-word; max-width: 300px; display: inline-block;"

    # Define nodes
    for node in nodes:
        node_id = node["id"]
        node_label = node["data"]["label"]
        # Remove tool name prefix robustly (case-insensitive, strip whitespace)
        prefixes = ["Power Automate: ", "Automation Anywhere: "]
        for prefix in prefixes:
            if node_label.lower().startswith(prefix.lower()):
                node_label = node_label[len(prefix):].lstrip()
        node_label = wrap_text_with_br(node_label, MAX_CHARS_PER_LINE)

        # Escape special characters
        node_label = node_label.replace("\\", "\\\\")
        node_label = node_label.replace("[", "\\[")
        node_label = node_label.replace("]", "\\]")
        node_label = node_label.replace("{", "\\{")
        node_label = node_label.replace("}", "\\}")
        node_label = node_label.replace("(", "\\(")
        node_label = node_label.replace(")", "\\)")
        node_label = node_label.replace("<", "&lt;")
        node_label = node_label.replace(">", "&gt;")
        node_label = node_label.replace("\n", "<br/>")

        shape = node.get("shape", "rectangle")
        if shape == "diamond":
            mermaid_syntax += f'    {node_id}{{"<div style=\"{style}\">{node_label}</div>"}}\n'
        else:
            mermaid_syntax += f'    {node_id}["<div style=\"{style}\">{node_label}</div>"]\n'

    # Define edges
    for edge in edges:
        source_id = edge["source"]
        target_id = edge["target"]
        mermaid_syntax += f"    {source_id} --> {target_id}\n"

    return mermaid_syntax