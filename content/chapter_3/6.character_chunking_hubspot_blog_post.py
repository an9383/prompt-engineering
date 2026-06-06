import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "hubspot_blog_post.txt")

with open(file_path, "r", encoding='utf-8') as f:
    text = f.read()

# with open("hubspot_blog_post.txt", "r") as f:
#     text = f.read()

chunks = [text[i : i + 200] for i in range(0, len(text), 200)]

for chunk in chunks:
    print("-" * 20)
    print(chunk)
