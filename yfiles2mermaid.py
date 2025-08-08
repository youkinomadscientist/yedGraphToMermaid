import xml.etree.ElementTree as ET
import sys
import re
import json

def convert_yfiles_to_mermaid(graphml_file):
    """
    Parses a yFiles-generated GraphML file, including color, stroke, and layout orientation,
    and converts it to Mermaid graph syntax.
    """
    namespaces = {
        'graphml': 'http://graphml.graphdrawing.org/xmlns',
        'y': 'http://www.yworks.com/xml/yfiles-common/3.0',
        'x': 'http://www.yworks.com/xml/yfiles-common/markup/3.0',
        'yjs': 'http://www.yworks.com/xml/yfiles-for-html/3.0/xaml'
    }

    try:
        tree = ET.parse(graphml_file)
        root = tree.getroot()

        # 1. Determine layout direction
        layout_direction = 'TD'
        layout_data_element = root.find('.//graphml:graph/graphml:data[@key="d6"]/y:Json', namespaces)
        if layout_data_element is not None and layout_data_element.text:
            try:
                layout_json = json.loads(layout_data_element.text)
                orientation = layout_json.get('config', {}).get('p_orientation')
                if orientation == 1: layout_direction = 'LR'
                elif orientation == 2: layout_direction = 'BT'
                elif orientation == 3: layout_direction = 'RL'
            except (json.JSONDecodeError, AttributeError):
                pass

        # 2. Pre-parse shared data for color and stroke mappings
        colors, strokes = {}, {}
        shared_data = root.find('.//y:SharedData', namespaces)
        if shared_data is not None:
            for element in shared_data:
                key = element.get('{http://www.yworks.com/xml/yfiles-common/markup/3.0}Key')
                if not key: continue
                if 'Color' in element.tag:
                    value = element.get('value', '#FFFFFF')
                    colors[key] = '#' + value[3:] if len(value) == 9 and value.startswith('#FF') else value
                elif 'Stroke' in element.tag:
                    fill = element.get('fill', '#FFFFFF')
                    match = re.search(r'\{y:GraphMLReference\s*(\d+)\}', fill)
                    strokes[key] = colors.get(match.group(1), '#FFFFFF') if match else fill

        # 3. Parse nodes and their styles
        nodes = {}
        for node_element in root.findall('.//graphml:node', namespaces):
            node_id = node_element.get('id')
            node_label, text_color, stroke_color = 'No Label', '#FFFFFF', '#AAAAAA'

            label_element = node_element.find('.//y:Label', namespaces)
            if label_element is not None:
                node_label = label_element.get('Text', 'No Label')
                # *** CRITICAL FIX: Correctly parse text color from LabelStyle ***
                label_style_element = label_element.find('.//yjs:LabelStyle', namespaces)
                if label_style_element is not None:
                    text_fill_ref = label_style_element.get('textFill', '')
                    match = re.search(r'(\d+)', text_fill_ref)
                    if match and match.group(1) in colors:
                        text_color = colors[match.group(1)]

            style_container = node_element.find('./graphml:data[@key="d7"]/yjs:ShapeNodeStyle', namespaces)
            if style_container is not None:
                stroke_ref = style_container.get('stroke')
                if stroke_ref:
                    match = re.search(r'(\d+)', stroke_ref)
                    if match and match.group(1) in strokes:
                        stroke_color = strokes[match.group(1)]
                else:
                    nested_stroke = style_container.find('.//yjs:Stroke', namespaces)
                    if nested_stroke is not None:
                        fill_color_val = nested_stroke.get('fill', '#AAAAAA')
                        match = re.search(r'\{y:GraphMLReference\s*(\d+)\}', fill_color_val)
                        if match and match.group(1) in colors:
                            stroke_color = colors[match.group(1)]
                        else:
                            stroke_color = '#' + fill_color_val[3:] if len(fill_color_val) == 9 and fill_color_val.startswith('#FF') else fill_color_val

            nodes[node_id] = {
                "label": node_label.replace('"', "'"),
                "safe_id": node_id,
                "text_color": text_color,
                "stroke_color": stroke_color
            }

        # 4. Print Mermaid syntax
        print(f"graph {layout_direction};")
        for _, data in nodes.items():
            # Use rounded rectangle brackets
            print(f'    {data["safe_id"]}("{data["label"]}");')
        
        for _, data in nodes.items():
            print(f'    style {data["safe_id"]} fill:#222,stroke:{data["stroke_color"]},color:{data["text_color"]}')

        for edge_element in root.findall('.//graphml:edge', namespaces):
            source_id, target_id = edge_element.get('source'), edge_element.get('target')
            if source_id in nodes and target_id in nodes:
                print(f'    {nodes[source_id]["safe_id"]} --> {nodes[target_id]["safe_id"]};')

    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        return 1
    
    return 0

def main():
    if len(sys.argv) != 2:
        print("Usage: python yfiles2mermaid.py <path_to_graphml_file>")
        return 1
    
    graphml_file = sys.argv[1]
    return convert_yfiles_to_mermaid(graphml_file)

if __name__ == "__main__":
    sys.exit(main())
