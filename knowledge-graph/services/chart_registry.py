"""
Chart Registry - Defines chart styles and detailed SVG generation instructions.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ChartCategory(Enum):
    STRUCTURE_HIERARCHY = "Structure & Hierarchy"
    FLOW_PROCESS = "Flow & Process"
    TIME_PLANNING = "Time & Planning"
    NETWORK_TOPOLOGY = "Network & Relationship Topology"
    SPATIAL_PHYSICAL = "Spatial & Physical Layout"
    LOGIC_DECISION = "Logic & Decision Making"
    STATUS_COMPARISON = "Status & Comparative Evaluation"


# Detailed SVG generation guidelines
SVG_BASE_RULES = """
CRITICAL SVG RULES (MUST FOLLOW):
1. ViewBox: Always use viewBox="0 0 1440 900". Never place elements outside this area.
2. Padding: Keep 80px padding from edges. Valid x range: 80-1360, y range: 80-820.
3. Node sizing: Standard node = 220x100px (rounded rect, rx=15), Center node = 280x120px.
4. Max nodes: Limit to 15-20 nodes for readability.
5. Font: Use 'PingFang TC', 'Microsoft JhengHei', 'Noto Sans TC' for Chinese support.
6. Text: Font-size 16-18px for nodes, 22px bold for center. NO truncation - use full Chinese names.
7. Colors: Professional palette - center=#2980B9, Company=#3498DB, Product=#F39C12, Country=#E74C3C.
8. Edges: Use cubic bezier curves with dashed stroke (stroke-dasharray="8,4"). Add arrowheads.
9. Edge Labels: White background boxes (rx=5) behind relationship labels for readability.
10. Shadows: Use feGaussianBlur filter with soft shadow effect for depth.
11. Title: Include a title bar at top center with context in Chinese (e.g., "供應鏈分析: GOOG").
12. Background: Clean white (#ffffff) background.
"""


@dataclass
class ChartStyle:
    id: str
    name: str
    category: ChartCategory
    description: str
    svg_instructions: str
    layout_type: str = "radial"  # radial, hierarchical, grid, flow
    max_nodes: int = 20
    is_internal_suitable: bool = False


class ChartRegistry:
    STYLES: dict[str, ChartStyle] = {
        # Category 1: Structure & Hierarchy
        "STACK_PYRAMID": ChartStyle(
            id="STACK_PYRAMID",
            name="Stack/Pyramid Diagram",
            category=ChartCategory.STRUCTURE_HIERARCHY,
            description="Macro technical stacks, value chain hierarchies, strategic priorities.",
            layout_type="hierarchical",
            max_nodes=12,
            svg_instructions=f"""
{SVG_BASE_RULES}
PYRAMID LAYOUT (1440x900):
- Title at top: y=50, centered at x=720
- Draw 3-5 horizontal layers stacked vertically
- Top layer (smallest): y=150, width=300, centered at x=720
- Each lower layer: +120px y, +150px width
- Bottom layer (largest): y=630, width=900
- Colors: gradient from dark (top #2c3e50) to light (bottom #bdc3c7)
- Add Chinese layer labels inside each rectangle
- Optional: Add small icons or numbers in layers
- Use rounded corners rx=10

EXAMPLE STRUCTURE:
<text x="720" y="50" font-size="28" font-weight="bold" text-anchor="middle">價值鏈分析</text>
<rect x="570" y="150" width="300" height="100" rx="10" fill="#2c3e50"/>
<rect x="495" y="270" width="450" height="100" rx="10" fill="#34495e"/>
<rect x="420" y="390" width="600" height="100" rx="10" fill="#7f8c8d"/>
<rect x="345" y="510" width="750" height="100" rx="10" fill="#95a5a6"/>
""",
            is_internal_suitable=False
        ),

        "N_TIER_NODE_MAP": ChartStyle(
            id="N_TIER_NODE_MAP",
            name="N-Tier Supply Chain Map",
            category=ChartCategory.STRUCTURE_HIERARCHY,
            description="Deep supply chain dependencies, tracing from finished goods to raw materials.",
            layout_type="radial",
            max_nodes=20,
            svg_instructions=f"""
{SVG_BASE_RULES}
N-TIER PROFESSIONAL LAYOUT (1440x900):
- Title: "供應鏈分析: [TICKER]" centered at top (y=50), font-size 28px bold
- Center node: Main company at (720, 450), size 280x120px, color #2980B9, rounded (rx=20)
- Tier 1 ring: 6-8 nodes in circle, radius=280px from center
- Tier 2 ring: Remaining nodes, radius=420px from center

NODE STYLING (MCK-STYLE):
- Size: 220x100px with rounded corners (rx=15, ry=15)
- Two-line text: Line 1 = type label (font-size 14px, light color), Line 2 = name (font-size 18px bold)
- Shadow filter: feGaussianBlur stdDeviation=3, offset dx=2 dy=2, opacity 0.2
- Border: 1.5px stroke, slightly darker than fill

NODE POSITIONING:
For n nodes in ring at radius r from center (720, 450):
  angle = (2 * π * i / n) - π/2
  x = 720 + r * cos(angle) - 110
  y = 450 + r * sin(angle) - 50

EDGE STYLING (PROFESSIONAL):
- Cubic bezier curves: path d="M x1,y1 C ctrl1_x,ctrl1_y ctrl2_x,ctrl2_y x2,y2"
- Stroke: #5D6D7E, width 2.5px, stroke-dasharray="8,4"
- Arrowhead marker at end (viewBox 0 0 10 10, markerWidth=6)
- Edge label: White rect background (width=80, height=28, rx=5) with centered text

COLOR PALETTE:
- Center/Primary: #2980B9 (strong blue)
- Company: #3498DB (blue)
- Supplier: #5CB85C (green) 
- Product: #F39C12 (orange)
- Customer: #9B59B6 (purple)
- Location: #E74C3C (red)
- Other: #95A5A6 (gray)

EXAMPLE STRUCTURE:
<defs>
  <marker id="arrowhead" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#5D6D7E"/>
  </marker>
  <filter id="shadow">...</filter>
</defs>
<text x="720" y="50" font-size="28" font-weight="bold" text-anchor="middle" fill="#34495E">供應鏈分析: TICKER</text>
<g transform="translate(x, y)" style="filter: url(#shadow);">
  <rect width="220" height="100" rx="15" ry="15" fill="#3498DB" stroke="#1F618D" stroke-width="1.5"/>
  <text x="110" y="40" font-size="14" text-anchor="middle" fill="#EAECEE">公司</text>
  <text x="110" y="70" font-size="18" font-weight="bold" text-anchor="middle" fill="#FFFFFF">Company Name</text>
</g>
""",
            is_internal_suitable=False
        ),

        "ORG_CHART": ChartStyle(
            id="ORG_CHART",
            name="Organizational Chart",
            category=ChartCategory.STRUCTURE_HIERARCHY,
            description="Departments, teams, and reporting relationships within a company.",
            layout_type="hierarchical",
            max_nodes=15,
            svg_instructions=f"""
{SVG_BASE_RULES}
ORG CHART LAYOUT:
- Root node: Top center at (450, 60)
- Level 2: Spread horizontally at y=160, even spacing
- Level 3: Below their parents at y=260
- Level 4: Below their parents at y=360
- Vertical lines connect parent to child
- Horizontal lines connect siblings to common vertical

SPACING:
- Horizontal gap between siblings: 150px minimum
- Vertical gap between levels: 100px
- Node size: 120x36px

CONNECTION STYLE:
- Use straight orthogonal lines (not diagonal)
- Parent connects down, then horizontal to children
""",
            is_internal_suitable=True
        ),

        "BOM_TREE": ChartStyle(
            id="BOM_TREE",
            name="Bill of Materials (BOM) Tree",
            category=ChartCategory.STRUCTURE_HIERARCHY,
            description="Product breakdown showing subsystems, modules, and parts.",
            layout_type="hierarchical",
            max_nodes=20,
            svg_instructions=f"""
{SVG_BASE_RULES}
BOM TREE LAYOUT:
- Root (product) at top center: (450, 50)
- Expand downward in tree structure
- Each level indented and spaced evenly
- Use different colors for: Assembly (blue), Module (green), Part (gray)
- Show quantity badges on edges (e.g., "x4")

TREE ALGORITHM:
1. Calculate subtree width for each node
2. Position children centered below parent
3. Draw connecting lines from parent bottom to child top
""",
            is_internal_suitable=True
        ),

        # Category 2: Flow & Process
        "SANKEY": ChartStyle(
            id="SANKEY",
            name="Sankey Diagram",
            category=ChartCategory.FLOW_PROCESS,
            description="Flow and scale of funds, energy, or materials between entities.",
            layout_type="flow",
            max_nodes=12,
            svg_instructions=f"""
{SVG_BASE_RULES}
SANKEY LAYOUT:
- Source nodes on left (x=50-150)
- Target nodes on right (x=750-850)
- Flow paths connect with width proportional to value
- Use gradient fills on flow paths
- Nodes are rectangles, height proportional to total flow

FLOW PATH:
- Use cubic bezier for smooth curves
- Path width = value / max_value * 50 (max 50px width)
- Colors: Use source node color with 0.6 opacity
""",
            is_internal_suitable=False
        ),

        "VALUE_STREAM": ChartStyle(
            id="VALUE_STREAM",
            name="Value Stream Map",
            category=ChartCategory.FLOW_PROCESS,
            description="Linear production steps with value-added segments and bottlenecks.",
            layout_type="flow",
            max_nodes=10,
            svg_instructions=f"""
{SVG_BASE_RULES}
VALUE STREAM LAYOUT:
- Linear left-to-right flow
- Process boxes at y=200, evenly spaced
- Inventory triangles between processes at y=280
- Timeline at bottom showing cycle times
- Data boxes below each process

SYMBOLS:
- Process: Rectangle with rounded corners
- Inventory: Triangle pointing down
- Transport: Truck icon or arrow
- Information: Dashed line
""",
            is_internal_suitable=False
        ),

        "SWIMLANE": ChartStyle(
            id="SWIMLANE",
            name="Swimlane Diagram",
            category=ChartCategory.FLOW_PROCESS,
            description="Process steps organized by responsible department or supplier.",
            layout_type="flow",
            max_nodes=15,
            svg_instructions=f"""
{SVG_BASE_RULES}
SWIMLANE LAYOUT:
- 3-5 horizontal lanes, each 100-150px tall
- Lane headers on left (width=100px)
- Process nodes positioned in appropriate lanes
- Arrows flow left-to-right, crossing lanes as needed
- Different background colors for each lane (subtle pastels)

LANE STRUCTURE:
<rect x="0" y="50" width="900" height="120" fill="#f8f9fa"/>
<rect x="0" y="170" width="900" height="120" fill="#fff"/>
<text x="50" y="110" class="lane-label">Department A</text>
""",
            is_internal_suitable=True
        ),

        # Category 4: Network & Relationship Topology
        "RADAR_CONSTELLATION": ChartStyle(
            id="RADAR_CONSTELLATION",
            name="Constellation/Radar Chart",
            category=ChartCategory.NETWORK_TOPOLOGY,
            description="Partnership strength and role classification around a core entity.",
            layout_type="radial",
            max_nodes=12,
            svg_instructions=f"""
{SVG_BASE_RULES}
CONSTELLATION LAYOUT:
- Center node at (450, 300), larger size (160x50)
- Satellite nodes in circular arrangement
- Connection thickness indicates relationship strength (1-5px)
- Optional: Distance from center indicates importance
- Use radar axes for multi-dimensional comparison

VISUAL ENCODING:
- Strong relationship: Thick line (#333, 4px)
- Medium relationship: Medium line (#666, 2px)
- Weak relationship: Thin dashed line (#999, 1px)
""",
            is_internal_suitable=False
        ),

        "FORCE_DIRECTED": ChartStyle(
            id="FORCE_DIRECTED",
            name="Complex Network Graph",
            category=ChartCategory.NETWORK_TOPOLOGY,
            description="Complex relationships that don't fit simple hierarchical models.",
            layout_type="radial",
            max_nodes=25,
            svg_instructions=f"""
{SVG_BASE_RULES}
NETWORK GRAPH LAYOUT:
- Distribute nodes to minimize edge crossings
- Cluster related nodes together
- Use color to indicate communities/groups
- Node size can indicate importance (degree)
- Edge thickness indicates relationship strength

POSITIONING:
- Start with circular layout
- Adjust positions to reduce overlaps
- Keep nodes within viewBox bounds
- Minimum 80px between node centers
""",
            is_internal_suitable=True
        ),

        # Category 5: Spatial & Physical Layout
        "GEO_MAP": ChartStyle(
            id="GEO_MAP",
            name="Geographic Map",
            category=ChartCategory.SPATIAL_PHYSICAL,
            description="Cross-border logistics, factory distribution, geopolitical risks.",
            layout_type="grid",
            max_nodes=15,
            svg_instructions=f"""
{SVG_BASE_RULES}
GEO MAP LAYOUT:
- Simplified world/region outline as background
- Location markers (circles or pins) at coordinates
- Curved lines connecting locations (trade routes)
- Use country colors or risk heatmap overlay

SIMPLIFIED REGIONS:
- Americas: x=100-250
- Europe: x=400-500
- Asia: x=600-800
- Position nodes by approximate geography
""",
            is_internal_suitable=False
        ),

        # Category 7: Status & Comparative Evaluation
        "HEATMAP_RISK": ChartStyle(
            id="HEATMAP_RISK",
            name="Heatmap & Risk Matrix",
            category=ChartCategory.STATUS_COMPARISON,
            description="Visual risk, dependency, or bottleneck assessment.",
            layout_type="grid",
            max_nodes=25,
            svg_instructions=f"""
{SVG_BASE_RULES}
RISK MATRIX LAYOUT:
- 5x5 grid, cell size ~100x80px
- X-axis: Impact (Low to High)
- Y-axis: Probability (Low to High)  
- Cell colors: Green (low risk) -> Yellow -> Orange -> Red (high risk)
- Place entity labels in appropriate cells

COLOR SCALE:
- (1,1) to (2,2): #27ae60 (green)
- (2,3) to (3,3): #f1c40f (yellow)
- (3,4) to (4,4): #e67e22 (orange)
- (4,5) to (5,5): #e74c3c (red)
""",
            is_internal_suitable=False
        ),

        "COMPARISON_DASHBOARD": ChartStyle(
            id="COMPARISON_DASHBOARD",
            name="Comparison Chart & Dashboard",
            category=ChartCategory.STATUS_COMPARISON,
            description="Comparing competitors or monitoring KPIs side by side.",
            layout_type="grid",
            max_nodes=8,
            svg_instructions=f"""
{SVG_BASE_RULES}
DASHBOARD LAYOUT:
- Divide into 2-4 columns for comparison
- Each column represents one entity
- Rows show metrics (bars, numbers, icons)
- Use consistent scale across columns
- Add column headers with entity names

METRIC BARS:
- Full width = 150px (max value)
- Height = 20px
- Color indicates performance (green=good, red=bad)
""",
            is_internal_suitable=False
        ),
    }

    @classmethod
    def get_style(cls, style_id: str) -> Optional[ChartStyle]:
        return cls.STYLES.get(style_id)

    @classmethod
    def get_default_style(cls) -> ChartStyle:
        return cls.STYLES["N_TIER_NODE_MAP"]

    @classmethod
    def list_styles(cls) -> str:
        return "\n".join([f"{s.id}: {s.name} - {s.description}" for s in cls.STYLES.values()])

    @classmethod
    def get_style_for_data(cls, entity_count: int, edge_count: int) -> ChartStyle:
        """Select appropriate chart style based on data characteristics."""
        if entity_count <= 8:
            return cls.STYLES["RADAR_CONSTELLATION"]
        elif entity_count <= 20:
            return cls.STYLES["N_TIER_NODE_MAP"]
        else:
            return cls.STYLES["FORCE_DIRECTED"]
