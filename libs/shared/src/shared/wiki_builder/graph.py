"""Build a graph.json from the wiki using Graphify (optional).

This is the bridge between the wiki (markdown-first) and graph-based queries.
Run ``build_wiki_graph()`` to produce ``wiki-graph/graph.json`` that can be
queried via Graphify's BFS/DFS traversal.

Graphify is an optional dependency -- the wiki works without it.
"""

import json
from pathlib import Path
from typing import Optional

_DEFAULT_WIKI_ROOT = Path(__file__).resolve().parents[5] / "wiki"
_DEFAULT_GRAPH_OUT = Path(__file__).resolve().parents[5] / "wiki-graph"


def _graphify_available() -> bool:
    try:
        import graphify  # noqa: F401
        return True
    except ImportError:
        return False


def build_wiki_graph(
    wiki_root: Optional[Path] = None,
    graph_out: Optional[Path] = None,
) -> Optional[Path]:
    """Run Graphify on the wiki folder to produce graph.json.

    Returns the path to graph.json if successful, None otherwise.
    """
    root = wiki_root or _DEFAULT_WIKI_ROOT
    out = graph_out or _DEFAULT_GRAPH_OUT
    out.mkdir(parents=True, exist_ok=True)

    if not _graphify_available():
        print(
            "  graphify not installed -- skipping graph build. "
            "Install with: pip install graphifyy"
        )
        return None

    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.detect import detect
    from graphify.export import to_json
    from graphify.extract import collect_files, extract

    detection = detect(root)
    total_files = detection.get("total_files", 0)
    if total_files == 0:
        print("  No wiki files found -- nothing to graph.")
        return None

    print(f"  Building graph from {total_files} wiki files...")

    all_files = []
    for ftype, fpaths in detection.get("files", {}).items():
        for fp in fpaths:
            p = Path(fp)
            if p.is_dir():
                all_files.extend(collect_files(p))
            else:
                all_files.append(p)

    ast_result = extract(all_files) if all_files else {"nodes": [], "edges": []}
    graph = build_from_json(ast_result)
    communities = cluster(graph)
    cohesion = score_all(graph, communities)

    graph_json_path = out / "graph.json"
    to_json(graph, communities, str(graph_json_path))

    print(
        f"  Graph built: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges, {len(communities)} communities"
    )
    return graph_json_path
