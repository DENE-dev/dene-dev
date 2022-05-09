import os
import ast
#scan a folder recurisively and return all files ending with the flag
def get_path_by_ext(root_dir, flag='.py'):
    paths = []
    for root, dirs, files in os.walk(root_dir):
        files = [f for f in files if not f[0] == '.']  # skip hidden files such as git files
        dirs[:] = [d for d in dirs if not d[0] == '.']
        for f in files:
            if f.endswith(flag):
                paths.append(os.path.join(root, f))
    return paths


class ExprVisitor(ast.NodeVisitor):
    def __init__(self):
        self.symbols = []
        self.predicate = []
        self.symbols = set()
        self.cmp_dump_str = []
    # processing operators
    def visit_Add(self, node):
        self.predicate.append("+")


    def visit_Mult(self, node):
        self.predicate.append("*")
    def visit_Sub(self, node):
        self.predicate.append("-")
    def visit_Div(self, node):
        self.predicate.append("/")
    def visit_FllorDiv(self, node):
        self.predicate.append("/")

    def visit_Pow(self, node):
        self.predicate.append("**")
    def visit_Gt(self, node):
        self.predicate.append(">")

    def visit_Is(self, node):
        self.predicate.append("==")

    def visit_Eq(self, node):
        self.predicate.append("==")

    def visit_And(self, node):

        self.predicate.append("&")

    def visit_Or(self, node):
        self.predicate.append("|")

    def visit_Constant(self, node):
        self.predicate.append(str(node.value))
    def visit_NameConstant(self, node):
        self.predicate.append(str(node.value))

    def visit_Num(self, node):
        self.predicate.append(str(node.n))

    def visit_Compare(self, node):
        if len(node.ops) == 1 and isinstance(node.ops[0],ast.Is):
            node.ops[0] = ast.Eq()
        cmp_str = ast.dump(node)
        self.cmp_dump_str.append(cmp_str)

    def visit_UnaryOp(self, node):
        #print(ast.dump(node))
        return node
    def visit_Name(self, node):
        self.predicate.append(node.id)
        self.symbols.add(node.id)

def get_condition_constraints(node):
    if node is None:
        return []
    visitor = ExprVisitor()
    visitor.visit(node)
    return visitor.cmp_dump_str