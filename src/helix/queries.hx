// Basic queries for the graph

// Create new origin node
QUERY CreateOriginNode(content: String) =>
    origin_node <- AddN<Origin>({ content: content })
    RETURN origin_node

// Create new cited node
QUERY CreateCitedNode(title: String, content: String) =>
    cited_node <- AddN<Cited>({ title: title, content: content })
    RETURN cited_node

// Get all origin nodes
QUERY GetOriginNodes() =>
    nodes <- N<Origin>
    RETURN nodes

// Get all cited nodes
QUERY GetCitedNodes() =>
    nodes <- N<Cited>
    RETURN nodes

// Get all edges
QUERY GetEdges() =>
    edges <- E<Cites>
    RETURN edges

// Drop all nodes
QUERY DropAllNodes() =>
    DROP N<Origin>

    RETURN NONE