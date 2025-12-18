from pathlib import Path

def read_markdown_files(path: Path):
    pages = []
    root = Path(path).resolve()
    print("ROOT =", root)
    print("EXISTS =", root.exists(), "IS_DIR =", root.is_dir())
    if root.exists():
        print("LS =", [p.name for p in root.iterdir()])

    for path in root.rglob("*.md"):
        # ignore .git et fichiers techniques
        if ".git" in path.parts:
            continue

        content = path.read_text(encoding="utf-8")

        pages.append({
            "page_path": path.relative_to(root).as_posix(),
            "content": content
        })
    
    for page in pages :
        print(page["content"])

    return pages

    

