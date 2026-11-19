import tree_sitter
import tree_sitter_typescript

language = tree_sitter.Language(
    tree_sitter_typescript.language_tsx()
)

parser = tree_sitter.Parser(language)

source_code =  """
export interface User {
    name: string;
}

export type UserID = string | number;

export function greet(name: string): string {
    return `Hello ${name}`;
}

export const calculate = (a: number, b: number): number => {
    return a + b;
};

export class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}
    """

tree = parser.parse(source_code.encode("utf-8"))

def print_tree(node, level = 0):
    print(" " * level + node.type)

    for child in node.named_children:
        print_tree(child, level + 1)

print_tree(tree.root_node)