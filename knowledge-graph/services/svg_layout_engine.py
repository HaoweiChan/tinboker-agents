"""
SVG Layout Engine - Professional supply chain visualization with high-quality rendering.
Generates 1440x900 infographics with Chinese labels, legends, and proper bezier curves.
"""

import math
from dataclasses import dataclass, field


TYPE_LABELS_ZH = {
    "Company": "公司",
    "Supplier": "供應商",
    "Customer": "客戶",
    "Product": "產品",
    "Technology": "技術",
    "Location": "地區",
    "Country": "國家",
    "Person": "人物",
    "Organization": "組織",
    "default": "其他",
    "center": "核心企業",
}

RELATIONSHIP_ZH = {
    "SUPPLIES": "供應",
    "supplies": "供應",
    "SUPPLIES_TO": "供應",
    "SUPPLIED_BY": "被供應",
    "INTEGRATES_WITH": "整合",
    "INTEGRATES": "整合",
    "COMPETES_WITH": "競爭",
    "PARTNERS_WITH": "合作",
    "PARTNERED_WITH": "合作",
    "LOST_CLIENT": "流失客戶",
    "REVENUE_SHARING": "分潤",
    "HAS_REVENUE_SHARE_AGREEMENT_WITH": "分潤",
    "PROVIDES_AI_TO": "提供AI",
    "HAS_INFOGRAPHIC": "有圖表",
    "BEING_CONSIDERED": "考慮中",
    "BEING_CONSIDERED_AS_SUPPLIER": "潛在供應商",
    "EXPLORING_PARTNERSHIP": "探索合作",
    "EXPLORING_PARTNERSHIP_TO_SUPPLY": "探索合作",
    "POTENTIAL_SUPPLIER": "潛在供應商",
    "COURTING_AS_CLIENT": "爭取客戶",
    "SUPPLIES_LOGISTICS": "物流服務",
    "SUPPLIES_LOGISTICS_SERVICES_TO": "物流服務",
    "SUPPLIES_CAPACITY": "供應產能",
    "CUSTOMER_OF": "客戶",
    "MANUFACTURER_OF": "製造商",
    "MANUFACTURES_CUSTOM_HARDWARE_FOR": "代工",
    "INVESTS_IN": "投資",
    "BUYS": "採購",
    "BUILDS": "建設",
    "EXPANDS": "擴展",
    "DEVELOPS": "開發",
    "SUPPLIES_SERVICES_TO": "服務",
    "MANDATES_INVESTMENT_FROM": "要求投資",
}


@dataclass
class NodeLayout:
    id: str
    label: str
    type_label: str
    x: float
    y: float
    width: float
    height: float
    tier: int = 0
    node_type: str = "default"
    color: str = "#3498DB"
    stroke_color: str = "#1F618D"
    subtitle: str = ""


@dataclass
class EdgeLayout:
    source_id: str
    target_id: str
    label: str = ""
    label_zh: str = ""
    color: str = "#5D6D7E"


@dataclass
class SVGLayout:
    width: int = 1440
    height: int = 900
    padding: int = 80
    title: str = "供應鏈分析"
    subtitle: str = ""
    nodes: list[NodeLayout] = field(default_factory=list)
    edges: list[EdgeLayout] = field(default_factory=list)


class SVGLayoutEngine:
    """Professional layout engine for supply chain visualizations."""

    COLORS = {
        "center": {"fill": "#3498DB", "stroke": "#1A5276"},
        "Company": {"fill": "#3498DB", "stroke": "#2471A3"},
        "Supplier": {"fill": "#27AE60", "stroke": "#1E8449"},
        "Customer": {"fill": "#9B59B6", "stroke": "#7D3C98"},
        "Product": {"fill": "#F39C12", "stroke": "#D68910"},
        "Technology": {"fill": "#1ABC9C", "stroke": "#16A085"},
        "Location": {"fill": "#F39C12", "stroke": "#D68910"},
        "Country": {"fill": "#F39C12", "stroke": "#D68910"},
        "Person": {"fill": "#34495E", "stroke": "#2C3E50"},
        "Risk": {"fill": "#E74C3C", "stroke": "#C0392B"},
        "default": {"fill": "#95A5A6", "stroke": "#7F8C8D"},
    }

    EDGE_COLORS = {
        "供應": "#27AE60",
        "合作": "#3498DB",
        "分潤": "#9B59B6",
        "投資": "#F39C12",
        "流失客戶": "#E74C3C",
        "競爭": "#E74C3C",
        "探索合作": "#3498DB",
        "潛在供應商": "#3498DB",
        "default": "#5D6D7E",
    }

    def __init__(self, width: int = 1440, height: int = 900, max_nodes: int = 15, language: str = "zh-TW"):
        self.width = width
        self.height = height
        self.max_nodes = max_nodes
        self.language = language
        self.padding = 100
        self.center_x = width / 2
        self.center_y = height / 2 + 30

    def layout_tiered(
        self,
        center_entity: dict,
        related_entities: list[dict],
        edges: list[dict],
        title: str | None = None,
    ) -> SVGLayout:
        """Create a tiered radial layout with high-quality nodes."""
        center_name = center_entity.get("name", center_entity.get("id", ""))
        auto_title = f"供應鏈分析: {center_name.upper()}"
        
        layout = SVGLayout(
            width=self.width, 
            height=self.height, 
            title=title or auto_title,
            subtitle="全球供應鏈關係圖"
        )

        # Limit and deduplicate entities
        seen_ids = set()
        unique_entities = []
        for e in related_entities:
            eid = e.get("id", "")
            if eid and eid not in seen_ids and eid != center_entity.get("id"):
                # Skip bad entity names
                if "_supply_chain" in eid.lower() or len(eid) > 50:
                    continue
                seen_ids.add(eid)
                unique_entities.append(e)
                if len(unique_entities) >= self.max_nodes - 1:
                    break

        # Categorize entities by relationship
        suppliers = []
        customers = []
        partners = []
        others = []
        
        edge_map = {}
        for edge in edges:
            src, dst, rel = edge.get("src"), edge.get("dst"), edge.get("rel", "")
            if src == center_entity.get("id"):
                edge_map[dst] = rel
            elif dst == center_entity.get("id"):
                edge_map[src] = rel

        for e in unique_entities:
            eid = e.get("id")
            rel = edge_map.get(eid, "")
            rel_lower = rel.lower()
            
            if "supplies" in rel_lower or "supply" in rel_lower:
                e["_category"] = "Supplier"
                suppliers.append(e)
            elif "customer" in rel_lower or "client" in rel_lower:
                e["_category"] = "Customer"
                customers.append(e)
            elif "partner" in rel_lower or "revenue" in rel_lower:
                e["_category"] = "Partner"
                partners.append(e)
            elif "lost" in rel_lower or "risk" in rel_lower:
                e["_category"] = "Risk"
                others.append(e)
            elif "invest" in rel_lower or "build" in rel_lower:
                e["_category"] = "Location"
                others.append(e)
            else:
                e["_category"] = e.get("type", "default")
                others.append(e)

        # Center node
        center_colors = self.COLORS["center"]
        center_node = NodeLayout(
            id=center_entity.get("id", "center"),
            label=center_entity.get("name", "Center"),
            type_label="核心企業",
            x=self.center_x - 140,
            y=self.center_y - 60,
            width=280,
            height=120,
            tier=0,
            node_type="center",
            color=center_colors["fill"],
            stroke_color=center_colors["stroke"],
        )
        layout.nodes.append(center_node)

        # Place nodes in sectors
        # Top-left: Suppliers (Tier 1)
        # Top-right: Suppliers (Tier 1 overflow)  
        # Right: Customers/Partners
        # Bottom: Others/Locations
        
        positions = self._calculate_sector_positions(suppliers, customers, partners, others)
        
        for e, (x, y) in positions:
            category = e.get("_category", "default")
            colors = self.COLORS.get(category, self.COLORS["default"])
            type_label = TYPE_LABELS_ZH.get(category, TYPE_LABELS_ZH["default"])
            
            layout.nodes.append(NodeLayout(
                id=e.get("id", ""),
                label=self._clean_label(e.get("name", e.get("id", ""))),
                type_label=type_label,
                x=x,
                y=y,
                width=200,
                height=90,
                tier=1,
                node_type=category,
                color=colors["fill"],
                stroke_color=colors["stroke"],
            ))

        # Add edges
        node_map = {n.id: n for n in layout.nodes}
        for edge in edges:
            src_id = edge.get("src", "")
            dst_id = edge.get("dst", "")
            if src_id in node_map and dst_id in node_map:
                rel = edge.get("rel", "")
                rel_zh = RELATIONSHIP_ZH.get(rel, self._clean_relationship(rel))
                layout.edges.append(EdgeLayout(
                    source_id=src_id,
                    target_id=dst_id,
                    label=rel,
                    label_zh=rel_zh,
                    color=self.EDGE_COLORS.get(rel_zh, self.EDGE_COLORS["default"]),
                ))

        return layout

    def _calculate_sector_positions(self, suppliers, customers, partners, others):
        """Calculate positions for different entity categories in sectors."""
        positions = []
        
        # Suppliers: Top arc (150° to 30°, i.e., top-left to top-right)
        if suppliers:
            radius = 300
            start_angle = math.pi * 5/6  # 150°
            end_angle = math.pi / 6      # 30°
            step = (start_angle - end_angle) / max(len(suppliers) - 1, 1) if len(suppliers) > 1 else 0
            for i, e in enumerate(suppliers[:6]):
                angle = start_angle - i * step
                x = self.center_x + radius * math.cos(angle) - 100
                y = self.center_y - 60 + radius * math.sin(angle) - 45
                y = max(self.padding, min(y, self.height - 150))
                x = max(self.padding, min(x, self.width - 220))
                positions.append((e, (x, y)))

        # Customers & Partners: Right side
        right_entities = customers + partners
        if right_entities:
            start_y = 200
            step_y = min(150, (self.height - 300) / max(len(right_entities), 1))
            for i, e in enumerate(right_entities[:4]):
                x = self.width - 280
                y = start_y + i * step_y
                positions.append((e, (x, y)))

        # Others: Bottom arc
        if others:
            radius = 320
            start_angle = -math.pi / 6   # -30°
            end_angle = -math.pi * 5/6   # -150°
            step = (start_angle - end_angle) / max(len(others) - 1, 1) if len(others) > 1 else 0
            for i, e in enumerate(others[:5]):
                angle = start_angle - i * step
                x = self.center_x + radius * math.cos(angle) - 100
                y = self.center_y - 60 + radius * math.sin(angle) - 45
                y = max(self.padding + 50, min(y, self.height - 150))
                x = max(self.padding, min(x, self.width - 220))
                positions.append((e, (x, y)))

        return positions

    def _clean_label(self, label: str) -> str:
        """Clean up entity labels."""
        # Remove underscores and clean up
        label = label.replace("_", " ").strip()
        # Capitalize properly
        if label.isupper() or label.islower():
            label = label.title()
        return label[:25] if len(label) > 25 else label

    def _clean_relationship(self, rel: str) -> str:
        """Clean up relationship labels."""
        return rel.replace("_", " ").title()[:20]

    def render_svg(self, layout: SVGLayout) -> str:
        """Render layout to high-quality SVG string."""
        svg_parts = [self._render_header(layout)]
        svg_parts.append(self._render_defs())
        svg_parts.append(self._render_background(layout))
        svg_parts.append(self._render_title(layout))

        # Render edges first (behind nodes)
        node_map = {n.id: n for n in layout.nodes}
        for edge in layout.edges:
            src = node_map.get(edge.source_id)
            dst = node_map.get(edge.target_id)
            if src and dst:
                svg_parts.append(self._render_edge(src, dst, edge.label_zh, edge.color))

        # Render nodes
        for node in layout.nodes:
            svg_parts.append(self._render_node(node))

        # Render legend
        svg_parts.append(self._render_legend())
        svg_parts.append(self._render_footer())
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)

    def _render_header(self, layout: SVGLayout) -> str:
        return f'''<svg width="{layout.width}" height="{layout.height}" viewBox="0 0 {layout.width} {layout.height}" 
     xmlns="http://www.w3.org/2000/svg"
     style="font-family: 'PingFang TC', 'Microsoft JhengHei', 'Noto Sans TC', sans-serif; background-color: #ffffff;">'''

    def _render_defs(self) -> str:
        return '''
  <defs>
    <marker id="arrowhead" viewBox="0 0 10 10" refX="8" refY="5" 
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#5D6D7E"/>
    </marker>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="4"/>
      <feOffset dx="2" dy="3" result="offsetblur"/>
      <feComponentTransfer>
        <feFuncA type="linear" slope="0.25"/>
      </feComponentTransfer>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <linearGradient id="centerGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#3498DB;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2471A3;stop-opacity:1" />
    </linearGradient>
  </defs>'''

    def _render_background(self, layout: SVGLayout) -> str:
        cx, cy = layout.width / 2, layout.height / 2 + 30
        return f'''
  <rect width="{layout.width}" height="{layout.height}" fill="#FAFBFC"/>
  <circle cx="{cx}" cy="{cy}" r="280" fill="none" stroke="#ECF0F1" stroke-width="2" stroke-dasharray="10,5"/>
  <circle cx="{cx}" cy="{cy}" r="400" fill="none" stroke="#ECF0F1" stroke-width="1" stroke-dasharray="5,5"/>'''

    def _render_title(self, layout: SVGLayout) -> str:
        cx = layout.width / 2
        return f'''
  <text x="{cx}" y="50" font-size="36" font-weight="bold" 
        text-anchor="middle" fill="#2C3E50">{layout.title}</text>
  <text x="{cx}" y="80" font-size="14" text-anchor="middle" fill="#7F8C8D">{layout.subtitle}</text>
  <line x1="{cx - 240}" y1="95" x2="{cx + 240}" y2="95" stroke="#BDC3C7" stroke-width="1"/>'''

    def _render_node(self, node: NodeLayout) -> str:
        if node.tier == 0:
            # Center node with gradient
            return f'''
  <g transform="translate({node.x:.1f}, {node.y:.1f})" style="filter: url(#shadow);">
    <rect width="{node.width}" height="{node.height}" rx="20" ry="20" 
          fill="url(#centerGradient)" stroke="{node.stroke_color}" stroke-width="2"/>
    <text x="{node.width/2}" y="40" font-size="14" text-anchor="middle" fill="#D5DBDB">{node.type_label}</text>
    <text x="{node.width/2}" y="75" font-size="28" font-weight="bold" 
          text-anchor="middle" fill="#FFFFFF">{node.label}</text>
  </g>'''
        else:
            # Regular node
            return f'''
  <g transform="translate({node.x:.1f}, {node.y:.1f})" style="filter: url(#shadow);">
    <rect width="{node.width}" height="{node.height}" rx="15" ry="15" 
          fill="{node.color}" stroke="{node.stroke_color}" stroke-width="1.5"/>
    <text x="{node.width/2}" y="30" font-size="11" text-anchor="middle" fill="#D5DBDB">{node.type_label}</text>
    <text x="{node.width/2}" y="55" font-size="18" font-weight="bold" 
          text-anchor="middle" fill="#FFFFFF">{node.label}</text>
  </g>'''

    def _render_edge(self, src: NodeLayout, dst: NodeLayout, label: str, color: str) -> str:
        # Calculate edge endpoints
        src_cx = src.x + src.width / 2
        src_cy = src.y + src.height / 2
        dst_cx = dst.x + dst.width / 2
        dst_cy = dst.y + dst.height / 2

        dx = dst_cx - src_cx
        dy = dst_cy - src_cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 50:
            return ""

        # Offset from node edges
        src_offset = max(src.width, src.height) / 2 + 10
        dst_offset = max(dst.width, dst.height) / 2 + 15

        x1 = src_cx + (dx / dist) * src_offset
        y1 = src_cy + (dy / dist) * src_offset
        x2 = dst_cx - (dx / dist) * dst_offset
        y2 = dst_cy - (dy / dist) * dst_offset

        # Control point for quadratic bezier (curved path)
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        # Perpendicular offset for curve
        perp_scale = min(0.3, 50 / dist)
        ctrl_x = mid_x - dy * perp_scale
        ctrl_y = mid_y + dx * perp_scale

        # Label position
        label_x = mid_x - dy * perp_scale * 0.4
        label_y = mid_y + dx * perp_scale * 0.4
        label_width = max(60, len(label) * 12 + 16)

        return f'''
  <g>
    <path d="M {x1:.1f} {y1:.1f} Q {ctrl_x:.1f} {ctrl_y:.1f}, {x2:.1f} {y2:.1f}" 
          stroke="{color}" stroke-width="2.5" fill="none" marker-end="url(#arrowhead)"/>
    <rect x="{label_x - label_width/2:.1f}" y="{label_y - 13:.1f}" width="{label_width}" height="26" 
          fill="#ffffff" rx="6" filter="url(#shadow)"/>
    <text x="{label_x:.1f}" y="{label_y + 4:.1f}" font-size="12" text-anchor="middle" 
          fill="{color}" font-weight="600">{label}</text>
  </g>'''

    def _render_legend(self) -> str:
        return '''
  <g transform="translate(50, 800)">
    <rect width="320" height="85" rx="8" fill="#FFFFFF" stroke="#ECF0F1" stroke-width="1" filter="url(#shadow)"/>
    <text x="160" y="20" font-size="12" font-weight="bold" text-anchor="middle" fill="#2C3E50">圖例 Legend</text>
    
    <rect x="15" y="35" width="14" height="14" fill="#27AE60" rx="3"/>
    <text x="35" y="46" font-size="11" fill="#34495E">供應商</text>
    
    <rect x="90" y="35" width="14" height="14" fill="#9B59B6" rx="3"/>
    <text x="110" y="46" font-size="11" fill="#34495E">合作夥伴</text>
    
    <rect x="180" y="35" width="14" height="14" fill="#3498DB" rx="3"/>
    <text x="200" y="46" font-size="11" fill="#34495E">客戶</text>
    
    <rect x="250" y="35" width="14" height="14" fill="#F39C12" rx="3"/>
    <text x="270" y="46" font-size="11" fill="#34495E">投資</text>
    
    <rect x="15" y="58" width="14" height="14" fill="#E74C3C" rx="3"/>
    <text x="35" y="69" font-size="11" fill="#34495E">風險</text>
    
    <line x1="90" y1="65" x2="120" y2="65" stroke="#5D6D7E" stroke-width="2.5"/>
    <text x="130" y="69" font-size="11" fill="#34495E">關係</text>
  </g>'''

    def _render_footer(self) -> str:
        return f'''
  <text x="{self.width - 50}" y="{self.height - 20}" font-size="10" text-anchor="end" fill="#BDC3C7">
    資料來源: 供應鏈分析系統 • Graph-Builder-Agent
  </text>'''
