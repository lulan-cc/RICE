from tree_sitter import Language, Parser
import tree_sitter_rust as tsrust
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

# -----------------------------
# 初始化 Rust parser（全局，只需初始化一次）
# -----------------------------
RUST_LANGUAGE = Language(tsrust.language())
parser = Parser(RUST_LANGUAGE)

# -----------------------------
# AST 解析
# -----------------------------
def parse(code: str):
    return parser.parse(code.encode("utf8"))

# -----------------------------
# 计算 AST 深度（跳过 source_file）
# -----------------------------
def ast_depth(node):
    if node.type == "source_file":
        depths = [ast_depth(c) for c in node.children if c.is_named]
        return max(depths) if depths else 0
    named_children = [c for c in node.children if c.is_named]
    if not named_children:
        return 1
    return 1 + max(ast_depth(c) for c in named_children)

# -----------------------------
# 收集 candidate 根节点（跳过 source_file）
# -----------------------------
def collect_candidate_roots(node, result):
    """
    用显式栈遍历 AST，收集所有候选根节点
    跳过 source_file 节点
    """
    stack = [node]

    while stack:
        current = stack.pop()
        if current.type != "source_file":
            result.append(current)
        # 添加所有 named children 到栈
        stack.extend([c for c in current.children if c.is_named])


# -----------------------------
# 深度受限 AST 2-gram
# -----------------------------
def ast_2gram_limited(node, counter, max_depth, cur_depth=1):
    if node.type == "source_file":
        for c in node.children:
            if c.is_named:
                ast_2gram_limited(c, counter, max_depth, cur_depth)
        return
    if cur_depth >= max_depth:
        return
    for c in node.children:
        if c.is_named:
            counter[(node.type, c.type)] += 1
            ast_2gram_limited(c, counter, max_depth, cur_depth + 1)

# -----------------------------
# Counter -> TF-IDF 文档
# -----------------------------
def counter_to_doc(counter):
    tokens = []
    for (p, c), cnt in counter.items():
        tok = f"{p}__{c}"
        tokens.extend([tok] * cnt)
    return " ".join(tokens)

# -----------------------------
# 工具函数：匹配 snippet，并保存完整代码
# -----------------------------
def match_and_save(snippet_code: str, full_code: str, save_path: str, threshold=0.6):
    """
    匹配 snippet 在 full_code 中的局部结构。
    如果任意子树相似度 >= threshold，则将 full_code 保存到 save_path。
    返回：True 表示保存成功，False 表示未命中
    """
    # 解析 AST
    snippet_tree = parse(snippet_code)
    full_tree = parse(full_code)

    # snippet AST 深度
    snippet_depth = ast_depth(snippet_tree.root_node)
    if snippet_depth <= 1:
        return False

    # snippet 2-gram
    snippet_counter = Counter()
    ast_2gram_limited(snippet_tree.root_node, snippet_counter, snippet_depth)
    snippet_doc = counter_to_doc(snippet_counter)

    # full AST 等深子树
    roots = []
    collect_candidate_roots(full_tree.root_node, roots)

    candidate_counters = []
    for r in roots:
        c = Counter()
        ast_2gram_limited(r, c, snippet_depth)
        if c:
            candidate_counters.append(c)

    if not candidate_counters:
        return False

    # 构建语料
    docs = [snippet_doc] + [counter_to_doc(c) for c in candidate_counters]

    # TF-IDF 向量化
    vectorizer = TfidfVectorizer(token_pattern=r"[^\s]+", norm="l2", smooth_idf=True)
    X = vectorizer.fit_transform(docs)
    snippet_vec = X[0]
    candidate_vecs = X[1:]

    # cosine 相似度
    sims = cosine_similarity(snippet_vec, candidate_vecs)[0]

    # 检查是否有命中
    if any(s >= threshold for s in sims):
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(full_code)
        return True

    return False

# -----------------------------
# CLI 测试示例
# -----------------------------
if __name__ == "__main__":
    snippet_code = """
    if a > b {
        println!("a > b");
    }
    """
    full_program_code = """
    fn main() {
        let a = 3;
        let b = 5;
        if a > b {
            println!("a > b");
        } else {
            println!("b >= a");
        }
    }
    """
    save_path = "matched_full_code.rs"
    saved = match_and_save(snippet_code, full_program_code, save_path)
    if saved:
        print(f"匹配成功，完整代码已保存到 {save_path}")
    else:
        print("未匹配到相似结构")
