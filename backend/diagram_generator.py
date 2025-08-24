import networkx as nx

# Configuration for graph layout and rendering
DEFAULT_CHAR_WIDTH_ESTIMATE = 25  # Average pixels per character for node width calculation
DEFAULT_LINE_HEIGHT_ESTIMATE = 40 # Pixels per line for node height calculation
DEFAULT_VIEWBOX_WIDTH = 1200       # Default width for the SVG viewbox

# Padding for node dimensions
PADDING_WIDTH = 150
PADDING_HEIGHT = 80

# Safety factor for calculated node dimensions to ensure text fits
SAFETY_FACTOR_WIDTH = 1.2
SAFETY_FACTOR_HEIGHT = 1.2

MAX_CHARS_PER_LINE = 15 # Maximum characters per line before inserting <br/>

def wrap_text_with_br(text: str, max_chars: int) -> str:
    """
    Wraps text by inserting <br/> tags if a line exceeds max_chars.
    Preserves existing <br/> tags.
    """
    wrapped_lines = []
    for line in text.split('<br/>'):
        if len(line) > max_chars:
            # Break long lines into smaller chunks
            chunks = [line[i:i+max_chars] for i in range(0, len(line), max_chars)]
            wrapped_lines.extend(chunks)
        else:
            wrapped_lines.append(line)
    return '<br/>'.join(wrapped_lines)

def layout_graph(nodes, edges):
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node["id"])
    for edge in edges:
        G.add_edge(edge["source"], edge["target"])

    # Step 1: Calculate Ranks (Levels)
    # This is a simplified ranking algorithm. For more complex graphs or
    # to achieve specific aesthetic layouts (e.g., minimizing edge crossings),
    # a proper longest path algorithm, Coffman-Graham algorithm, or a force-directed
    # layout might be needed. The current approach is a basic topological sort.
    # Initialize ranks for all nodes to 0
    ranks = {node_id: 0 for node_id in G.nodes()}
    # Perform a topological sort to determine ranks
    # Nodes with no predecessors are rank 0
    # Rank of a node is max(rank of predecessors) + 1
    
    # Get all nodes with no incoming edges (potential starting nodes)
    sources = [node for node, degree in G.in_degree() if degree == 0]
    
    # Use a queue for BFS-like traversal to assign ranks
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
                # If already visited, update rank if a longer path is found
                ranks[successor] = max(ranks[successor], current_rank + 1)

    # Ensure all nodes have a rank, even if not reachable from a source (e.g., isolated nodes or cycles)
    # For simplicity, assign them to rank 0 if they haven't been assigned yet.
    for node_id in G.nodes():
        if node_id not in ranks:
            ranks[node_id] = 0

    # Step 2: Assign X-coordinates within Ranks and Y-coordinates based on Ranks
    # Group nodes by rank
    nodes_by_rank = {}
    for node_id, rank in ranks.items():
        if rank not in nodes_by_rank:
            nodes_by_rank[rank] = []
        nodes_by_rank[rank].append(node_id)

    # Sort ranks to process layer by layer
    sorted_ranks = sorted(nodes_by_rank.keys())

    # Calculate positions
    max_nodes_in_rank = max(len(nodes_by_rank[rank]) for rank in sorted_ranks) if sorted_ranks else 1
    
    # Calculate dynamic node dimensions for each node
    for node in nodes:
        node_label = node["data"]["label"]
        lines = node_label.split('<br/>') # Split by the newline replacement

        # Calculate width for this specific node
        current_node_text_width = 0
        for line in lines:
            current_node_text_width = max(current_node_text_width, len(line) * DEFAULT_CHAR_WIDTH_ESTIMATE)
        
        node_calculated_width = (current_node_text_width + PADDING_WIDTH) * SAFETY_FACTOR_WIDTH
        node_calculated_height = (len(lines) * DEFAULT_LINE_HEIGHT_ESTIMATE + PADDING_HEIGHT) * SAFETY_FACTOR_HEIGHT
        
        # Store calculated dimensions in the node itself
        node["calculated_width"] = node_calculated_width
        node["calculated_height"] = node_calculated_height

    # Define spacing parameters
    x_spacing = 50 # Horizontal spacing between nodes
    y_spacing = 100 # Vertical spacing between ranks

    for rank in sorted_ranks:
        current_rank_nodes = nodes_by_rank[rank]
        # Sort nodes within a rank for consistent ordering (e.g., by ID)
        current_rank_nodes.sort()
        
        # Calculate total width for current rank to center it
        # Sum of individual node widths + spacing between them
        current_rank_total_width = sum(next((n["calculated_width"] for n in nodes if n["id"] == node_id), 0) for node_id in current_rank_nodes) \
                                 + (len(current_rank_nodes) - 1) * x_spacing
        
        current_rank_start_x_offset = (DEFAULT_VIEWBOX_WIDTH - current_rank_total_width) / 2 if current_rank_total_width < DEFAULT_VIEWBOX_WIDTH else 0
        
        current_x_position = current_rank_start_x_offset
        for i, node_id in enumerate(current_rank_nodes):
            node = next((n for n in nodes if n["id"] == node_id), None)
            if node:
                node["position"] = {
                    "x": current_x_position,
                    "y": rank * (max(next((n["calculated_height"] for n in nodes if n["id"] == node_id), 0) for node_id in current_rank_nodes) + y_spacing) + 5, # Use max height in rank for y-spacing
                    "width": node["calculated_width"],
                    "height": node["calculated_height"]
                }
                current_x_position += node["calculated_width"] + x_spacing
    
    max_y = 0
    for node in nodes:
        if "position" in node and node["position"]["y"] + node["position"]["height"] > max_y:
            max_y = node["position"]["y"] + node["position"]["height"]
    
    # Add some padding to the max_y
    max_y += y_spacing # Add a spacing for padding

    return nodes, max_y

def generate_mermaid_diagram(nodes, edges):
    mermaid_syntax = "graph TD\n"

    # Define nodes
    for node in nodes:
        node_id = node["id"]
        node_label = node["data"]["label"]
        node_label = wrap_text_with_br(node_label, MAX_CHARS_PER_LINE) # Apply wrapping first
        # Escape special characters for Mermaid labels
        node_label = node_label.replace('\\', '\\\\') # Escape backslashes
        # node_label = node_label.replace('"', '\"') # Removed: Escape double quotes for Mermaid
        node_label = node_label.replace('[', '\[') # Escape [
        node_label = node_label.replace(']', '\]') # Escape ]
        node_label = node_label.replace('{', '\{') # Escape {
        node_label = node_label.replace('}', '\}') # Escape }
        node_label = node_label.replace('(', '\(') # Escape (
        node_label = node_label.replace(')', '\)') # Escape )
        node_label = node_label.replace('<', '&lt;') # Escape <
        node_label = node_label.replace('>', '&gt;') # Escape >
        node_label = node_label.replace('\n', '<br/>') # Handle newlines

        shape = node.get("shape", "rectangle") # Default to rectangle

        if shape == "diamond":
            mermaid_syntax += f"""    {node_id}{{"<div style='padding: 5px;'>{node_label}</div>"}}
"""
        else: # Default to rectangle for other shapes or if shape is not specified
            mermaid_syntax += f"""    {node_id}["<div style='padding: 5px;'>{node_label}</div>"]
"""

    # Define edges
    for edge in edges:
        source_id = edge["source"]
        target_id = edge["target"]
        mermaid_syntax += f"""    {source_id} --> {target_id}
"""

    return mermaid_syntax