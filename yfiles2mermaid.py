import xml.etree.ElementTree as ET
import sys
import re

def convert_yfiles_to_mermaid(graphml_file):
    """
    Parses a yFiles-generated GraphML file, including color information,
    and converts it to Mermaid graph syntax.
    """
    # XML namespaces used in the yFiles GraphML
    namespaces = {
        'graphml': 'http://graphml.graphdrawing.org/xmlns',
        'y': 'http://www.yworks.com/xml/yfiles-common/3.0',
        'x': 'http://www.yworks.com/xml/yfiles-common/markup/3.0',
        'yjs': 'http://www.yworks.com/xml/yfiles-for-html/3.0/xaml'
    }

    try:
        tree = ET.parse(graphml_file)
        root = tree.getroot()

        # 1. Pre-parse shared data to get color mappings
        colors = {}
        for color_element in root.findall('.//yjs:Color', namespaces):
            key = color_element.get('{http://www.yworks.com/xml/yfiles-common/markup/3.0}Key')
            value = color_element.get('value', '#FFFFFF') # Default to white if no value
            # yFiles uses ARGB (#AARRGGBB), Mermaid uses RGB (#RRGGBB). Strip the alpha.
            if len(value) == 9 and value.startswith('#FF'):
                 colors[key] = '#' + value[3:]
            else:
                 colors[key] = value

        # 2. Parse nodes and their styles
        nodes = {}
        for node_element in root.findall('.//graphml:node', namespaces):
            node_id = node_element.get('id')
            label_element = node_element.find('.//y:Label', namespaces)
            
            if label_element is not None:
                node_label = label_element.get('Text', 'No Label')
                node_color = '#FFFFFF' # Default color
                
                style_element = label_element.find('.//yjs:LabelStyle', namespaces)
                if style_element is not None:
                    text_fill_ref = style_element.get('textFill')
                    # Extract the key from "{y:GraphMLReference 38}"
                    match = re.search(r'(\d+)', text_fill_ref or '')
                    if match:
                        color_key = match.group(1)
                        if color_key in colors:
                            node_color = colors[color_key]

                nodes[node_id] = {
                    "label": node_label.replace('"', "'"),
                    "safe_id": node_id,
                    "color": node_color
                }

        # 3. Print Mermaid syntax
        print("graph TD;")
        # Print node definitions
        for node_id, data in nodes.items():
            print(f'    {data["safe_id"]}["{data["label"]}"];')
        
        # Print node styles
        for node_id, data in nodes.items():
            # Use fill for background, color for text
            print(f'    style {data["safe_id"]} fill:#222,stroke:#aaa,color:{data["color"]}')

        # Print edges
        for edge_element in root.findall('.//graphml:edge', namespaces):
            source_id = edge_element.get('source')
            target_id = edge_element.get('target')

            if source_id in nodes and target_id in nodes:
                source_node = nodes[source_id]
                target_node = nodes[target_id]
                print(f'    {source_node["safe_id"]} --> {target_node["safe_id"]};')

    except ET.ParseError as e:
        sys.stderr.write(f"Error parsing XML file: {e}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        return 1
    
    return 0

def main():
    if len(sys.argv) != 2:
        print("Usage: python yfiles2mermaid.py <path_to_graphml_file>")
        return 1
    
    # Correctly get the file path from the command-line arguments
    graphml_file = sys.argv[1]
    return convert_yfiles_to_mermaid(graphml_file)

if __name__ == "__main__":
    sys.exit(main())
